"""Tests for PR Slice #2: Conversion Rate Improvement — Tool Implementations (T-103, T-104, T-105).

These tests validate the conversion tool implementations:
- T-103: agendar_cita tool + CalendlyIntegration
- T-104: calificar_necesidad tool + registrar_datos_cliente extension
- T-105: notificar_lead_caliente tool + LeadAlertDispatcher
"""

import importlib
import sys
import time
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


# ── T-103: CalendlyIntegration ───────────────────────────────────────────────


class TestCalendlyIntegrationCreateEvent:
    """T-103.1: CalendlyIntegration.create_event must generate scheduling links."""

    def test_create_event_returns_dict(self):
        """create_event must return a dict."""
        from backend.conversion.scheduling import CalendlyIntegration
        ci = CalendlyIntegration()
        result = ci.create_event(lead_id="test-lead-1")
        assert isinstance(result, dict)

    def test_create_event_has_required_fields(self):
        """Response must have cita_creada, calendly_link, estado."""
        from backend.conversion.scheduling import CalendlyIntegration
        ci = CalendlyIntegration()
        result = ci.create_event(lead_id="test-lead-1")
        assert "cita_creada" in result
        assert "calendly_link" in result
        assert "estado" in result

    def test_create_event_without_api_key_returns_fallback(self):
        """Without CALENDLY_API_KEY, returns generic link with cita_creada=False."""
        from backend.conversion.scheduling import CalendlyIntegration
        ci = CalendlyIntegration(api_key=None)
        result = ci.create_event(lead_id="test-lead-2")
        assert result["cita_creada"] is False
        assert "calendly.com" in result["calendly_link"]
        assert result["estado"] == "pendiente"

    def test_create_event_includes_lead_id(self):
        """Response must include the lead_id passed in."""
        from backend.conversion.scheduling import CalendlyIntegration
        ci = CalendlyIntegration()
        result = ci.create_event(lead_id="unique-lead-xyz")
        assert result["lead_id"] == "unique-lead-xyz"

    def test_create_event_with_service_and_preferences(self):
        """create_event should accept service and preferences params."""
        from backend.conversion.scheduling import CalendlyIntegration
        ci = CalendlyIntegration()
        result = ci.create_event(
            lead_id="test-lead-3",
            service="cloud_computing",
            preferences={"dia_preferido": "lunes", "hora_preferida": "10:00"},
        )
        assert isinstance(result, dict)
        assert result["lead_id"] == "test-lead-3"


class TestCalendlyIntegrationSavesToSupabase:
    """T-103.2: create_event must save to agent_citas table when Supabase available."""

    @patch("backend.conversion.scheduling.supabase")
    def test_create_event_saves_to_agent_citas(self, mock_supabase):
        """When Supabase is available, insert into agent_citas."""
        from backend.conversion.scheduling import CalendlyIntegration

        mock_result = MagicMock()
        mock_result.data = [{"id": "cita-uuid-1"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        ci = CalendlyIntegration()
        ci._supabase = mock_supabase  # Inject mock
        result = ci.create_event(lead_id="lead-123", service="seguridad")

        # Verify Supabase insert was called
        mock_supabase.table.assert_called_with("agent_citas")
        assert result["cita_creada"] is True

    @patch("backend.conversion.scheduling.supabase")
    def test_create_event_handles_supabase_error(self, mock_supabase):
        """Supabase error should not crash — graceful degrade."""
        from backend.conversion.scheduling import CalendlyIntegration

        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        ci = CalendlyIntegration()
        ci._supabase = mock_supabase
        result = ci.create_event(lead_id="lead-456")

        # Should not raise, but cita_creada should be False
        assert isinstance(result, dict)
        assert result["cita_creada"] is False


# ── T-103: agendar_cita tool ─────────────────────────────────────────────────


class TestAgendarCitaTool:
    """T-103.3: agendar_cita tool in tools.py must delegate to CalendlyIntegration."""

    def test_agendar_cita_returns_dict(self):
        """agendar_cita must return a dict."""
        from backend.conversion.tools import agendar_cita
        result = agendar_cita(lead_id="test-lead")
        assert isinstance(result, dict)

    def test_agendar_cita_has_response_fields(self):
        """Response must have cita_creada, calendly_link, estado."""
        from backend.conversion.tools import agendar_cita
        result = agendar_cita(lead_id="test-lead")
        assert "cita_creada" in result
        assert "calendly_link" in result
        assert "estado" in result

    def test_agendar_cita_passes_service_and_preferences(self):
        """Tool must forward servicio_interes and preferencias."""
        from backend.conversion.tools import agendar_cita
        result = agendar_cita(
            lead_id="test-lead",
            servicio_interes="datos",
            preferencias={"dia_preferido": "martes"},
        )
        assert isinstance(result, dict)


# ── T-103: Tool registration in gotocloud_voicebot_tool.py ────────────────────


class TestAgendarCitaRegistration:
    """T-103.4: agendar_cita must be registered in GOTOCLOUD_TOOLS and ejecutar_tool."""

    def test_agendar_cita_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include agendar_cita definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "agendar_cita" in tool_names

    def test_agendar_cita_tool_has_correct_schema(self):
        """agendar_cita tool definition must have required parameters."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool = next(t for t in GOTOCLOUD_TOOLS if t["name"] == "agendar_cita")
        assert "parameters" in tool
        props = tool["parameters"]["properties"]
        assert "lead_id" in props

    def test_ejecutar_tool_routes_agendar_cita(self):
        """ejecutar_tool must handle 'agendar_cita' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool
        result = ejecutar_tool("agendar_cita", {"lead_id": "test-lead"})
        assert isinstance(result, dict)
        assert "cita_creada" in result or "error" not in result or "calendly_link" in result


# ── T-104: calificar_necesidad tool ──────────────────────────────────────────


class TestCalificarNecesidadTool:
    """T-104.1: calificar_necesidad tool must capture budget/timeline/urgency."""

    def test_calificar_necesidad_returns_dict(self):
        """calificar_necesidad must return a dict."""
        from backend.conversion.tools import calificar_necesidad
        result = calificar_necesidad(lead_id="test-lead")
        assert isinstance(result, dict)

    def test_calificar_necesidad_has_required_fields(self):
        """Response must have calificado, lead_id, and captured fields."""
        from backend.conversion.tools import calificar_necesidad
        result = calificar_necesidad(
            lead_id="test-lead",
            presupuesto_estimado="$5M-10M",
            timeline="1-3 meses",
            urgencia="alta",
        )
        assert "calificado" in result
        assert result["lead_id"] == "test-lead"

    def test_calificar_necesidad_captures_presupuesto(self):
        """Must store presupuesto_estimado in response."""
        from backend.conversion.tools import calificar_necesidad
        result = calificar_necesidad(lead_id="test", presupuesto_estimado="$10M-20M")
        assert result.get("presupuesto_estimado") == "$10M-20M"

    def test_calificar_necesidad_captures_timeline(self):
        """Must store timeline in response."""
        from backend.conversion.tools import calificar_necesidad
        result = calificar_necesidad(lead_id="test", timeline="inmediato")
        assert result.get("timeline") == "inmediato"


class TestCalificarNecesidadSupabase:
    """T-104.2: calificar_necesidad must persist to conversation_threads."""

    @patch("backend.conversion.tools.supabase")
    def test_calificar_necesidad_saves_to_conversation_threads(self, mock_supabase):
        """When Supabase available, update conversation_threads with qualification data."""
        from backend.conversion.tools import calificar_necesidad

        mock_result = MagicMock()
        mock_result.data = [{"id": "thread-1"}]
        mock_supabase.table.return_value.update.return_value.execute.return_value = mock_result

        result = calificar_necesidad(
            lead_id="thread-1",
            presupuesto_estimado="$5M-10M",
            timeline="1-3 meses",
            urgencia="alta",
        )

        mock_supabase.table.assert_called_with("conversation_threads")
        assert result["calificado"] is True

    @patch("backend.conversion.tools.supabase")
    def test_calificar_necesidad_handles_supabase_error(self, mock_supabase):
        """Supabase error should not crash."""
        from backend.conversion.tools import calificar_necesidad

        mock_supabase.table.return_value.update.return_value.execute.side_effect = Exception("DB error")

        result = calificar_necesidad(lead_id="thread-1", presupuesto_estimado="$5M")
        assert isinstance(result, dict)


# ── T-104: registrar_datos_cliente extension ─────────────────────────────────


class TestRegistrarDatosClienteExtension:
    """T-104.3: registrar_datos_cliente must accept presupuesto/timeline fields."""

    def test_registrar_datos_cliente_accepts_presupuesto(self):
        """Tool must accept presupuesto_estimado param without error."""
        from service.gotocloud_voicebot_tool import ejecutar_tool
        result = ejecutar_tool(
            "registrar_datos_cliente",
            {
                "nombre": "Test User",
                "cedula": "99999999",
                "presupuesto_estimado": "$5M-10M",
            },
        )
        assert isinstance(result, dict)
        assert result["registrado"] is True

    def test_registrar_datos_cliente_accepts_timeline(self):
        """Tool must accept timeline param without error."""
        from service.gotocloud_voicebot_tool import ejecutar_tool
        result = ejecutar_tool(
            "registrar_datos_cliente",
            {
                "nombre": "Test User 2",
                "cedula": "99999998",
                "timeline": "1-3 meses",
            },
        )
        assert isinstance(result, dict)
        assert result["registrado"] is True


# ── T-104: calificar_necesidad registration ──────────────────────────────────


class TestCalificarNecesidadRegistration:
    """T-104.4: calificar_necesidad must be registered and routable."""

    def test_calificar_necesidad_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include calificar_necesidad definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "calificar_necesidad" in tool_names

    def test_ejecutar_tool_routes_calificar_necesidad(self):
        """ejecutar_tool must handle 'calificar_necesidad' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool
        result = ejecutar_tool(
            "calificar_necesidad",
            {
                "lead_id": "test-lead",
                "presupuesto_estimado": "$5M-10M",
                "timeline": "1-3 meses",
            },
        )
        assert isinstance(result, dict)
        assert "calificado" in result


# ── T-105: LeadAlertDispatcher ───────────────────────────────────────────────


class TestLeadAlertDispatcherSendAlert:
    """T-105.1: LeadAlertDispatcher.send_alert must POST to webhook with retry."""

    def test_send_alert_returns_dict(self):
        """send_alert must return a dict."""
        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher()
        result = dispatcher.send_alert(lead_id="test-lead", score=85, payload={})
        assert isinstance(result, dict)

    def test_send_alert_without_webhook_url_skips(self):
        """Without webhook URL, should skip with status='skipped'."""
        import os
        original = os.environ.get("CONVERSION_TOOLS_ENABLED")
        os.environ["CONVERSION_TOOLS_ENABLED"] = "true"

        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher(webhook_url=None)
        result = dispatcher.send_alert(lead_id="test-lead", score=85, payload={})

        if original is not None:
            os.environ["CONVERSION_TOOLS_ENABLED"] = original
        else:
            os.environ.pop("CONVERSION_TOOLS_ENABLED", None)

        assert result["status"] == "skipped"

    def test_send_alert_has_required_fields(self):
        """Response must have lead_id, status, attempts."""
        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher()
        result = dispatcher.send_alert(lead_id="test-lead", score=85, payload={})
        assert "lead_id" in result
        assert "status" in result
        assert "attempts" in result

    @patch("backend.conversion.alerts.requests.post")
    def test_send_alert_posts_to_webhook(self, mock_post):
        """When webhook URL configured, POST to it."""
        import os
        original = os.environ.get("CONVERSION_TOOLS_ENABLED")
        os.environ["CONVERSION_TOOLS_ENABLED"] = "true"

        from backend.conversion.alerts import LeadAlertDispatcher

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = LeadAlertDispatcher(webhook_url="https://example.com/webhook")
        # Inject mock supabase for logging
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])
        dispatcher._supabase = mock_supabase

        result = dispatcher.send_alert(
            lead_id="hot-lead-1",
            score=85,
            payload={"nombre": "Juan", "servicios": ["Kármán"]},
            intention="caliente",
        )

        mock_post.assert_called_once()
        assert result["status"] == "enviada"

        if original is not None:
            os.environ["CONVERSION_TOOLS_ENABLED"] = original
        else:
            os.environ.pop("CONVERSION_TOOLS_ENABLED", None)

    @patch("backend.conversion.alerts.requests.post")
    def test_send_alert_retries_on_failure(self, mock_post):
        """On failure, should retry up to MAX_RETRIES times."""
        import os
        original = os.environ.get("CONVERSION_TOOLS_ENABLED")
        os.environ["CONVERSION_TOOLS_ENABLED"] = "true"

        from backend.conversion.alerts import LeadAlertDispatcher

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        dispatcher = LeadAlertDispatcher(webhook_url="https://example.com/webhook")
        # Inject mock supabase for logging
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])
        dispatcher._supabase = mock_supabase
        dispatcher.MAX_RETRIES = 2  # Speed up test

        result = dispatcher.send_alert(lead_id="fail-lead", score=90, payload={})

        assert mock_post.call_count == 2  # MAX_RETRIES attempts
        assert result["status"] == "fallida"

        if original is not None:
            os.environ["CONVERSION_TOOLS_ENABLED"] = original
        else:
            os.environ.pop("CONVERSION_TOOLS_ENABLED", None)

    def test_send_alert_respects_feature_flag(self):
        """When CONVERSION_TOOLS_ENABLED=False, should log only, no webhook."""
        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher(webhook_url="https://example.com/webhook")
        dispatcher._conversion_enabled = False  # Simulate flag off
        result = dispatcher.send_alert(lead_id="test-lead", score=85, payload={})
        # Should skip webhook even if URL is configured
        assert result["status"] in ("skipped", "logged_only")


class TestLeadAlertDispatcherBuildPayload:
    """T-105.2: _build_payload must construct standard alert payload."""

    def test_build_payload_structure(self):
        """Payload must have event, timestamp, lead, session, calificacion."""
        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher()
        payload = dispatcher._build_payload(
            lead_id="lead-1",
            score=85,
            lead_data={"nombre": "Juan", "telefono": "+573001234567"},
            session_data={"id": "session-1", "channel": "voice"},
            qualification={"presupuesto": "$5M-10M", "timeline": "1-3 meses"},
        )
        assert payload["event"] == "lead_caliente"
        assert payload["timestamp"] != ""
        assert payload["lead"]["nombre"] == "Juan"
        assert payload["session"]["channel"] == "voice"
        assert payload["calificacion"]["presupuesto"] == "$5M-10M"


# ── T-105: notificar_lead_caliente tool ──────────────────────────────────────


class TestNotificarLeadCalienteTool:
    """T-105.3: notificar_lead_caliente tool must delegate to LeadAlertDispatcher."""

    def test_notificar_lead_caliente_returns_dict(self):
        """notificar_lead_caliente must return a dict."""
        from backend.conversion.tools import notificar_lead_caliente
        result = notificar_lead_caliente(lead_id="test-lead", score_lead=85)
        assert isinstance(result, dict)

    def test_notificar_lead_caliente_has_required_fields(self):
        """Response must have alerta_enviada, lead_id, score_lead."""
        from backend.conversion.tools import notificar_lead_caliente
        result = notificar_lead_caliente(lead_id="test-lead", score_lead=85)
        assert "alerta_enviada" in result
        assert result["lead_id"] == "test-lead"
        assert result["score_lead"] == 85


# ── T-105: notificar_lead_caliente registration ──────────────────────────────


class TestNotificarLeadCalienteRegistration:
    """T-105.4: notificar_lead_caliente must be registered and routable."""

    def test_notificar_lead_caliente_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include notificar_lead_caliente definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "notificar_lead_caliente" in tool_names

    def test_ejecutar_tool_routes_notificar_lead_caliente(self):
        """ejecutar_tool must handle 'notificar_lead_caliente' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool
        result = ejecutar_tool(
            "notificar_lead_caliente",
            {"lead_id": "test-lead", "score_lead": 85, "canal": "voice", "intencion": "caliente"},
        )
        assert isinstance(result, dict)
        assert "alerta_enviada" in result


# ── T-105: Feature flag CONVERSION_TOOLS_ENABLED ─────────────────────────────


class TestConversionFeatureFlag:
    """T-105.5: CONVERSION_TOOLS_ENABLED flag controls webhook dispatch."""

    def test_flag_default_false(self):
        """When flag not set, tools should degrade gracefully."""
        import os
        # Ensure flag is not set
        original = os.environ.pop("CONVERSION_TOOLS_ENABLED", None)
        from backend.conversion.alerts import LeadAlertDispatcher

        dispatcher = LeadAlertDispatcher(webhook_url="https://example.com/webhook")
        # Without flag, should still work but log only
        result = dispatcher.send_alert(lead_id="test", score=85, payload={})
        assert isinstance(result, dict)

        # Restore original
        if original is not None:
            os.environ["CONVERSION_TOOLS_ENABLED"] = original

    def test_flag_true_enables_webhook(self):
        """When flag is true, webhook dispatch should be enabled."""
        import os
        original = os.environ.get("CONVERSION_TOOLS_ENABLED")
        os.environ["CONVERSION_TOOLS_ENABLED"] = "true"

        # Reload module to pick up env var
        import backend.conversion.alerts as alerts_module
        importlib.reload(alerts_module)

        from backend.conversion.alerts import LeadAlertDispatcher
        dispatcher = LeadAlertDispatcher(webhook_url="https://example.com/webhook")
        # With flag true and no actual endpoint, should attempt webhook
        result = dispatcher.send_alert(lead_id="test", score=85, payload={})
        assert isinstance(result, dict)

        # Restore
        if original is not None:
            os.environ["CONVERSION_TOOLS_ENABLED"] = original
        else:
            os.environ.pop("CONVERSION_TOOLS_ENABLED", None)
