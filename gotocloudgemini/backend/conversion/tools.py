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
from backend.conversion.email import EmailSender
from backend.conversion.crm import get_crm_provider, CRMProvider


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

    Looks up the lead's email from conversation_threads metadata,
    renders the appropriate template, and sends via SendGrid/Resend.
    Logs the result to email_logs table.

    Args:
        lead_id: ID del lead en Supabase (conversation_threads UUID).
        template_id: Template to use (follow_up_caliente, follow_up_tibio, recordatorio_cita).

    Returns:
        Dict with email_enviado status and details.
    """
    if not lead_id:
        return {"error": "lead_id es requerido para enviar_email_seguimiento"}

    # Look up lead data from Supabase
    lead_email = None
    lead_nombre = None
    lead_servicios = []

    if supabase is not None:
        try:
            result = supabase.table("conversation_threads").select("id, metadata").eq("id", lead_id).execute()
            if result.data and len(result.data) > 0:
                metadata = result.data[0].get("metadata", {})
                if isinstance(metadata, dict):
                    lead_email = metadata.get("email")
                    lead_nombre = metadata.get("nombre")
                    lead_servicios = metadata.get("servicios_interes", [])
        except Exception as ex:
            print(f"[enviar_email_seguimiento] Error looking up lead: {ex}")

    if not lead_email:
        return {
            "email_enviado": False,
            "lead_id": lead_id,
            "template_id": template_id,
            "razon": "email_no_disponible",
            "mensaje": "No se encontró email para este lead.",
        }

    # Build context for template interpolation
    context = {
        "nombre_cliente": lead_nombre or "cliente",
        "servicio_interes": ", ".join(lead_servicios) if lead_servicios else "nuestros servicios",
        "proximo_paso": "Un asesor de GoToCloud se comunicará contigo pronto.",
        "link_cita": "https://calendly.com/gotocloud/asesoria",
    }

    # Send email
    sender = EmailSender()
    send_result = sender.send(
        to_email=lead_email,
        subject=f"Gracias por contactarte con GoToCloud - Próximos pasos",
        template_id=template_id,
        context=context,
    )

    return {
        "email_enviado": send_result.get("success", False),
        "lead_id": lead_id,
        "template_id": template_id,
        "destinatario": lead_email,
        "razon": send_result.get("razon") if not send_result.get("success") else None,
        "mensaje": send_result.get("mensaje", "Email enviado correctamente" if send_result.get("success") else ""),
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
    lead_id: str = "",
    identificador: str = "",
    tipo: str = "email",
    crm_tipo: str = "hubspot",
) -> dict[str, Any]:
    """Consulta estado de lead en CRM externo (HubSpot).

    Searches for an existing contact in the CRM by email or cedula.
    Logs the lookup attempt to crm_sync_log table.

    Args:
        lead_id: ID del lead en Supabase (optional, for logging).
        identificador: Email or cedula to search for.
        tipo: Type of identifier ('email', 'cedula').
        crm_tipo: CRM type (hubspot).

    Returns:
        Dict with CRM lookup results.
    """
    if not identificador and not lead_id:
        return {"error": "identificador o lead_id es requerido para consultar_crm"}

    try:
        provider = get_crm_provider(crm_tipo)
    except ValueError as ex:
        return {"error": str(ex)}

    # If only lead_id provided, look up email from Supabase first
    search_id = identificador
    search_type = tipo

    if not search_id and lead_id and supabase is not None:
        try:
            result = supabase.table("conversation_threads").select("id, metadata").eq("id", lead_id).execute()
            if result.data and len(result.data) > 0:
                metadata = result.data[0].get("metadata", {})
                if isinstance(metadata, dict):
                    search_id = metadata.get("email", "")
                    search_type = "email"
        except Exception as ex:
            print(f"[consultar_crm] Error looking up lead: {ex}")

    if not search_id:
        return {
            "success": False,
            "cliente_encontrado": False,
            "razon": "identificador_no_disponible",
        }

    return provider.get_lead(search_id, identifier_type=search_type)


# ── Tool: crear_lead_crm ─────────────────────────────────────────────────────


def crear_lead_crm(
    lead_id: str = "",
    crm_tipo: str = "hubspot",
    nombre: str = "",
    email: str = "",
    telefono: str = "",
    empresa: str = "",
    servicios_interes: list[str] | None = None,
    presupuesto: str = "",
    timeline: str = "",
    score_lead: int = 0,
    intencion: str = "",
) -> dict[str, Any]:
    """Sincroniza lead con CRM externo.

    Creates a new lead in the CRM with the provided data.
    If only lead_id is provided, looks up data from Supabase first.
    Logs the sync attempt to crm_sync_log table.

    Args:
        lead_id: ID del lead en Supabase.
        crm_tipo: CRM type (hubspot).
        nombre: Lead's full name.
        email: Lead's email.
        telefono: Lead's phone.
        empresa: Lead's company.
        servicios_interes: Services of interest.
        presupuesto: Budget range.
        timeline: Decision timeline.
        score_lead: Lead score 0-100.
        intencion: Lead intention classification.

    Returns:
        Dict with CRM creation results.
    """
    if not lead_id and not (nombre and email):
        return {"error": "lead_id o (nombre + email) es requerido para crear_lead_crm"}

    # If only lead_id provided, look up data from Supabase
    lead_data = {
        "nombre": nombre,
        "email": email,
        "telefono": telefono,
        "empresa": empresa,
    }

    if lead_id and supabase is not None and not nombre:
        try:
            result = supabase.table("conversation_threads").select("id, metadata").eq("id", lead_id).execute()
            if result.data and len(result.data) > 0:
                metadata = result.data[0].get("metadata", {})
                if isinstance(metadata, dict):
                    lead_data["nombre"] = metadata.get("nombre", nombre)
                    lead_data["email"] = metadata.get("email", email)
                    lead_data["telefono"] = metadata.get("telefono", telefono)
                    lead_data["empresa"] = metadata.get("empresa", empresa)
        except Exception as ex:
            print(f"[crear_lead_crm] Error looking up lead: {ex}")

    try:
        provider = get_crm_provider(crm_tipo)
    except ValueError as ex:
        return {"error": str(ex)}

    return provider.create_lead(lead_data)
