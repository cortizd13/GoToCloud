import asyncio
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta, timezone
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .gemini_live_client import GeminiLiveClient
from .audio_codec import gemini_pcm_to_twilio_payload, twilio_payload_to_gemini_pcm
from .event_bus import EventBus
from .agent_orchestrator import AgentOrchestrator
from .channel_adapter import ChannelAdapterFactory, ChannelType
from .supabase_client import supabase

try:
    from service.gotocloud_voicebot_tool import (
        GOTOCLOUD_TOOLS,
        SYSTEM_PROMPT,
        ejecutar_tool,
    )
    logger_tmp = logging.getLogger(__name__)
    logger_tmp.info(f"GoToCloud tools cargados: {len(GOTOCLOUD_TOOLS)} tools")
except ImportError:
    GOTOCLOUD_TOOLS = None
    SYSTEM_PROMPT = None
    ejecutar_tool = None
    logging.getLogger(__name__).warning(
        "service/gotocloud_voicebot_tool.py no encontrado — corriendo sin tools"
    )

try:
    from .text_agent_client import TextAgentSession
    TEXT_AGENT_AVAILABLE = True
except ImportError:
    TextAgentSession = None  # type: ignore[assignment]
    TEXT_AGENT_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "text_agent_client.py no disponible — endpoint /chat/message deshabilitado"
    )

# Sesiones activas del agente de texto
_sessions: dict[str, TextAgentSession] = {}

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

BOGOTA_TZ = timezone(timedelta(hours=-5), name="America/Bogota")

app = FastAPI(title="Twilio ↔ Gemini Live Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multi-channel infrastructure lifecycle
event_bus = EventBus()
orchestrator = AgentOrchestrator(event_bus=event_bus)


@app.on_event("startup")
async def startup():
    await event_bus.start()
    await orchestrator.start()
    logger.info("Multi-channel infrastructure started")
    if GOTOCLOUD_TOOLS:
        logger.info(f"[TOOLS] Cargados {len(GOTOCLOUD_TOOLS)} tools de GoToCloud")
    else:
        logger.warning("[TOOLS] Sin tools — Camila correrá sin funciones de registro")


@app.on_event("shutdown")
async def shutdown():
    await orchestrator.stop()
    await event_bus.stop()
    logger.info("Multi-channel infrastructure stopped")

TWIML_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}" />
  </Connect>
</Response>"""


def _stream_url() -> str:
    public_url = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    if not public_url:
        raise ValueError("PUBLIC_URL no está configurada en backend/.env")
    for prefix in ("https://", "http://"):
        if public_url.startswith(prefix):
            return "wss://" + public_url[len(prefix):] + "/twilio-stream"
    return public_url + "/twilio-stream"  # asume que ya es wss://


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "event_bus": "running",
        "orchestrator": "ready",
        "channels": ChannelAdapterFactory.list_channels(),
    }


def _bogota_day_bounds(days_ago: int = 0) -> tuple[datetime, datetime]:
    target_day = datetime.now(BOGOTA_TZ).date() - timedelta(days=days_ago)
    start_local = datetime.combine(target_day, time.min, tzinfo=BOGOTA_TZ)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "N/D"
    seconds = max(0, int(seconds))
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}:{remainder:02d}"


def _trend(current: int | float | None, previous: int | float | None) -> dict:
    if current is None or previous is None:
        return {"value": "N/D", "direction": "flat"}
    if previous == 0:
        if current == 0:
            return {"value": "0%", "direction": "flat"}
        return {"value": "+100%", "direction": "up"}

    change = ((current - previous) / previous) * 100
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return {"value": f"{change:+.1f}%", "direction": direction}


def _safe_query(table_name: str, select: str, date_column: str | None = None,
                start: datetime | None = None, end: datetime | None = None) -> list[dict]:
    if supabase is None:
        return []

    try:
        query = supabase.table(table_name).select(select)
        if date_column and start and end:
            query = query.gte(date_column, start.isoformat()).lt(
                date_column, end.isoformat()
            )
        result = query.execute()
        return result.data or []
    except Exception as exc:
        logger.warning("Dashboard query failed for %s: %s", table_name, exc)
        return []


def _extract_rating(payload: dict | None) -> float | None:
    if not isinstance(payload, dict):
        return None

    for key in ("csat", "rating", "score", "satisfaction"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _count_sentiment(row: dict) -> str | None:
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        sentiment = metadata.get("sentiment") or metadata.get("sentimiento")
        if isinstance(sentiment, str):
            normalized = sentiment.lower()
            if normalized in {"positive", "positivo", "pos"}:
                return "positive"
            if normalized in {"negative", "negativo", "neg"}:
                return "negative"
    return None


def _hour_label(hour: int) -> str:
    return f"{hour:02d}:00"


def _format_lead(row: dict) -> dict:
    cliente = row.get("clientes") or {}
    return {
        "id": row.get("id"),
        "nombre": cliente.get("nombre") or "Desconocido",
        "empresa": cliente.get("empresa") or "",
        "telefono": cliente.get("telefono") or "",
        "scoreLead": row.get("score_lead") or 0,
        "intention": row.get("intention") or "fria",
        "serviciosInteres": row.get("servicios_interes") or [],
        "recomendaciones": row.get("recomendaciones") or "",
        "startedAt": str(row.get("started_at") or ""),
    }


def _dashboard_recommendations(reason_counts: Counter, channel_counts: Counter,
                               avg_score: float | None, total_today: int) -> list[dict]:
    recommendations = []

    if reason_counts:
        top_reason, top_count = reason_counts.most_common(1)[0]
        recommendations.append({
            "id": "faq-top-reason",
            "title": f"Actualizar FAQ para {top_reason}",
            "impact": "alto" if top_count >= max(3, total_today * 0.3) else "medio",
        })

    if channel_counts:
        top_channel, _ = channel_counts.most_common(1)[0]
        recommendations.append({
            "id": "channel-playbook",
            "title": f"Crear playbook para conversaciones por {top_channel}",
            "impact": "medio",
        })

    if avg_score is not None and avg_score >= 70:
        recommendations.append({
            "id": "hot-leads",
            "title": "Priorizar seguimiento comercial a leads calientes",
            "impact": "alto",
        })

    recommendations.append({
        "id": "knowledge-refresh",
        "title": "Re-entrenar agente con preguntas recientes de clientes",
        "impact": "medio",
    })

    return recommendations[:4]


@app.get("/dashboard/summary")
async def dashboard_summary():
    """Resumen ejecutivo para el dashboard, calculado desde Supabase."""
    if supabase is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"detail": "Supabase no está configurado en backend/.env"},
        )

    today_start, today_end = _bogota_day_bounds()
    yesterday_start, yesterday_end = _bogota_day_bounds(days_ago=1)

    sessions_today = _safe_query(
        "conversation_sessions",
        "id,channel_type,status,started_at,ended_at,created_at",
        "started_at",
        today_start,
        today_end,
    )
    sessions_yesterday = _safe_query(
        "conversation_sessions",
        "id,channel_type,status,started_at,ended_at,created_at",
        "started_at",
        yesterday_start,
        yesterday_end,
    )
    calls_today = _safe_query(
        "sesiones",
        "id,started_at,ended_at,duracion_segundos,intention,score_lead,servicios_interes,recomendaciones,created_at",
        "started_at",
        today_start,
        today_end,
    )
    calls_yesterday = _safe_query(
        "sesiones",
        "id,started_at,duracion_segundos,created_at",
        "started_at",
        yesterday_start,
        yesterday_end,
    )
    messages_today = _safe_query(
        "messages",
        "id,sender,metadata,created_at",
        "created_at",
        today_start,
        today_end,
    )
    events_today = _safe_query(
        "analytics_events",
        "id,event_type,payload,created_at",
        "created_at",
        today_start,
        today_end,
    )
    threads_today = _safe_query(
        "conversation_threads",
        "id,topic,status,metadata,created_at",
        "created_at",
        today_start,
        today_end,
    )

    total_today = len(sessions_today) + len(calls_today)
    total_yesterday = len(sessions_yesterday) + len(calls_yesterday)

    durations = []
    for session in sessions_today:
        started_at = _parse_timestamp(session.get("started_at"))
        ended_at = _parse_timestamp(session.get("ended_at"))
        if started_at and ended_at:
            durations.append((ended_at - started_at).total_seconds())
    durations.extend(
        call.get("duracion_segundos")
        for call in calls_today
        if isinstance(call.get("duracion_segundos"), (int, float))
    )
    avg_duration = sum(durations) / len(durations) if durations else None

    completed_sessions = sum(
        1 for session in sessions_today if session.get("status") == "completed"
    )
    completed_calls = sum(1 for call in calls_today if call.get("ended_at"))
    fcr_value = (
        round(((completed_sessions + completed_calls) / total_today) * 100)
        if total_today
        else None
    )

    ratings = [
        rating
        for event in events_today
        if (rating := _extract_rating(event.get("payload"))) is not None
    ]
    csat_value = sum(ratings) / len(ratings) if ratings else None

    lead_scores = [
        call.get("score_lead")
        for call in calls_today
        if isinstance(call.get("score_lead"), (int, float))
    ]
    avg_score = sum(lead_scores) / len(lead_scores) if lead_scores else None

    channel_counts = Counter(
        session.get("channel_type") or "desconocido" for session in sessions_today
    )
    # Legacy sesiones are all voice calls during transition period
    if calls_today:
        channel_counts["voice"] += len(calls_today)

    reason_counts = Counter()
    for call in calls_today:
        for service in call.get("servicios_interes") or []:
            if service:
                reason_counts[str(service)] += 1
    for thread in threads_today:
        topic = thread.get("topic")
        if topic:
            reason_counts[str(topic)] += 1

    hourly = {
        hour: {
            "hour": _hour_label(hour),
            "conversations": 0,
            "sentimentPositive": 0,
            "sentimentNegative": 0,
        }
        for hour in range(24)
    }
    for row in sessions_today + calls_today:
        started_at = _parse_timestamp(row.get("started_at") or row.get("created_at"))
        if started_at:
            hour = started_at.astimezone(BOGOTA_TZ).hour
            hourly[hour]["conversations"] += 1

    for message in messages_today:
        created_at = _parse_timestamp(message.get("created_at"))
        sentiment = _count_sentiment(message)
        if created_at and sentiment:
            hour = created_at.astimezone(BOGOTA_TZ).hour
            key = "sentimentPositive" if sentiment == "positive" else "sentimentNegative"
            hourly[hour][key] += 1

    overview = [
        {
            "id": "volume",
            "label": "Volumen total",
            "value": f"{total_today:,}",
            "detail": "conversaciones hoy · vs ayer",
            "trend": _trend(total_today, total_yesterday),
        },
        {
            "id": "csat",
            "label": "CSAT promedio",
            "value": f"{csat_value:.1f}" if csat_value is not None else "N/D",
            "detail": "de 5.0 · eventos Supabase",
            "trend": {"value": "N/D", "direction": "flat"},
        },
        {
            "id": "fcr",
            "label": "First contact res.",
            "value": f"{fcr_value}%" if fcr_value is not None else "N/D",
            "detail": "resuelto sin escalar",
            "trend": {"value": "N/D", "direction": "flat"},
        },
        {
            "id": "aht",
            "label": "AHT promedio",
            "value": _format_duration(avg_duration),
            "detail": "tiempo promedio de manejo",
            "trend": _trend(
                avg_duration,
                (
                    sum(
                        item.get("duracion_segundos", 0)
                        for item in calls_yesterday
                        if isinstance(item.get("duracion_segundos"), (int, float))
                    )
                    / len(calls_yesterday)
                    if calls_yesterday
                    else None
                ),
            ),
        },
    ]

    # Hot leads and escalation candidates (all time, not just today)
    leads_raw: list[dict] = []
    try:
        if supabase is not None:
            result = (
                supabase.table("sesiones")
                .select(
                    "id,score_lead,intention,servicios_interes,recomendaciones,started_at,"
                    "clientes(nombre,empresa,telefono)"
                )
                .order("score_lead", desc=True)
                .limit(60)
                .execute()
            )
            leads_raw = result.data or []
    except Exception as exc:
        logger.warning("Hot leads query failed: %s", exc)

    hot_leads = [
        _format_lead(r)
        for r in leads_raw
        if (r.get("score_lead") or 0) >= 70 or r.get("intention") == "caliente"
    ][:10]
    hot_ids = {r.get("id") for r in leads_raw if (r.get("score_lead") or 0) >= 70 or r.get("intention") == "caliente"}
    escalation_candidates = [
        _format_lead(r)
        for r in leads_raw
        if r.get("recomendaciones") and r.get("id") not in hot_ids
    ][:10]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "range": "today",
        "overview": overview,
        "volumeByHour": list(hourly.values()),
        "hotLeads": hot_leads,
        "escalationCandidates": escalation_candidates,
        "contactReasons": [
            {
                "label": label,
                "value": count,
                "percentage": round((count / total_today) * 100) if total_today else 0,
            }
            for label, count in reason_counts.most_common(6)
        ],
        "channels": [
            {
                "label": str(label).replace("_", " ").title(),
                "value": count,
                "percentage": round((count / total_today) * 100) if total_today else 0,
            }
            for label, count in channel_counts.most_common()
        ],
        "recommendations": _dashboard_recommendations(
            reason_counts,
            channel_counts,
            avg_score,
            total_today,
        ),
        "source": {
            "sessions": len(sessions_today),
            "calls": len(calls_today),
            "messages": len(messages_today),
            "events": len(events_today),
        },
    }


@app.get("/dashboard/clients")
async def dashboard_clients():
    """Lista de clientes con estadísticas agregadas de sus sesiones."""
    if supabase is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": "Supabase no configurado"})

    clients = _safe_query("clientes", "id,nombre,empresa,telefono,cedula,created_at")
    sessions = _safe_query(
        "sesiones",
        "id,cliente_id,started_at,score_lead,intention,duracion_segundos",
    )

    sessions_by_client: dict[int, list[dict]] = defaultdict(list)
    for session in sessions:
        cid = session.get("cliente_id")
        if cid is not None:
            sessions_by_client[cid].append(session)

    result = []
    for client in clients:
        cid = client["id"]
        client_sessions = sessions_by_client.get(cid, [])
        scores = [
            s["score_lead"]
            for s in client_sessions
            if isinstance(s.get("score_lead"), (int, float))
        ]
        intentions = [s["intention"] for s in client_sessions if s.get("intention")]
        last_session = max(
            (s for s in client_sessions if s.get("started_at")),
            key=lambda s: s["started_at"],
            default=None,
        )
        intention_priority = {"caliente": 3, "calida": 2, "fria": 1}
        best_intention = (
            max(intentions, key=lambda i: intention_priority.get(i, 0))
            if intentions
            else "fria"
        )
        result.append({
            "id": cid,
            "nombre": client["nombre"],
            "empresa": client.get("empresa") or "",
            "telefono": client.get("telefono") or "",
            "cedula": client.get("cedula") or "",
            "totalSessions": len(client_sessions),
            "lastSessionAt": last_session["started_at"] if last_session else None,
            "avgScore": round(sum(scores) / len(scores)) if scores else 0,
            "intention": best_intention,
        })

    result.sort(key=lambda c: c.get("lastSessionAt") or "", reverse=True)
    return {"clients": result}


@app.get("/dashboard/clients/{client_id}/sessions")
async def dashboard_client_sessions(client_id: int):
    """Historial completo de sesiones de un cliente."""
    if supabase is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": "Supabase no configurado"})

    try:
        result = (
            supabase.table("sesiones")
            .select(
                "id,started_at,ended_at,duracion_segundos,resumen,intention,"
                "score_lead,servicios_interes,recomendaciones"
            )
            .eq("cliente_id", client_id)
            .order("started_at", desc=True)
            .execute()
        )
        sessions = result.data or []
    except Exception as exc:
        logger.warning("Client sessions query failed: %s", exc)
        sessions = []

    return {
        "sessions": [
            {
                "id": s["id"],
                "startedAt": s.get("started_at"),
                "endedAt": s.get("ended_at"),
                "duracionSegundos": s.get("duracion_segundos"),
                "resumen": s.get("resumen") or "",
                "intention": s.get("intention") or "fria",
                "scoreLead": s.get("score_lead") or 0,
                "serviciosInteres": s.get("servicios_interes") or [],
                "recomendaciones": s.get("recomendaciones") or "",
            }
            for s in sessions
        ]
    }


@app.post("/chat/message")
async def chat_message(request: dict):
    """Endpoint de chat textual — usado por el frontend (ChatbotWidget)."""
    if not TEXT_AGENT_AVAILABLE:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"detail": "Text agent no disponible — verificá GEMINI_API_KEY"},
        )

    message = (request.get("message") or "").strip()
    session_id = request.get("session_id")
    model = request.get("model")
    ended_flag = request.get("ended", False)

    if not message:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=422,
            content={"detail": "El campo 'message' es obligatorio"},
        )

    # Recuperar o crear sesión
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
    else:
        session = TextAgentSession(model=model)
        _sessions[session.session_id] = session
        session_id = session.session_id

        # Create DB thread + session for persistence (REQ-5, REQ-7)
        await _ensure_chat_session_db(session)

    try:
        # Persist user message before sending to Gemini (REQ-6)
        if session.db_session_id:
            await orchestrator.memory.add_message(
                session.db_session_id,
                "user",
                message,
            )

        result = await session.send_message(message)

        # Persist agent response after Gemini replies (REQ-6)
        if session.db_session_id and result.get("reply"):
            await orchestrator.memory.add_message(
                session.db_session_id,
                "agent",
                result["reply"],
                metadata={"tool_calls": result.get("tool_calls", [])},
            )

        # Close session when conversation ends (REQ-7)
        if result.get("ended") or ended_flag:
            if session.db_session_id:
                await orchestrator.session_manager.close_session(session.db_session_id)

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Text agent error: {error_msg}")
        from fastapi.responses import JSONResponse

        status = 500
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            status = 429
            error_msg = (
                "Límite de uso de la API alcanzado. "
                "Intentá de nuevo en unos segundos."
            )
        elif "API_KEY" in error_msg or "API key" in error_msg:
            status = 401

        return JSONResponse(status_code=status, content={"detail": error_msg})

    return {
        "session_id": session_id,
        "reply": result["reply"],
        "tool_calls": result["tool_calls"],
        "ended": result["ended"],
    }


async def _ensure_chat_session_db(session: TextAgentSession) -> None:
    """Create a conversation_thread + conversation_session (webchat) for DB persistence.

    Called once when a new TextAgentSession is created. Sets db_session_id
    and db_thread_id on the session object for subsequent message persistence.
    """
    if supabase is None:
        logger.debug("Supabase not available — skipping chat session persistence")
        return

    try:
        # Webchat sessions are anonymous — create a new thread without a contact_id
        # (contact_id is nullable in conversation_threads; passing "webchat-anonymous"
        # would violate the UUID FK constraint)
        thread_result = supabase.table("conversation_threads").insert(
            {"topic": "Web chat session", "status": "active"}
        ).execute()
        thread = thread_result.data[0]

        chat_session = await orchestrator.session_manager.create_session(
            thread["id"],
            channel_type="webchat",
        )

        session.db_session_id = chat_session["id"]
        session.db_thread_id = thread["id"]
        logger.info(
            f"Chat DB session created: session={chat_session['id']}, "
            f"thread={thread['id']}"
        )
    except Exception as exc:
        logger.warning(f"Failed to create chat DB session: {exc}")
        # Graceful degrade — session works without persistence


@app.get("/twiml")
@app.post("/twiml")
async def twiml(request: Request):
    logger.info(f"[TWIML] Request from {request.client} method={request.method} headers={dict(request.headers)}")
    try:
        stream_url = _stream_url()
    except ValueError as exc:
        logger.error(f"[TWIML] Error: {exc}")
        return Response(content=str(exc), status_code=500, media_type="text/plain")
    logger.info(f"[TWIML] Responding with stream_url={stream_url}")
    return Response(
        content=TWIML_TEMPLATE.format(stream_url=stream_url),
        media_type="application/xml",
    )


@app.websocket("/twilio-stream")
async def twilio_stream(websocket: WebSocket):
    logger.info(f"[WS] WebSocket connection attempt from {websocket.client}")
    await websocket.accept()
    logger.info("[WS] WebSocket accepted — Twilio connected")

    gemini = GeminiLiveClient()
    logger.info("[WS] Connecting to Gemini Live...")
    await gemini.connect(
        tools=GOTOCLOUD_TOOLS,
        tool_handler=ejecutar_tool,
        system_instruction=SYSTEM_PROMPT,
        voice_name="Aoede",
    )
    logger.info(f"Gemini Live connected — tools={'activos' if GOTOCLOUD_TOOLS else 'sin tools'}")

    stream_sid: str | None = None
    stop_event = asyncio.Event()

    # Timer para fallback de timeout (60 segundos)
    timeout_task: asyncio.Task | None = None

    async def timeout_fallback():
        """Fallback: ejecutar registrar_resumen_llamada si no se ejecutó en 60s."""
        # No ejecutar si la llamada ya terminó (stop_event está seteado)
        if stop_event.is_set():
            return
        if ejecutar_tool:
            logger.warning("[timeout fallback] 60s sin actividad — invocando registrar_resumen_llamada")
            try:
                result = ejecutar_tool("registrar_resumen_llamada", {
                    "resumen": "Llamada finalizada por tiempo de espera.",
                    "intention": "calida",
                    "score_lead": 50,
                    "servicios_interes": [],
                    "recomendaciones": "Cliente no completó la conversación.",
                })
                logger.info(f"[timeout fallback] Resultado: {result}")
            except Exception as ex:
                logger.error(f"[timeout fallback] Error: {ex}")

    def reset_timeout_timer():
        """Reinicia el timer de 60 segundos."""
        nonlocal timeout_task
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        timeout_task = asyncio.create_task(timeout_fallback())

    # Iniciar timer al principio
    reset_timeout_timer()

    async def receive_from_twilio():
        nonlocal stream_sid
        try:
            while not stop_event.is_set():
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                event = msg.get("event")

                if event == "connected":
                    logger.info("Twilio connected (protocol handshake)")

                elif event == "start":
                    stream_sid = msg["start"]["streamSid"]
                    logger.info(f"Twilio start streamSid={stream_sid}")

                elif event == "media":
                    payload_b64 = msg["media"]["payload"]
                    try:
                        pcm = twilio_payload_to_gemini_pcm(payload_b64)
                        logger.debug(f"Twilio media received bytes={len(pcm)}")
                        await gemini.send_audio_pcm16_16k(pcm)
                        logger.debug(f"sent to Gemini bytes={len(pcm)}")
                        # Resetear timer de fallback al recibir audio
                        reset_timeout_timer()
                    except Exception as exc:
                        logger.warning(f"Audio conversion error (Twilio→Gemini): {exc}")

                elif event == "stop":
                    logger.info("Twilio stop")
                    stop_event.set()
                    # Cancelar el timer de fallback al terminar la llamada
                    if timeout_task and not timeout_task.done():
                        timeout_task.cancel()
                    break

        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected")
            stop_event.set()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"receive_from_twilio error: {exc}")
            stop_event.set()

    async def send_to_twilio():
        try:
            while not stop_event.is_set():
                async for pcm_chunk in gemini.receive_audio():
                    if stop_event.is_set():
                        break
                    if not stream_sid:
                        logger.debug("Gemini audio recibido, streamSid aún no disponible — descartando")
                        continue
                    try:
                        payload_b64 = gemini_pcm_to_twilio_payload(pcm_chunk, input_rate=24000)
                        logger.info(f"Gemini audio received bytes={len(pcm_chunk)}, sent to Twilio")
                        await websocket.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": payload_b64},
                        }))
                    except Exception as exc:
                        logger.warning(f"Audio conversion error (Gemini→Twilio): {exc}")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"send_to_twilio error: {exc}")
            stop_event.set()

    tasks = [
        asyncio.create_task(receive_from_twilio(), name="twilio_recv"),
        asyncio.create_task(send_to_twilio(), name="gemini_recv"),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        # Limpiar timer de fallback
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await gemini.close()
        logger.info("Gemini session closed")


# ─────────────────────────────────────────────────────────────
# WEB CLIENT — WebSocket para frontend web (sin Twilio)
# ─────────────────────────────────────────────────────────────
#
# PROTOCOLO:
#   Browser → Server : frames BINARIOS — PCM16 LE 16kHz (raw bytes del micrófono)
#   Server → Browser : frames BINARIOS — PCM16 LE 24kHz (audio de Gemini)
#                      frames TEXTO    — JSON con eventos:
#                        {"type": "status",     "value": "connected|listening|speaking|ended"}
#                        {"type": "transcript", "role": "user|model", "text": "..."}
#                        {"type": "tool",       "name": "...", "result": {...}}
#                        {"type": "error",      "message": "..."}
# ─────────────────────────────────────────────────────────────

async def _ws_send_json(ws: WebSocket, payload: dict):
    """Helper para enviar un frame JSON de texto al browser."""
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


@app.websocket("/web-stream")
async def web_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WEB] Browser conectado")

    await _ws_send_json(websocket, {"type": "status", "value": "connected"})

    gemini = GeminiLiveClient()

    # Wrapper del tool handler que también notifica al browser
    async def tool_handler_web(nombre: str, args: dict):
        result = ejecutar_tool(nombre, args) if ejecutar_tool else {"error": "tools no disponibles"}
        await _ws_send_json(websocket, {"type": "tool", "name": nombre, "result": result})
        return result

    async def transcript_cb(role: str, text: str) -> None:
        await _ws_send_json(websocket, {"type": "transcript", "role": role, "text": text})

    try:
        await gemini.connect(
            tools=GOTOCLOUD_TOOLS,
            tool_handler=ejecutar_tool,
            system_instruction=SYSTEM_PROMPT,
            voice_name="Aoede",
            transcript_callback=transcript_cb,
        )
    except Exception as exc:
        logger.error(f"[WEB] Error conectando Gemini: {exc}")
        await _ws_send_json(websocket, {"type": "error", "message": str(exc)})
        await websocket.close()
        return

    logger.info("[WEB] Gemini Live conectado")
    await _ws_send_json(websocket, {"type": "status", "value": "listening"})

    stop_event = asyncio.Event()

    async def receive_from_browser():
        """Recibe audio PCM16 16kHz del browser y lo envía a Gemini."""
        try:
            while not stop_event.is_set():
                data = await websocket.receive()
                if data["type"] == "websocket.disconnect":
                    stop_event.set()
                    break
                if "bytes" in data and data["bytes"]:
                    await gemini.send_audio_pcm16_16k(data["bytes"])
                elif "text" in data and data["text"]:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "stop":
                        logger.info("[WEB] Browser envió stop")
                        stop_event.set()
                        break
        except WebSocketDisconnect:
            logger.info("[WEB] Browser desconectado")
            stop_event.set()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"[WEB] receive_from_browser error: {exc}")
            stop_event.set()

    async def send_to_browser():
        """Recibe audio PCM16 24kHz de Gemini y lo envía al browser."""
        try:
            while not stop_event.is_set():
                await _ws_send_json(websocket, {"type": "status", "value": "speaking"})
                async for pcm_chunk in gemini.receive_audio():
                    if stop_event.is_set():
                        break
                    await websocket.send_bytes(pcm_chunk)
                await _ws_send_json(websocket, {"type": "status", "value": "listening"})
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"[WEB] send_to_browser error: {exc}")
            stop_event.set()

    tasks = [
        asyncio.create_task(receive_from_browser(), name="web_recv"),
        asyncio.create_task(send_to_browser(),      name="web_send"),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await gemini.close()
        await _ws_send_json(websocket, {"type": "status", "value": "ended"})
        logger.info("[WEB] Sesión cerrada")
