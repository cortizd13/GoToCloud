"""backend.conversion.tools — Conversion tool implementations.

Tools:
- agendar_cita: Schedule appointment via Calendly
- calificar_necesidad: Capture budget, timeline, urgency
- enviar_email_seguimiento: Send follow-up email via SendGrid
- notificar_lead_caliente: Alert sales team via webhook
- consultar_crm: Look up lead in external CRM
- crear_lead_crm: Create lead in external CRM
"""

from __future__ import annotations

from typing import Any

# Import compatibility: works with sys.path (standalone) and package-relative (main.py)
try:
    from backend.supabase_client import supabase
except ImportError:
    try:
        from supabase_client import supabase
    except ImportError:
        supabase = None

from backend.conversion.scheduling import CalendlyIntegration
from backend.conversion.alerts import LeadAlertDispatcher


# ── Tool: agendar_cita ───────────────────────────────────────────────────────


def agendar_cita(
    lead_id: str,
    servicio_interes: str | None = None,
    preferencias: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agenda una cita con un asesor de GoToCloud.

    Uses CalendlyIntegration to generate a scheduling link and persist
    the appointment to the agent_citas table.

    Args:
        lead_id: ID del lead en Supabase.
        servicio_interes: Servicio o producto de interés.
        preferencias: Optional dict with dia_preferido, hora_preferida, tema.

    Returns:
        Dict with cita_creada, calendly_link, estado.
    """
    calendly = CalendlyIntegration()
    return calendly.create_event(
        lead_id=lead_id,
        service=servicio_interes,
        preferences=preferencias,
    )


# ── Tool: calificar_necesidad ────────────────────────────────────────────────


def calificar_necesidad(
    lead_id: str,
    presupuesto_estimado: str | None = None,
    timeline: str | None = None,
    urgencia: str | None = None,
    decision_maker: bool | None = None,
) -> dict[str, Any]:
    """Captura presupuesto estimado, timeline de decisión y urgencia del lead.

    Persists qualification data to conversation_threads table in Supabase.

    Args:
        lead_id: ID del lead (conversation_threads UUID).
        presupuesto_estimado: Rango de presupuesto.
        timeline: Timeline de decisión.
        urgencia: Nivel de urgencia (alta, media, baja).
        decision_maker: Whether the lead is a decision maker.

    Returns:
        Dict with calificado status and captured fields.
    """
    calificado = False

    if supabase is not None:
        try:
            update_data: dict[str, Any] = {}
            if presupuesto_estimado is not None:
                update_data["presupuesto_estimado"] = presupuesto_estimado
            if timeline is not None:
                update_data["timeline"] = timeline
            if decision_maker is not None:
                update_data["decision_maker"] = decision_maker

            if update_data:
                result = supabase.table("conversation_threads").update(update_data).eq("id", lead_id).execute()
                if result.data:
                    calificado = True
                    print(f"[calificar_necesidad] Lead {lead_id} qualified: {update_data}")
            else:
                # No data to update, but still mark as calificado
                calificado = True
        except Exception as ex:
            print(f"[calificar_necesidad] Error saving qualification: {ex}")
    else:
        print(f"[calificar_necesidad] Supabase not available — qualification logged only")
        calificado = True  # Accept the data even without DB

    return {
        "calificado": calificado,
        "lead_id": lead_id,
        "presupuesto_estimado": presupuesto_estimado,
        "timeline": timeline,
        "urgencia": urgencia,
        "decision_maker": decision_maker,
    }


# ── Tool: enviar_email_seguimiento ───────────────────────────────────────────


def enviar_email_seguimiento(
    lead_id: str,
    template_id: str = "follow_up_caliente",
) -> dict[str, Any]:
    """Envía email de follow-up al lead con resumen y próximos pasos.

    TODO: Integrate with SendGrid API for real email delivery.
    TODO: Load template from email_templates.py and interpolate variables.
    TODO: Log email status to email_logs table.

    Args:
        lead_id: ID del lead en Supabase.
        template_id: Template to use (follow_up_caliente, follow_up_tibio, recordatorio_cita).

    Returns:
        Dict with email_sent status.
    """
    # TODO: Replace stub with real SendGrid integration
    return {
        "email_enviado": False,
        "lead_id": lead_id,
        "template_id": template_id,
        "mensaje": "Integración con SendGrid pendiente de configurar.",
    }


# ── Tool: notificar_lead_caliente ────────────────────────────────────────────


def notificar_lead_caliente(
    lead_id: str,
    score_lead: int,
    canal: str = "voice",
    intencion: str | None = None,
) -> dict[str, Any]:
    """Alerta a vendedor sobre lead con alta intención de compra.

    Uses LeadAlertDispatcher to send webhook POST with retry logic
    and logs to lead_alerts_log table.

    Args:
        lead_id: ID del lead en Supabase.
        score_lead: Score 0-100.
        canal: Channel type (voice, whatsapp, webchat).
        intencion: Lead intention classification.

    Returns:
        Dict with alerta_enviada status.
    """
    dispatcher = LeadAlertDispatcher()

    # Build the alert payload
    payload = dispatcher._build_payload(
        lead_id=lead_id,
        score=score_lead,
        lead_data={"lead_id": lead_id, "canal": canal, "intencion": intencion},
        session_data={"channel": canal},
        qualification={"score_lead": score_lead, "intencion": intencion},
    )

    result = dispatcher.send_alert(
        lead_id=lead_id,
        score=score_lead,
        payload=payload,
        intention=intencion,
    )

    return {
        "alerta_enviada": result.get("status") == "enviada",
        "lead_id": lead_id,
        "score_lead": score_lead,
        "canal": canal,
        "status": result.get("status", "unknown"),
        "mensaje": result.get("mensaje", ""),
    }


# ── Tool: consultar_crm ──────────────────────────────────────────────────────


def consultar_crm(
    lead_id: str,
    crm_tipo: str = "hubspot",
) -> dict[str, Any]:
    """Consulta estado de lead en CRM externo (HubSpot).

    TODO: Integrate with HubSpot API via CRMProvider interface.
    TODO: Map Supabase fields to CRM fields.

    Args:
        lead_id: ID del lead en Supabase.
        crm_tipo: CRM type (hubspot).

    Returns:
        Dict with CRM lookup results.
    """
    # TODO: Replace stub with real CRMProvider.get_lead()
    return {
        "success": False,
        "cliente_encontrado": False,
        "lead_id": lead_id,
        "crm_tipo": crm_tipo,
        "mensaje": "Integración con CRM pendiente de configurar.",
    }


# ── Tool: crear_lead_crm ─────────────────────────────────────────────────────


def crear_lead_crm(
    lead_id: str,
    crm_tipo: str = "hubspot",
) -> dict[str, Any]:
    """Sincroniza lead con CRM externo.

    TODO: Integrate with HubSpot API via CRMProvider interface.
    TODO: Map Supabase fields to CRM fields.
    TODO: Log sync status to crm_sync_log table.

    Args:
        lead_id: ID del lead en Supabase.
        crm_tipo: CRM type (hubspot).

    Returns:
        Dict with CRM creation results.
    """
    # TODO: Replace stub with real CRMProvider.create_lead()
    return {
        "success": False,
        "lead_id": lead_id,
        "crm_tipo": crm_tipo,
        "mensaje": "Integración con CRM pendiente de configurar.",
    }
