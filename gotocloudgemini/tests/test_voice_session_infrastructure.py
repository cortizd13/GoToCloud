"""Tests for PR #2 — Voice Session Infrastructure.

Cubre:
- crear_sesion_archivo() helper: creates thread + session in unified tables
- registrar_resumen_llamada: calls crear_sesion_archivo AND inserts into sesiones (legacy)
- Voice sessions have channel_type='voice' and status='completed'
- Backward compatibility: both conversation_sessions and sesiones get rows
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import uuid

# ── Mock Supabase with state tracking ─────────────────────────

class _MockExecResult:
    def __init__(self, data):
        self.data = data


class _MockQuery:
    """Flexible mock that tracks all operations."""

    def __init__(self, table_name, store):
        self.table_name = table_name
        self.store = store  # dict: table_name -> list of rows
        self._method = None
        self._data = None
        self._eq_col = None
        self._eq_val = None
        self._update_data = None

    def select(self, *args, **kwargs):
        self._method = "select"
        return self

    def insert(self, data):
        self._method = "insert"
        self._data = dict(data) if data else {}
        return self

    def update(self, data):
        self._method = "update"
        self._update_data = dict(data) if data else {}
        return self

    def eq(self, col, val):
        self._eq_col = col
        self._eq_val = val
        return self

    def execute(self):
        table_rows = self.store.setdefault(self.table_name, [])

        if self._method == "insert":
            # Auto-generate ID if not present
            if "id" not in self._data:
                self._data["id"] = str(uuid.uuid4())
            table_rows.append(dict(self._data))
            return _MockExecResult([dict(self._data)])

        if self._method == "update":
            # Find and update matching row
            for row in table_rows:
                if row.get(self._eq_col) == self._eq_val:
                    row.update(self._update_data)
                    return _MockExecResult([row])
            return _MockExecResult([])

        if self._method == "select":
            if self._eq_col:
                filtered = [r for r in table_rows if r.get(self._eq_col) == self._eq_val]
                return _MockExecResult(filtered)
            return _MockExecResult(table_rows)

        return _MockExecResult([])


class _MockSupabase:
    """Supabase mock that stores all inserted rows."""

    def __init__(self):
        self.store = {}  # table_name -> list of rows

    def table(self, name):
        return _MockQuery(name, self.store)

    def get_rows(self, table_name):
        return self.store.get(table_name, [])


# ── Setup module path ─────────────────────────────────────────

_module_path = str(Path(__file__).parent.parent)
if _module_path not in sys.path:
    sys.path.insert(0, _module_path)


# ═══════════════════════════════════════════════════════════════
#  Tests for crear_sesion_archivo()
# ═══════════════════════════════════════════════════════════════

class TestCrearSesionArchivo:
    """Unit tests for the crear_sesion_archivo helper."""

    def setup_method(self):
        self.mock_supabase = _MockSupabase()

    def _import_with_mock(self):
        """Import gotocloud_voicebot_tool with mocked supabase."""
        with patch.dict("sys.modules", {
            "backend.supabase_client": MagicMock(
                supabase=self.mock_supabase,
                is_connected=lambda: True,
            )
        }):
            # Force reimport to get fresh module with mocked supabase
            if "service.gotocloud_voicebot_tool" in sys.modules:
                del sys.modules["service.gotocloud_voicebot_tool"]
            from service.gotocloud_voicebot_tool import crear_sesion_archivo, _cliente_actual
            return crear_sesion_archivo, _cliente_actual

    def test_creates_thread_and_session(self):
        """crear_sesion_archivo creates both thread and session rows."""
        crear_sesion, _ = self._import_with_mock()

        result = crear_sesion(1, {"resumen": "Test call", "intention": "calida"})

        assert result is not None
        assert "session_id" in result
        assert "thread_id" in result

        # Verify thread was created
        threads = self.mock_supabase.get_rows("conversation_threads")
        assert len(threads) == 1
        assert str(threads[0]["metadata"]["cliente_id"]) == "1"  # Stored as string

        # Verify session was created
        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 1
        assert sessions[0]["channel_type"] == "voice"
        assert sessions[0]["thread_id"] == result["thread_id"]

    def test_session_has_voice_channel_type(self):
        """Session is created with channel_type='voice'."""
        crear_sesion, _ = self._import_with_mock()

        result = crear_sesion(42, {})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["channel_type"] == "voice"

    def test_session_metadata_contains_call_data(self):
        """Session metadata stores resumen, intention, score_lead, etc."""
        crear_sesion, _ = self._import_with_mock()

        result = crear_sesion(1, {
            "resumen": "Interested in cloud",
            "intention": "caliente",
            "score_lead": 85,
            "servicios_interes": ["cloud_computing", "seguridad"],
            "recomendaciones": "Follow up ASAP",
        })

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        metadata = sessions[0]["metadata"]
        assert metadata["resumen"] == "Interested in cloud"
        assert metadata["intention"] == "caliente"
        assert metadata["score_lead"] == 85
        assert "cloud_computing" in metadata["servicios_interes"]
        assert metadata["recomendaciones"] == "Follow up ASAP"

    def test_returns_none_without_supabase(self):
        """Returns None when supabase is not available."""
        with patch.dict("sys.modules", {
            "backend.supabase_client": MagicMock(
                supabase=None,
                is_connected=lambda: False,
            )
        }):
            if "service.gotocloud_voicebot_tool" in sys.modules:
                del sys.modules["service.gotocloud_voicebot_tool"]
            from service.gotocloud_voicebot_tool import crear_sesion_archivo

            result = crear_sesion_archivo(1, {})
            assert result is None

    def test_thread_has_active_status(self):
        """Thread is created with status='active'."""
        crear_sesion, _ = self._import_with_mock()

        crear_sesion(1, {})

        threads = self.mock_supabase.get_rows("conversation_threads")
        assert threads[0]["status"] == "active"

    def test_session_has_active_status_initially(self):
        """Session starts with status='active' (closed by caller later)."""
        crear_sesion, _ = self._import_with_mock()

        crear_sesion(1, {})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["status"] == "active"

    def test_started_at_uses_provided_value(self):
        """Session uses started_at from session_data if provided."""
        crear_sesion, _ = self._import_with_mock()

        crear_sesion(1, {"started_at": "2026-05-17T10:00:00+00:00"})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["started_at"] == "2026-05-17T10:00:00+00:00"


# ═══════════════════════════════════════════════════════════════
#  Tests for registrar_resumen_llamada with new helper
# ═══════════════════════════════════════════════════════════════

class _FakeQueryPR2:
    """Supabase query mock that tracks operations."""

    def __init__(self, table_name, store):
        self.table_name = table_name
        self.store = store
        self._method = None
        self._data = None
        self._eq_col = None
        self._eq_val = None
        self._update_data = None

    def select(self, *args, **kwargs):
        self._method = "select"
        return self

    def insert(self, data):
        self._method = "insert"
        self._data = dict(data) if data else {}
        return self

    def update(self, data):
        self._method = "update"
        self._update_data = dict(data) if data else {}
        return self

    def eq(self, col, val):
        self._eq_col = col
        self._eq_val = val
        return self

    def execute(self):
        table_rows = self.store.setdefault(self.table_name, [])

        if self._method == "insert":
            if "id" not in self._data:
                self._data["id"] = len(table_rows) + 1
            row = dict(self._data)
            table_rows.append(row)
            return _MockExecResult([row])

        if self._method == "update":
            for row in table_rows:
                if row.get(self._eq_col) == self._eq_val:
                    row.update(self._update_data)
                    return _MockExecResult([row])
            return _MockExecResult([])

        if self._method == "select":
            if self._eq_col:
                filtered = [r for r in table_rows if r.get(self._eq_col) == self._eq_val]
                return _MockExecResult(filtered)
            return _MockExecResult(table_rows)

        return _MockExecResult([])


class _FakeSupabasePR2:
    """Supabase mock for PR2 integration tests."""

    def __init__(self):
        self.store = {}

    def table(self, name):
        return _FakeQueryPR2(name, self.store)

    def get_rows(self, table_name):
        return self.store.get(table_name, [])


class TestRegistrarResumenLlamadaPR2:
    """Tests that registrar_resumen_llamada calls crear_sesion_archivo."""

    def setup_method(self):
        self.mock_supabase = _FakeSupabasePR2()

    def _import_with_mock(self):
        with patch.dict("sys.modules", {
            "backend.supabase_client": MagicMock(
                supabase=self.mock_supabase,
                is_connected=lambda: True,
            )
        }):
            if "service.gotocloud_voicebot_tool" in sys.modules:
                del sys.modules["service.gotocloud_voicebot_tool"]
            from service.gotocloud_voicebot_tool import (
                ejecutar_tool,
                _cliente_actual,
            )
            return ejecutar_tool, _cliente_actual

    def test_creates_unified_session(self):
        """registrar_resumen_llamada creates row in conversation_sessions."""
        ejecutar, _cliente = self._import_with_mock()

        # First register a client
        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        # Then register summary
        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Interested in cloud services",
            "intention": "calida",
            "score_lead": 70,
            "servicios_interes": ["cloud_computing"],
        })

        assert resp["registrado"] is True
        assert "session_id" in resp

        # Verify conversation_sessions has a row
        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 1
        assert sessions[0]["channel_type"] == "voice"

    def test_session_is_completed(self):
        """Session status is set to 'completed' after registrar_resumen_llamada."""
        ejecutar, _cliente = self._import_with_mock()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["status"] == "completed"
        assert "ended_at" in sessions[0]

    def test_legacy_sesiones_also_inserted(self):
        """Legacy sesiones table also gets a row for backward compatibility."""
        ejecutar, _cliente = self._import_with_mock()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        # Both tables should have rows
        sesiones = self.mock_supabase.get_rows("sesiones")
        assert len(sesiones) == 1
        assert sesiones[0]["cliente_id"] == 1
        assert sesiones[0]["resumen"] == "Test"

        assert "llamada_id" in resp  # Legacy ID

    def test_response_contains_both_ids(self):
        """Response includes both session_id (unified) and llamada_id (legacy)."""
        ejecutar, _cliente = self._import_with_mock()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        assert "session_id" in resp
        assert "llamada_id" in resp

    def test_validation_still_works_invalid_score(self):
        """Invalid score_lead still returns error."""
        ejecutar, _cliente = self._import_with_mock()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 150,
        })

        assert "error" in resp
        assert "score_lead" in resp["error"].lower()

    def test_validation_still_works_invalid_intention(self):
        """Invalid intention still returns error."""
        ejecutar, _cliente = self._import_with_mock()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test User",
            "cedula": "1234567890",
        })

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "invalid",
            "score_lead": 50,
        })

        assert "error" in resp
        assert "intention" in resp["error"].lower()

    def test_error_without_client(self):
        """Returns error if no client registered."""
        ejecutar, _cliente = self._import_with_mock()
        _cliente.clear()

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        assert "error" in resp
        assert "cliente" in resp["error"].lower()
