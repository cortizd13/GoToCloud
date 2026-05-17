"""Tests for PR Slice #4: Email Follow-up (T-108).

These tests validate:
- T-108.1: EmailSender.send() with SendGrid/Resend integration
- T-108.2: Template interpolation
- T-108.3: Email logging to email_logs table
- T-108.4: Graceful degrade when no API key
- T-108.5: enviar_email_seguimiento tool wiring
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend"


@pytest.fixture(autouse=True)
def add_backend_to_path():
    """Ensure backend/ is importable."""
    backend_dir = str(BACKEND_PATH.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    yield


# ── T-108.1: EmailSender.send() ──────────────────────────────────────────────


class TestEmailSenderInit:
    """T-108.1.1: EmailSender must load API key from env vars."""

    def test_init_with_explicit_api_key(self):
        """When api_key is passed, use it directly."""
        from backend.conversion.email import EmailSender
        sender = EmailSender(api_key="test-key-123")
        assert sender.api_key == "test-key-123"

    def test_init_loads_sendgrid_from_env(self):
        """When no api_key, load SENDGRID_API_KEY from env."""
        with patch.dict(os.environ, {"SENDGRID_API_KEY": "sg-key-456"}, clear=False):
            from backend.conversion.email import EmailSender
            sender = EmailSender()
            assert sender.api_key == "sg-key-456"

    def test_init_loads_resend_from_env(self):
        """When no SENDGRID_API_KEY, load RESEND_API_KEY from env."""
        # Ensure SENDGRID is not set
        original_sg = os.environ.pop("SENDGRID_API_KEY", None)
        try:
            with patch.dict(os.environ, {"RESEND_API_KEY": "re-key-789"}, clear=False):
                from backend.conversion.email import EmailSender
                sender = EmailSender()
                assert sender.api_key == "re-key-789"
        finally:
            if original_sg is not None:
                os.environ["SENDGRID_API_KEY"] = original_sg

    def test_init_no_api_key_available(self):
        """When no env vars set, api_key should be None."""
        original_sg = os.environ.pop("SENDGRID_API_KEY", None)
        original_re = os.environ.pop("RESEND_API_KEY", None)
        try:
            from backend.conversion.email import EmailSender
            sender = EmailSender()
            assert sender.api_key is None
        finally:
            if original_sg is not None:
                os.environ["SENDGRID_API_KEY"] = original_sg
            if original_re is not None:
                os.environ["RESEND_API_KEY"] = original_re


class TestEmailSenderRenderTemplate:
    """T-108.2: Template interpolation must replace {{variable}} placeholders."""

    def test_render_single_placeholder(self):
        """Single placeholder must be replaced."""
        from backend.conversion.email import EmailSender
        sender = EmailSender()
        result = sender.render_template("Hola {{nombre}}", {"nombre": "Juan"})
        assert result == "Hola Juan"

    def test_render_multiple_placeholders(self):
        """Multiple placeholders must all be replaced."""
        from backend.conversion.email import EmailSender
        sender = EmailSender()
        result = sender.render_template(
            "Hola {{nombre}}, tu servicio es {{servicio}}",
            {"nombre": "Juan", "servicio": "Kármán"},
        )
        assert "Hola Juan" in result
        assert "Kármán" in result

    def test_render_unknown_placeholder_unchanged(self):
        """Unknown placeholders should remain in output."""
        from backend.conversion.email import EmailSender
        sender = EmailSender()
        result = sender.render_template("Hola {{nombre}} {{desconocido}}", {"nombre": "Juan"})
        assert "Hola Juan" in result
        assert "{{desconocido}}" in result


class TestEmailSenderSend:
    """T-108.1.2: EmailSender.send() must send via SendGrid or Resend API."""

    @patch("backend.conversion.email.requests.post")
    def test_send_with_sendgrid_api_key(self, mock_post):
        """With SENDGRID_API_KEY, use SendGrid API endpoint."""
        from backend.conversion.email import EmailSender

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sender = EmailSender(api_key="sg-test-key")
        result = sender.send(
            to_email="juan@test.com",
            subject="Test Subject",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan", "proximo_paso": "Llamada con asesor"},
        )

        # Verify SendGrid endpoint was called
        mock_post.assert_called_once()
        # url is the first positional argument
        called_url = mock_post.call_args[0][0] if mock_post.call_args[0] else mock_post.call_args[1].get("url", "")
        assert "api.sendgrid.com" in called_url
        assert result["success"] is True

    @patch("backend.conversion.email.requests.post")
    def test_send_with_resend_api_key(self, mock_post):
        """With RESEND_API_KEY (no SENDGRID), use Resend API endpoint."""
        from backend.conversion.email import EmailSender

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sender = EmailSender(api_key="re-test-key", provider="resend")
        result = sender.send(
            to_email="juan@test.com",
            subject="Test Subject",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )

        mock_post.assert_called_once()
        assert result["success"] is True

    def test_send_without_api_key_returns_graceful_degrade(self):
        """Without API key, return graceful degrade response."""
        from backend.conversion.email import EmailSender
        sender = EmailSender(api_key=None)
        result = sender.send(
            to_email="juan@test.com",
            subject="Test",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )
        assert result["success"] is False
        assert result["razon"] == "email_no_configurado"

    @patch("backend.conversion.email.requests.post")
    def test_send_handles_api_error(self, mock_post):
        """API error should not crash — return error status."""
        from backend.conversion.email import EmailSender

        mock_post.side_effect = Exception("API timeout")

        sender = EmailSender(api_key="sg-test-key")
        result = sender.send(
            to_email="juan@test.com",
            subject="Test",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )

        assert result["success"] is False
        assert result["status"] == "error"

    @patch("backend.conversion.email.requests.post")
    def test_send_handles_400_response(self, mock_post):
        """400 response should return error status."""
        from backend.conversion.email import EmailSender

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        sender = EmailSender(api_key="sg-test-key")
        result = sender.send(
            to_email="juan@test.com",
            subject="Test",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )

        assert result["success"] is False
        assert result["status"] == "error"


class TestEmailSenderLogsToSupabase:
    """T-108.3: Email send must log to email_logs table."""

    @patch("backend.conversion.email.supabase")
    @patch("backend.conversion.email.requests.post")
    def test_send_logs_to_email_logs_on_success(self, mock_post, mock_supabase):
        """Successful send must insert into email_logs."""
        from backend.conversion.email import EmailSender

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])

        sender = EmailSender(api_key="sg-test-key")
        sender._supabase = mock_supabase  # Inject mock
        result = sender.send(
            to_email="juan@test.com",
            subject="Test Subject",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )

        mock_supabase.table.assert_called_with("email_logs")
        assert result["success"] is True

    @patch("backend.conversion.email.supabase")
    @patch("backend.conversion.email.requests.post")
    def test_send_logs_error_to_email_logs(self, mock_post, mock_supabase):
        """Failed send must log error to email_logs."""
        from backend.conversion.email import EmailSender

        mock_post.side_effect = Exception("API error")
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-2"}])

        sender = EmailSender(api_key="sg-test-key")
        sender._supabase = mock_supabase
        result = sender.send(
            to_email="juan@test.com",
            subject="Test",
            template_id="follow_up_caliente",
            context={"nombre_cliente": "Juan"},
        )

        # Should still log even on error
        mock_supabase.table.assert_called_with("email_logs")
        assert result["success"] is False


# ── T-108.5: enviar_email_seguimiento tool wiring ────────────────────────────


class TestEnviarEmailSeguimientoTool:
    """T-108.5: enviar_email_seguimiento tool must delegate to EmailSender."""

    @patch("backend.conversion.tools.EmailSender")
    def test_enviar_email_seguimiento_returns_dict(self, mock_sender_class):
        """Tool must return a dict."""
        from backend.conversion.tools import enviar_email_seguimiento
        result = enviar_email_seguimiento(lead_id="test-lead", template_id="follow_up_caliente")
        assert isinstance(result, dict)

    @patch("backend.conversion.tools.supabase")
    @patch("backend.conversion.tools.EmailSender")
    def test_enviar_email_seguimiento_looks_up_lead_email(self, mock_sender_class, mock_supabase):
        """Tool must look up lead email from conversation_threads."""
        from backend.conversion.tools import enviar_email_seguimiento

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "thread-1", "metadata": {"email": "juan@test.com", "nombre": "Juan"}}]
        )

        mock_sender = MagicMock()
        mock_sender.send.return_value = {"success": True, "to_email": "juan@test.com"}
        mock_sender_class.return_value = mock_sender

        result = enviar_email_seguimiento(lead_id="thread-1", template_id="follow_up_caliente")

        assert isinstance(result, dict)
        assert "email_enviado" in result

    def test_enviar_email_seguimiento_without_lead_id(self):
        """Tool must return error if lead_id is not provided."""
        from backend.conversion.tools import enviar_email_seguimiento
        result = enviar_email_seguimiento(lead_id="", template_id="follow_up_caliente")
        assert "error" in result


class TestEnviarEmailSeguimientoRegistration:
    """T-108.6: enviar_email_seguimiento must be registered in GOTOCLOUD_TOOLS."""

    def test_enviar_email_seguimiento_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include enviar_email_seguimiento definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "enviar_email_seguimiento" in tool_names

    def test_enviar_email_seguimiento_has_correct_schema(self):
        """Tool definition must have required parameters."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool = next(t for t in GOTOCLOUD_TOOLS if t["name"] == "enviar_email_seguimiento")
        assert "parameters" in tool
        props = tool["parameters"]["properties"]
        assert "lead_id" in props
        assert "template_id" in props

    @patch("backend.conversion.tools.supabase")
    @patch("backend.conversion.tools.EmailSender")
    def test_ejecutar_tool_routes_enviar_email_seguimiento(self, mock_sender_class, mock_supabase):
        """ejecutar_tool must handle 'enviar_email_seguimiento' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "thread-1", "metadata": {"email": "juan@test.com"}}]
        )
        mock_sender = MagicMock()
        mock_sender.send.return_value = {"success": True}
        mock_sender_class.return_value = mock_sender

        result = ejecutar_tool(
            "enviar_email_seguimiento",
            {"lead_id": "thread-1", "template_id": "follow_up_caliente"},
        )
        assert isinstance(result, dict)
