"""backend.conversion.email — SendGrid email integration stub.

Phase 1: Stub implementation with TODO markers.
Phase 2: Full SendGrid API integration with template interpolation.
"""

from __future__ import annotations

from typing import Any

from backend.conversion.email_templates import FOLLOW_UP_TEMPLATE


class EmailSender:
    """Email sender using SendGrid API.

    TODO: Implement real SendGrid API calls:
    - POST /v3/mail/send for email delivery
    - Template interpolation using email_templates.py
    - Bounce and open tracking

    TODO: Store SENDGRID_API_KEY in .env.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize SendGrid email sender.

        Args:
            api_key: SendGrid API key. If None, reads from env.
        """
        # TODO: Load API key from environment variable
        self.api_key = api_key

    def send(
        self,
        to_email: str,
        subject: str,
        template_id: str = "follow_up_caliente",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an email using a template.

        TODO: Load template, interpolate variables, send via SendGrid.
        TODO: Log email status to email_logs table.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            template_id: Template identifier.
            context: Variables for template interpolation.

        Returns:
            Dict with send status.
        """
        # TODO: Replace stub with real SendGrid API call
        return {
            "success": False,
            "to_email": to_email,
            "subject": subject,
            "template_id": template_id,
            "mensaje": "SendGrid integration not yet configured.",
        }

    def render_template(self, template: str, context: dict[str, Any]) -> str:
        """Render an email template with variable interpolation.

        Args:
            template: Template string with {{variable}} placeholders.
            context: Dict of variable values.

        Returns:
            Rendered template string.
        """
        # TODO: Replace with proper template engine (Jinja2 or similar)
        result = template
        for key, value in context.items():
            # Support both {{key}} and {key} placeholder formats
            result = result.replace(f"{{{{{key}}}}}", str(value))
            result = result.replace(f"{{{key}}}", str(value))
        return result
