"""
WhatsApp handler via Twilio.
Recibe mensajes de WhatsApp (webhook), los envía a Camila (TextAgentSession),
y responde al usuario por WhatsApp. También envía mensajes de seguimiento
post-llamada.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

_twilio_client: Any | None = None


def _get_twilio_client() -> Any | None:
    global _twilio_client
    if _twilio_client is not None:
        return _twilio_client
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_ACCOUNT_SID o TWILIO_AUTH_TOKEN no configurados")
        return None
    from twilio.rest import Client

    _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio_client


# Sesiones de WhatsApp por número de teléfono (sin prefijo whatsapp:)
_whatsapp_sessions: dict[str, Any] = {}


async def handle_whatsapp_message(from_number: str, body: str) -> str:
    """
    Procesa un mensaje entrante de WhatsApp y devuelve la respuesta de Camila.
    from_number debe venir limpio (sin prefijo whatsapp:).
    """
    try:
        from .text_agent_client import TextAgentSession
    except ImportError:
        logger.error("TextAgentSession no disponible")
        return (
            "Lo siento, el servicio de chat no está disponible en este momento."
        )

    session = _whatsapp_sessions.get(from_number)
    if session is None or getattr(session, "ended", False):
        session = TextAgentSession()
        _whatsapp_sessions[from_number] = session
        # Persistencia en DB (lazy import para evitar circular)
        try:
            from .main import _ensure_chat_session_db

            await _ensure_chat_session_db(session)
        except Exception as exc:
            logger.warning(f"WhatsApp DB session creation failed: {exc}")

    # Persistir mensaje del usuario
    if getattr(session, "db_session_id", None):
        try:
            from .main import orchestrator

            await orchestrator.memory.add_message(
                session.db_session_id, "user", body
            )
        except Exception as exc:
            logger.warning(f"WhatsApp persist user msg failed: {exc}")

    result = await session.send_message(body)

    # Persistir respuesta del agente
    if getattr(session, "db_session_id", None) and result.get("reply"):
        try:
            from .main import orchestrator

            await orchestrator.memory.add_message(
                session.db_session_id,
                "agent",
                result["reply"],
                metadata={"tool_calls": result.get("tool_calls", [])},
            )
        except Exception as exc:
            logger.warning(f"WhatsApp persist agent msg failed: {exc}")

    if result.get("ended") and getattr(session, "db_session_id", None):
        try:
            from .main import orchestrator

            await orchestrator.session_manager.close_session(
                session.db_session_id
            )
        except Exception as exc:
            logger.warning(f"WhatsApp close session failed: {exc}")

    return result.get("reply", "Lo siento, no pude procesar tu mensaje.")


async def send_whatsapp_message(to_number: str, body: str) -> bool:
    """
    Envía un mensaje de WhatsApp a un número vía Twilio.
    to_number debe ser E.164 sin prefijo whatsapp: (ej: +573174270148).
    """
    client = _get_twilio_client()
    if not client:
        logger.error(
            "No se pudo enviar mensaje de WhatsApp: Twilio no configurado"
        )
        return False

    from_wa = TWILIO_WHATSAPP_NUMBER
    if not from_wa:
        logger.error("TWILIO_WHATSAPP_NUMBER no configurado")
        return False

    to_wa = (
        to_number
        if to_number.startswith("whatsapp:")
        else f"whatsapp:{to_number}"
    )

    try:
        loop = asyncio.get_running_loop()
        message = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                from_=from_wa,
                body=body,
                to=to_wa,
            ),
        )
        logger.info(f"WhatsApp enviado a {to_wa}, sid={message.sid}")
        return True
    except Exception as exc:
        logger.error(f"Error enviando WhatsApp a {to_wa}: {exc}")
        return False
