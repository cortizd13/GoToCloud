"""backend.conversion — Conversion rate improvement tools for agente Camila.

This package provides tools for:
- Scheduling appointments (agendar_cita)
- Lead qualification (calificar_necesidad)
- Email follow-up (enviar_email_seguimiento)
- Hot lead alerts (notificar_lead_caliente)
- CRM sync (consultar_crm, crear_lead_crm)

Phase 1: Stub implementations with TODO markers.
Phase 2-3: Full integrations (Calendly, SendGrid, HubSpot).
"""

from backend.conversion.tools import (
    agendar_cita,
    calificar_necesidad,
    consultar_crm,
    crear_lead_crm,
    enviar_email_seguimiento,
    notificar_lead_caliente,
)

__all__ = [
    "register_conversion_tools",
    "agendar_cita",
    "calificar_necesidad",
    "enviar_email_seguimiento",
    "notificar_lead_caliente",
    "consultar_crm",
    "crear_lead_crm",
]


def register_conversion_tools(tool_registry: dict | None = None) -> dict:
    """Register all conversion tools into the GOTOCLOUD_TOOLS registry.

    Args:
        tool_registry: Optional dict to register tools into.
            If None, returns a new dict with all tool mappings.

    Returns:
        Dict mapping tool names to handler functions.

    TODO: Integrate with gotocloud_voicebot_tool.py GOTOCLOUD_TOOLS.
    """
    registry = tool_registry or {}
    registry["agendar_cita"] = agendar_cita
    registry["calificar_necesidad"] = calificar_necesidad
    registry["enviar_email_seguimiento"] = enviar_email_seguimiento
    registry["notificar_lead_caliente"] = notificar_lead_caliente
    registry["consultar_crm"] = consultar_crm
    registry["crear_lead_crm"] = crear_lead_crm
    return registry
