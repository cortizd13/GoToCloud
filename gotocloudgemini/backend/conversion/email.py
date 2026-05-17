"""backend.conversion.email — SendGrid/Resend email integration.

Phase 2: Full email delivery via SendGrid or Resend REST API.
Supports template interpolation, email_logs logging, and graceful degrade.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from backend.conversion.email_templates import TEMPLATES, get_template

# Import compatibility: works with sys.path (standalone) and package-relative (main.py)
try:
    from backend.supabase_client import supabase
except ImportError:
    try:
        from supabase_client import supabase
    except ImportError:
        supabase = None


class EmailSender:
    """Email sender using SendGrid or Resend REST API.

    Reads API key from SENDGRID_API_KEY or RESEND_API_KEY env var.
    Falls back gracefully if no API key is configured.
    """

    SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
    RESEND_URL = "https://api.resend.com/emails"
    FROM_EMAIL = "camila@gotocloud.ai"
    FROM_NAME = "Camila — GoToCloud"

    def __init__(self, api_key: str | None = None, provider: str | None = None):
        """Initialize email sender.

        Args:
            api_key: API key. If None, reads from env vars.
            provider: 'sendgrid' or 'resend'. Auto-detected from env if None.
        """
        if api_key:
            self.api_key = api_key
            self.provider = provider or "sendgrid"
        else:
            self.api_key = os.environ.get("SENDGRID_API_KEY") or os.environ.get("RESEND_API_KEY")
            if self.api_key and self.api_key.startswith("re_"):
                self.provider = "resend"
            else:
                self.provider = provider or "sendgrid"

    def send(
        self,
        to_email: str,
        subject: str,
        template_id: str = "follow_up_caliente",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an email using a template.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            template_id: Template identifier from TEMPLATES registry.
            context: Variables for template interpolation.

        Returns:
            Dict with success status, to_email, subject, and optional error details.
        """
        context = context or {}

        # Graceful degrade: no API key configured
        if not self.api_key:
            self._log_email(to_email, subject, template_id, status="error", error="email_no_configurado")
            return {
                "success": False,
                "razon": "email_no_configurado",
                "to_email": to_email,
                "subject": subject,
                "template_id": template_id,
            }

        # Build email body from template
        try:
            template_str = get_template(template_id)
        except KeyError:
            return {
                "success": False,
                "razon": f"template_no_encontrado: {template_id}",
                "to_email": to_email,
            }

        body = self.render_template(template_str, context)

        # Extract subject from template if it starts with "Asunto:"
        if body.startswith("Asunto:"):
            lines = body.split("\n", 1)
            template_subject = lines[0].replace("Asunto:", "").strip()
            body = lines[1] if len(lines) > 1 else ""
        else:
            template_subject = subject

        try:
            if self.provider == "resend":
                result = self._send_resend(to_email, template_subject or subject, body)
            else:
                result = self._send_sendgrid(to_email, template_subject or subject, body)

            self._log_email(to_email, template_subject or subject, template_id, status=result.get("status", "enviado"))
            return result

        except Exception as ex:
            self._log_email(to_email, template_subject or subject, template_id, status="error", error=str(ex))
            return {
                "success": False,
                "status": "error",
                "to_email": to_email,
                "subject": template_subject or subject,
                "template_id": template_id,
                "mensaje": str(ex),
            }

    def _send_sendgrid(self, to_email: str, subject: str, body: str) -> dict[str, Any]:
        """Send via SendGrid REST API."""
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.FROM_EMAIL, "name": self.FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }

        response = requests.post(
            self.SENDGRID_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 202):
            return {
                "success": True,
                "status": "enviado",
                "to_email": to_email,
                "subject": subject,
                "provider": "sendgrid",
            }
        else:
            return {
                "success": False,
                "status": "error",
                "to_email": to_email,
                "subject": subject,
                "mensaje": f"SendGrid HTTP {response.status_code}: {response.text[:200]}",
            }

    def _send_resend(self, to_email: str, subject: str, body: str) -> dict[str, Any]:
        """Send via Resend REST API."""
        payload = {
            "from": f"{self.FROM_NAME} <{self.FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        }

        response = requests.post(
            self.RESEND_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 201):
            return {
                "success": True,
                "status": "enviado",
                "to_email": to_email,
                "subject": subject,
                "provider": "resend",
            }
        else:
            return {
                "success": False,
                "status": "error",
                "to_email": to_email,
                "subject": subject,
                "mensaje": f"Resend HTTP {response.status_code}: {response.text[:200]}",
            }

    def render_template(self, template: str, context: dict[str, Any]) -> str:
        """Render an email template with {{variable}} interpolation.

        Args:
            template: Template string with {{variable}} placeholders.
            context: Dict of variable values.

        Returns:
            Rendered template string.
        """
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def _log_email(
        self,
        to_email: str,
        subject: str,
        template_id: str,
        status: str = "enviado",
        error: str | None = None,
    ) -> None:
        """Log email send attempt to email_logs table."""
        if supabase is None:
            return

        try:
            log_data = {
                "destinatario": to_email,
                "subject": subject,
                "status": status,
                "template_used": template_id,
            }
            supabase.table("email_logs").insert(log_data).execute()
        except Exception as ex:
            print(f"[EmailSender] Error logging to email_logs: {ex}")
