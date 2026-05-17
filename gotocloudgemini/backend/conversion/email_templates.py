"""backend.conversion.email_templates — Email template placeholders.

Templates for follow-up emails sent by agente Camila after lead interactions.
Templates use {{variable}} syntax for interpolation.

Phase 1: Template placeholders only.
Phase 2: Full templates with professional branding and SendGrid integration.
"""

# ── Follow-up Template (Hot Lead) ────────────────────────────────────────────

FOLLOW_UP_TEMPLATE = """\
Asunto: Gracias por contactarte con GoToCloud - Próximos pasos

Hola {cliente_nombre},

Gracias por tu interés en GoToCloud. Fue un placer conversar contigo sobre {servicio_interes}.

Resumen de nuestra conversación:
{resumen_conversacion}

Próximo paso: {proximo_paso}

{link_cita}

Datos de contacto del asesor:
- Email: asesor@gotocloud.ai
- WhatsApp: +57 317 427 0148
- Web: https://www.gotocloud.ai

---
GoToCloud — Transformación digital con soluciones en la nube
Colombia | Estados Unidos | México | Ecuador | Perú | Argentina

Este email fue generado automáticamente por nuestro asistente Camila.
Si no deseas recibir más comunicaciones, responde con "BAJA".
"""

# ── Follow-up Template (Warm Lead) ───────────────────────────────────────────

FOLLOW_UP_WARM_TEMPLATE = """\
Asunto: Información sobre servicios de GoToCloud

Hola {cliente_nombre},

Gracias por tu tiempo. Te compartimos información sobre {servicio_interes}.

Próximo paso: {proximo_paso}

Cuando estés listo para avanzar, podemos agendar una cita personalizada:
{link_cita}

Saludos,
Equipo GoToCloud
"""

# ── Appointment Reminder Template ────────────────────────────────────────────

APPOINTMENT_REMINDER_TEMPLATE = """\
Asunto: Recordatorio de cita con GoToCloud

Hola {cliente_nombre},

Te recordamos tu cita agendada para {fecha_cita}.

Link de confirmación: {link_confirmacion}

Servicio de interés: {servicio_interes}

Saludos,
Equipo GoToCloud
"""

# ── Template Registry ────────────────────────────────────────────────────────

TEMPLATES = {
    "follow_up_caliente": FOLLOW_UP_TEMPLATE,
    "follow_up_tibio": FOLLOW_UP_WARM_TEMPLATE,
    "recordatorio_cita": APPOINTMENT_REMINDER_TEMPLATE,
}


def get_template(template_id: str) -> str:
    """Get a template by ID.

    Args:
        template_id: Template identifier.

    Returns:
        Template string.

    Raises:
        KeyError: If template_id is not found.
    """
    if template_id not in TEMPLATES:
        raise KeyError(f"Template '{template_id}' not found. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[template_id]
