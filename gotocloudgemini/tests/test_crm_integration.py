"""Tests for PR Slice #4: CRM Integration (T-109).

These tests validate:
- T-109.1: HubSpotCRM.get_lead() with REST API
- T-109.2: HubSpotCRM.create_lead() with REST API
- T-109.3: HubSpotCRM.update_lead() with REST API
- T-109.4: CRM sync logging to crm_sync_log table
- T-109.5: Graceful degrade when no API key
- T-109.6: consultar_crm and crear_lead_crm tool wiring
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


# ── T-109.1: HubSpotCRM.get_lead() ───────────────────────────────────────────


class TestHubSpotCRMGetLead:
    """T-109.1: HubSpotCRM.get_lead must search by email or cedula."""

    @patch("backend.conversion.crm.requests.post")
    def test_get_lead_by_email_finds_contact(self, mock_post):
        """Search by email returns contact data when found."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "id": "hs_123456",
                "properties": {
                    "email": "juan@test.com",
                    "firstname": "Juan",
                    "lastname": "Pérez",
                    "phone": "+573001234567",
                },
            }]
        }
        mock_post.return_value = mock_response

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.get_lead("juan@test.com", identifier_type="email")

        mock_post.assert_called_once()
        assert result["success"] is True
        assert result["cliente_encontrado"] is True
        assert result["crm_id"] == "hs_123456"

    @patch("backend.conversion.crm.requests.post")
    def test_get_lead_by_email_not_found(self, mock_post):
        """Search by email returns not found when no results."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.get_lead("unknown@test.com", identifier_type="email")

        assert result["success"] is True
        assert result["cliente_encontrado"] is False

    @patch("backend.conversion.crm.requests.post")
    def test_get_lead_handles_api_error(self, mock_post):
        """API error should not crash — return error status."""
        from backend.conversion.crm import HubSpotCRM

        mock_post.side_effect = Exception("API timeout")

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.get_lead("juan@test.com", identifier_type="email")

        assert result["success"] is False

    def test_get_lead_without_api_key_returns_graceful_degrade(self):
        """Without API key, return graceful degrade response."""
        from backend.conversion.crm import HubSpotCRM
        crm = HubSpotCRM(api_key=None)
        result = crm.get_lead("juan@test.com", identifier_type="email")
        assert result["success"] is False
        assert result["razon"] == "crm_no_configurado"


# ── T-109.2: HubSpotCRM.create_lead() ────────────────────────────────────────


class TestHubSpotCRMCreateLead:
    """T-109.2: HubSpotCRM.create_lead must create contact in HubSpot."""

    @patch("backend.conversion.crm.requests.post")
    def test_create_lead_success(self, mock_post):
        """Create lead returns CRM ID on success."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "hs_new_789"}
        mock_post.return_value = mock_response

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.create_lead({
            "nombre": "María López",
            "email": "maria@test.com",
            "telefono": "+573009876543",
            "empresa": "TestCorp",
        })

        mock_post.assert_called_once()
        assert result["success"] is True
        assert result["crm_id"] == "hs_new_789"

    @patch("backend.conversion.crm.requests.post")
    def test_create_lead_handles_api_error(self, mock_post):
        """API error should not crash."""
        from backend.conversion.crm import HubSpotCRM

        mock_post.side_effect = Exception("API error")

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.create_lead({"nombre": "Test", "email": "test@test.com"})

        assert result["success"] is False

    def test_create_lead_without_api_key_returns_graceful_degrade(self):
        """Without API key, return graceful degrade response."""
        from backend.conversion.crm import HubSpotCRM
        crm = HubSpotCRM(api_key=None)
        result = crm.create_lead({"nombre": "Test", "email": "test@test.com"})
        assert result["success"] is False
        assert result["razon"] == "crm_no_configurado"


# ── T-109.3: HubSpotCRM.update_lead() ────────────────────────────────────────


class TestHubSpotCRMUpdateLead:
    """T-109.3: HubSpotCRM.update_lead must update contact in HubSpot."""

    @patch("backend.conversion.crm.requests.patch")
    def test_update_lead_success(self, mock_patch):
        """Update lead returns success on 200."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.update_lead("hs_123456", {"phone": "+573001112233"})

        mock_patch.assert_called_once()
        assert result["success"] is True

    @patch("backend.conversion.crm.requests.patch")
    def test_update_lead_handles_api_error(self, mock_patch):
        """API error should not crash."""
        from backend.conversion.crm import HubSpotCRM

        mock_patch.side_effect = Exception("API error")

        crm = HubSpotCRM(api_key="test-hubspot-key")
        result = crm.update_lead("hs_123456", {"phone": "+573001112233"})

        assert result["success"] is False


# ── T-109.4: CRM sync logging ────────────────────────────────────────────────


class TestHubSpotCRMLogsToSupabase:
    """T-109.4: CRM operations must log to crm_sync_log table."""

    @patch("backend.conversion.crm.supabase")
    @patch("backend.conversion.crm.requests.post")
    def test_get_lead_logs_lookup_to_crm_sync_log(self, mock_post, mock_supabase):
        """get_lead must log lookup operation to crm_sync_log."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])

        crm = HubSpotCRM(api_key="test-key")
        crm._supabase = mock_supabase
        result = crm.get_lead("test@test.com", identifier_type="email")

        mock_supabase.table.assert_called_with("crm_sync_log")
        assert result["success"] is True

    @patch("backend.conversion.crm.supabase")
    @patch("backend.conversion.crm.requests.post")
    def test_create_lead_logs_create_to_crm_sync_log(self, mock_post, mock_supabase):
        """create_lead must log create operation to crm_sync_log."""
        from backend.conversion.crm import HubSpotCRM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "hs_new"}
        mock_post.return_value = mock_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-2"}])

        crm = HubSpotCRM(api_key="test-key")
        crm._supabase = mock_supabase
        result = crm.create_lead({"nombre": "Test", "email": "test@test.com"})

        mock_supabase.table.assert_called_with("crm_sync_log")
        assert result["success"] is True


# ── T-109.6: Tool wiring ─────────────────────────────────────────────────────


class TestConsultarCrmTool:
    """T-109.6.1: consultar_crm tool must delegate to HubSpotCRM."""

    @patch("backend.conversion.tools.get_crm_provider")
    def test_consultar_crm_returns_dict(self, mock_provider):
        """Tool must return a dict."""
        from backend.conversion.tools import consultar_crm
        result = consultar_crm(lead_id="test-lead")
        assert isinstance(result, dict)

    @patch("backend.conversion.tools.get_crm_provider")
    def test_consultar_crm_calls_provider_get_lead(self, mock_provider):
        """Tool must call CRM provider's get_lead method."""
        from backend.conversion.tools import consultar_crm

        mock_crm = MagicMock()
        mock_crm.get_lead.return_value = {"success": True, "cliente_encontrado": False}
        mock_provider.return_value = mock_crm

        result = consultar_crm(identificador="test@test.com", tipo="email", crm_tipo="hubspot")

        mock_crm.get_lead.assert_called_once_with("test@test.com", identifier_type="email")
        assert isinstance(result, dict)

    def test_consultar_crm_without_lead_id(self):
        """Tool must return error if lead_id is not provided."""
        from backend.conversion.tools import consultar_crm
        result = consultar_crm(lead_id="")
        assert "error" in result


class TestCrearLeadCrmTool:
    """T-109.6.2: crear_lead_crm tool must delegate to HubSpotCRM."""

    @patch("backend.conversion.tools.get_crm_provider")
    def test_crear_lead_crm_returns_dict(self, mock_provider):
        """Tool must return a dict."""
        from backend.conversion.tools import crear_lead_crm
        result = crear_lead_crm(lead_id="test-lead")
        assert isinstance(result, dict)

    @patch("backend.conversion.tools.get_crm_provider")
    def test_crear_lead_crm_calls_provider_create_lead(self, mock_provider):
        """Tool must call CRM provider's create_lead method."""
        from backend.conversion.tools import crear_lead_crm

        mock_crm = MagicMock()
        mock_crm.create_lead.return_value = {"success": True, "crm_id": "hs_new"}
        mock_provider.return_value = mock_crm

        result = crear_lead_crm(lead_id="thread-1", crm_tipo="hubspot")

        mock_crm.create_lead.assert_called_once()
        assert result["success"] is True

    def test_crear_lead_crm_without_lead_id(self):
        """Tool must return error if lead_id is not provided."""
        from backend.conversion.tools import crear_lead_crm
        result = crear_lead_crm(lead_id="")
        assert "error" in result


class TestCRMToolRegistration:
    """T-109.7: CRM tools must be registered in GOTOCLOUD_TOOLS."""

    def test_consultar_crm_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include consultar_crm definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "consultar_crm" in tool_names

    def test_crear_lead_crm_in_tools_list(self):
        """GOTOCLOUD_TOOLS must include crear_lead_crm definition."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool_names = [t["name"] for t in GOTOCLOUD_TOOLS]
        assert "crear_lead_crm" in tool_names

    def test_consultar_crm_has_correct_schema(self):
        """Tool definition must have required parameters."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool = next(t for t in GOTOCLOUD_TOOLS if t["name"] == "consultar_crm")
        assert "parameters" in tool
        props = tool["parameters"]["properties"]
        assert "identificador" in props
        assert "tipo" in props

    def test_crear_lead_crm_has_correct_schema(self):
        """Tool definition must have required parameters."""
        from service.gotocloud_voicebot_tool import GOTOCLOUD_TOOLS
        tool = next(t for t in GOTOCLOUD_TOOLS if t["name"] == "crear_lead_crm")
        assert "parameters" in tool
        props = tool["parameters"]["properties"]
        assert "nombre" in props
        assert "email" in props

    @patch("backend.conversion.tools.get_crm_provider")
    def test_ejecutar_tool_routes_consultar_crm(self, mock_provider):
        """ejecutar_tool must handle 'consultar_crm' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool

        mock_crm = MagicMock()
        mock_crm.get_lead.return_value = {"success": True, "cliente_encontrado": False}
        mock_provider.return_value = mock_crm

        result = ejecutar_tool("consultar_crm", {"identificador": "juan@test.com", "tipo": "email"})
        assert isinstance(result, dict)

    @patch("backend.conversion.tools.get_crm_provider")
    def test_ejecutar_tool_routes_crear_lead_crm(self, mock_provider):
        """ejecutar_tool must handle 'crear_lead_crm' name."""
        from service.gotocloud_voicebot_tool import ejecutar_tool

        mock_crm = MagicMock()
        mock_crm.create_lead.return_value = {"success": True, "crm_id": "hs_new"}
        mock_provider.return_value = mock_crm

        result = ejecutar_tool(
            "crear_lead_crm",
            {"nombre": "Juan", "email": "juan@test.com", "telefono": "+573001234567"},
        )
        assert isinstance(result, dict)
