"""backend.conversion.tools — Stub implementations for all 6 conversion tools.

All tools are Phase 1 stubs with TODO markers. They return placeholder
responses that match the expected contract from the design document.

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


# ── Tool: agendar_cita ───────────────────────────────────────────────────────


def agendar_cita(
    lead_id: str,
    servicio_interes: str | None = None,
    preferencias: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agenda una cita con un asesor de GoToCloud.

    TODO: Integrate with Calendly API for real scheduling.
    TODO: Persist appointment to agent_citas table in Supabase.
    TODO: Handle Calendly availability conflicts.

    Args:
        lead_id: ID del lead en Supabase.
        servicio_interes: Servicio o producto de interés.
        preferencias: Optional dict with dia_preferido, hora_preferida, tema.

    Returns:
        Dict with cita_creada, calendly_link, estado.
    """
    # TODO: Replace stub with real Calendly integration
    return {
        "cita_creada": False,
        "calendly_link": "https://calendly.com/gotocloud/asesoria",
        "estado": "pendiente",
        "error": "calendly_no_disponible",
        "mensaje": "Integración con Calendly pendiente de configurar.",
    }


# ── Tool: calificar_necesidad ────────────────────────────────────────────────


def calificar_necesidad(
    lead_id: str,
    presupuesto_estimado: str | None = None,
    timeline: str | None = None,
    urgencia: str | None = None,
) -> dict[str, Any]:
    """Captura presupuesto estimado, timeline de decisión y urgencia del lead.

    TODO: Persist qualification data to conversation_threads / sesiones.
    TODO: Trigger auto-scoring based on captured data.

    Args:
        lead_id: ID del lead en Supabase.
        presupuesto_estimado: Rango de presupuesto.
        timeline: Timeline de decisión.
        urgencia: Nivel de urgencia (alta, media, baja).

    Returns:
        Dict with calificado status and captured fields.
    """
    # TODO: Replace stub with real Supabase persistence
    return {
        "calificado": False,
        "lead_id": lead_id,
        "presupuesto_estimado": presupuesto_estimado,
        "timeline": timeline,
        "urgencia": urgencia,
        "mensaje": "Captura de calificación pendiente de implementar.",
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

    TODO: Send webhook POST to LEAD_ALERT_WEBHOOK_URL.
    TODO: Log alert to lead_alerts_log table.
    TODO: Implement retry logic with exponential backoff.

    Args:
        lead_id: ID del lead en Supabase.
        score_lead: Score 0-100.
        canal: Channel type (voice, whatsapp, webchat).
        intencion: Lead intention classification.

    Returns:
        Dict with alerta_enviada status.
    """
    # TODO: Replace stub with real webhook dispatch
    return {
        "alerta_enviada": False,
        "lead_id": lead_id,
        "score_lead": score_lead,
        "canal": canal,
        "mensaje": "Webhook de alerta pendiente de configurar.",
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
