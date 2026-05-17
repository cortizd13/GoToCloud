"""Tests for PR Slice #1: Conversion Rate Improvement — Package Structure (T-102).

These tests validate that the backend/conversion/ package exists with
correct module structure, exports, and stub implementations.
"""

import importlib
import sys
from pathlib import Path

import pytest

BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend"
CONVERSION_PATH = BACKEND_PATH / "conversion"


@pytest.fixture(autouse=True)
def add_backend_to_path():
    """Ensure backend/ is importable."""
    backend_dir = str(BACKEND_PATH.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    yield


# ── Package Structure ─────────────────────────────────────────────────────────


class TestPackageStructure:
    """SC-102.1: backend/conversion/ package must exist with correct files."""

    def test_conversion_directory_exists(self):
        """The conversion/ directory must exist under backend/."""
        assert CONVERSION_PATH.is_dir(), (
            f"backend/conversion/ directory not found at {CONVERSION_PATH}"
        )

    def test_init_file_exists(self):
        """__init__.py must exist."""
        init_path = CONVERSION_PATH / "__init__.py"
        assert init_path.is_file(), f"__init__.py not found at {init_path}"

    def test_tools_file_exists(self):
        """tools.py must exist."""
        tools_path = CONVERSION_PATH / "tools.py"
        assert tools_path.is_file(), f"tools.py not found at {tools_path}"

    def test_scheduling_file_exists(self):
        """scheduling.py must exist."""
        scheduling_path = CONVERSION_PATH / "scheduling.py"
        assert scheduling_path.is_file(), f"scheduling.py not found at {scheduling_path}"

    def test_alerts_file_exists(self):
        """alerts.py must exist."""
        alerts_path = CONVERSION_PATH / "alerts.py"
        assert alerts_path.is_file(), f"alerts.py not found at {alerts_path}"

    def test_crm_file_exists(self):
        """crm.py must exist."""
        crm_path = CONVERSION_PATH / "crm.py"
        assert crm_path.is_file(), f"crm.py not found at {crm_path}"

    def test_email_file_exists(self):
        """email.py must exist."""
        email_path = CONVERSION_PATH / "email.py"
        assert email_path.is_file(), f"email.py not found at {email_path}"

    def test_email_templates_file_exists(self):
        """email_templates.py must exist."""
        templates_path = CONVERSION_PATH / "email_templates.py"
        assert templates_path.is_file(), f"email_templates.py not found at {templates_path}"


# ── Package Exports ───────────────────────────────────────────────────────────


class TestPackageExports:
    """SC-102.2: __init__.py must export register_conversion_tools()."""

    def test_register_conversion_tools_exported(self):
        """register_conversion_tools must be importable from the package."""
        from backend.conversion import register_conversion_tools
        assert callable(register_conversion_tools)


# ── Tools Module ──────────────────────────────────────────────────────────────


class TestToolsModule:
    """SC-102.3: tools.py must have stub implementations for all 6 tools."""

    def test_agendar_cita_exists(self):
        """agendar_cita tool stub must exist."""
        from backend.conversion.tools import agendar_cita
        assert callable(agendar_cita)

    def test_calificar_necesidad_exists(self):
        """calificar_necesidad tool stub must exist."""
        from backend.conversion.tools import calificar_necesidad
        assert callable(calificar_necesidad)

    def test_enviar_email_seguimiento_exists(self):
        """enviar_email_seguimiento tool stub must exist."""
        from backend.conversion.tools import enviar_email_seguimiento
        assert callable(enviar_email_seguimiento)

    def test_notificar_lead_caliente_exists(self):
        """notificar_lead_caliente tool stub must exist."""
        from backend.conversion.tools import notificar_lead_caliente
        assert callable(notificar_lead_caliente)

    def test_consultar_crm_exists(self):
        """consultar_crm tool stub must exist."""
        from backend.conversion.tools import consultar_crm
        assert callable(consultar_crm)

    def test_crear_lead_crm_exists(self):
        """crear_lead_crm tool stub must exist."""
        from backend.conversion.tools import crear_lead_crm
        assert callable(crear_lead_crm)

    def test_tools_have_todo_markers(self):
        """Tool stubs should contain TODO markers indicating placeholder status."""
        import backend.conversion.tools as tools_module
        source = Path(tools_module.__file__).read_text(encoding="utf-8")
        assert "TODO" in source, "tools.py should have TODO markers for stub implementations"


# ── Scheduling Module ────────────────────────────────────────────────────────


class TestSchedulingModule:
    """SC-102.4: scheduling.py must have Calendly stub."""

    def test_calendly_stub_exists(self):
        """CalendlyIntegration class or function must exist."""
        from backend.conversion.scheduling import CalendlyIntegration
        assert CalendlyIntegration is not None

    def test_calendly_has_create_event_stub(self):
        """CalendlyIntegration must have create_event method stub."""
        from backend.conversion.scheduling import CalendlyIntegration
        instance = CalendlyIntegration()
        assert hasattr(instance, "create_event")
        assert callable(instance.create_event)

    def test_scheduling_has_todo_marker(self):
        """scheduling.py should have TODO markers."""
        import backend.conversion.scheduling as sched_module
        source = Path(sched_module.__file__).read_text(encoding="utf-8")
        assert "TODO" in source


# ── Alerts Module ────────────────────────────────────────────────────────────


class TestAlertsModule:
    """SC-102.5: alerts.py must have lead alert dispatcher stub."""

    def test_lead_alert_dispatcher_exists(self):
        """LeadAlertDispatcher class must exist."""
        from backend.conversion.alerts import LeadAlertDispatcher
        assert LeadAlertDispatcher is not None

    def test_dispatcher_has_send_method(self):
        """LeadAlertDispatcher must have send_alert method."""
        from backend.conversion.alerts import LeadAlertDispatcher
        instance = LeadAlertDispatcher()
        assert hasattr(instance, "send_alert")
        assert callable(instance.send_alert)

    def test_alerts_has_todo_marker(self):
        """alerts.py should have TODO markers."""
        import backend.conversion.alerts as alerts_module
        source = Path(alerts_module.__file__).read_text(encoding="utf-8")
        assert "TODO" in source


# ── CRM Module ───────────────────────────────────────────────────────────────


class TestCRMModule:
    """SC-102.6: crm.py must have CRMProvider interface + HubSpotCRM stub."""

    def test_crm_provider_interface_exists(self):
        """CRMProvider class must exist."""
        from backend.conversion.crm import CRMProvider
        assert CRMProvider is not None

    def test_hubspot_crm_exists(self):
        """HubSpotCRM class must exist."""
        from backend.conversion.crm import HubSpotCRM
        assert HubSpotCRM is not None

    def test_hubspot_inherits_provider(self):
        """HubSpotCRM must inherit from CRMProvider."""
        from backend.conversion.crm import CRMProvider, HubSpotCRM
        assert issubclass(HubSpotCRM, CRMProvider)

    def test_crm_provider_has_required_methods(self):
        """CRMProvider must define get_lead, create_lead, update_lead as abstract methods."""
        from backend.conversion.crm import CRMProvider
        # CRMProvider is abstract — check methods exist on the class
        assert hasattr(CRMProvider, "get_lead")
        assert hasattr(CRMProvider, "create_lead")
        assert hasattr(CRMProvider, "update_lead")
        # Verify they are abstract
        assert "get_lead" in CRMProvider.__abstractmethods__
        assert "create_lead" in CRMProvider.__abstractmethods__
        assert "update_lead" in CRMProvider.__abstractmethods__

    def test_crm_has_todo_marker(self):
        """crm.py should have TODO markers."""
        import backend.conversion.crm as crm_module
        source = Path(crm_module.__file__).read_text(encoding="utf-8")
        assert "TODO" in source


# ── Email Module ─────────────────────────────────────────────────────────────


class TestEmailModule:
    """SC-102.7: email.py must have SendGrid stub."""

    def test_email_sender_exists(self):
        """EmailSender class must exist."""
        from backend.conversion.email import EmailSender
        assert EmailSender is not None

    def test_email_sender_has_send_method(self):
        """EmailSender must have send method."""
        from backend.conversion.email import EmailSender
        instance = EmailSender()
        assert hasattr(instance, "send")
        assert callable(instance.send)

    def test_email_has_todo_marker(self):
        """email.py should have TODO markers."""
        import backend.conversion.email as email_module
        source = Path(email_module.__file__).read_text(encoding="utf-8")
        assert "TODO" in source


# ── Email Templates Module ───────────────────────────────────────────────────


class TestEmailTemplatesModule:
    """SC-102.8: email_templates.py must have template placeholders."""

    def test_templates_module_exists(self):
        """email_templates module must be importable."""
        from backend.conversion import email_templates
        assert email_templates is not None

    def test_follow_up_template_exists(self):
        """A follow-up email template must be defined."""
        from backend.conversion.email_templates import FOLLOW_UP_TEMPLATE
        assert FOLLOW_UP_TEMPLATE is not None
        assert isinstance(FOLLOW_UP_TEMPLATE, str)

    def test_template_has_placeholders(self):
        """Template must contain placeholder variables."""
        from backend.conversion.email_templates import FOLLOW_UP_TEMPLATE
        # Check for at least one placeholder pattern
        has_placeholder = (
            "{{" in FOLLOW_UP_TEMPLATE
            or "{cliente_nombre}" in FOLLOW_UP_TEMPLATE
            or "{nombre_cliente}" in FOLLOW_UP_TEMPLATE
        )
        assert has_placeholder, "Template must contain placeholder variables"
