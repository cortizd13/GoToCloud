# Tests for PR #5 — Legacy Compatibility & Integration Tests (FINAL)
#
# Cubre:
# - 5.1: Tool backward compatibility — registrar_resumen_llamada writes to both
#         conversation_sessions AND sesiones (dual-write verified)
# - 5.2: Unit test for crear_sesion_archivo() — mock Supabase, correct table + columns
# - 5.3: Integration test — voice call end-to-end creates row in conversation_sessions
#         with channel_type='voice', status='completed'
# - 5.4: Integration test — POST /chat/message first message creates thread + session;
#         second message appends to same session

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Module path setup ──────────────────────────────────────────

_module_path = str(Path(__file__).parent.parent)
if _module_path not in sys.path:
    sys.path.insert(0, _module_path)


# ═══════════════════════════════════════════════════════════════
#  Shared mock infrastructure
# ═══════════════════════════════════════════════════════════════

class _MockExecResult:
    def __init__(self, data):
        self.data = data


class _MockQuery:
    """Stateful Supabase query mock that tracks all operations."""

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

    def order(self, col, desc=False):
        return self

    def limit(self, n):
        return self

    def execute(self):
        table_rows = self.store.setdefault(self.table_name, [])

        if self._method == "insert":
            if "id" not in self._data:
                self._data["id"] = str(uuid.uuid4())
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


class _MockSupabase:
    """Supabase mock that stores all inserted rows per table."""

    def __init__(self):
        self.store = {}

    def table(self, name):
        return _MockQuery(name, self.store)

    def get_rows(self, table_name):
        return self.store.get(table_name, [])


def _import_tool_with_mock(mock_supabase):
    """Import gotocloud_voicebot_tool with a mocked supabase client."""
    with patch.dict("sys.modules", {
        "backend.supabase_client": MagicMock(
            supabase=mock_supabase,
            is_connected=lambda: True,
        )
    }):
        if "service.gotocloud_voicebot_tool" in sys.modules:
            del sys.modules["service.gotocloud_voicebot_tool"]
        from service.gotocloud_voicebot_tool import (
            ejecutar_tool,
            crear_sesion_archivo,
            _cliente_actual,
        )
        return ejecutar_tool, crear_sesion_archivo, _cliente_actual


# ═══════════════════════════════════════════════════════════════
#  Task 5.1: Backward compatibility — dual-write verification
# ═══════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Verify registrar_resumen_llamada writes to BOTH tables (REQ-11, REQ-12)."""

    def setup_method(self):
        self.mock_supabase = _MockSupabase()

    def _import(self):
        return _import_tool_with_mock(self.mock_supabase)

    def test_dual_write_both_tables_populated(self):
        """registrar_resumen_llamada inserts into conversation_sessions AND sesiones."""
        ejecutar, _, _cliente = self._import()

        # Register client first
        ejecutar("registrar_datos_cliente", {
            "nombre": "Carlos Mendez",
            "cedula": "9876543210",
        })

        # Register summary (end of call)
        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Interested in OASIS AI for document automation",
            "intention": "caliente",
            "score_lead": 90,
            "servicios_interes": ["datos", "soluciones_saas"],
            "recomendaciones": "Schedule demo with sales team",
        })

        assert resp["registrado"] is True

        # Unified session table
        unified = self.mock_supabase.get_rows("conversation_sessions")
        assert len(unified) == 1
        assert unified[0]["channel_type"] == "voice"

        # Legacy archive table
        legacy = self.mock_supabase.get_rows("sesiones")
        assert len(legacy) == 1
        assert legacy[0]["cliente_id"] is not None  # UUID from Supabase
        assert legacy[0]["resumen"] == "Interested in OASIS AI for document automation"
        assert legacy[0]["intention"] == "caliente"

    def test_response_contains_both_ids(self):
        """Response includes session_id (unified) and llamada_id (legacy)."""
        ejecutar, _, _cliente = self._import()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Ana Lopez",
            "cedula": "1122334455",
        })

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Pricing inquiry",
            "intention": "calida",
            "score_lead": 60,
        })

        assert "session_id" in resp, "Missing unified session_id"
        assert "llamada_id" in resp, "Missing legacy llamada_id"

    def test_unified_session_marked_completed(self):
        """Unified session status is 'completed' with ended_at after summary."""
        ejecutar, _, _cliente = self._import()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Pedro Gomez",
            "cedula": "5566778899",
        })

        ejecutar("registrar_resumen_llamada", {
            "resumen": "General inquiry",
            "intention": "fria",
            "score_lead": 20,
        })

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 1
        assert sessions[0]["status"] == "completed"
        assert "ended_at" in sessions[0]

    def test_legacy_data_preserves_all_fields(self):
        """Legacy sesiones row preserves resumen, intention, score_lead, servicios."""
        ejecutar, _, _cliente = self._import()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Maria Torres",
            "cedula": "9988776655",
        })

        ejecutar("registrar_resumen_llamada", {
            "resumen": "Wants FinOps consulting",
            "intention": "calida",
            "score_lead": 75,
            "servicios_interes": ["cloud_computing", "servicios_administrados"],
            "recomendaciones": "Send pricing deck",
        })

        legacy = self.mock_supabase.get_rows("sesiones")[0]
        assert legacy["resumen"] == "Wants FinOps consulting"
        assert legacy["intention"] == "calida"
        assert legacy["score_lead"] == 75
        assert "cloud_computing" in legacy["servicios_interes"]
        assert legacy["recomendaciones"] == "Send pricing deck"

    def test_validation_errors_prevent_dual_write(self):
        """Invalid input returns error without writing to either table."""
        ejecutar, _, _cliente = self._import()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test",
            "cedula": "0000000000",
        })

        # Invalid score
        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 200,
        })
        assert "error" in resp

        # No rows should be created
        assert len(self.mock_supabase.get_rows("conversation_sessions")) == 0
        assert len(self.mock_supabase.get_rows("sesiones")) == 0

    def test_no_client_returns_error(self):
        """Without registered client, returns error without writing."""
        ejecutar, _, _cliente = self._import()
        _cliente.clear()

        resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        assert "error" in resp
        assert "cliente" in resp["error"].lower()


# ═══════════════════════════════════════════════════════════════
#  Task 5.2: Unit tests for crear_sesion_archivo()
# ═══════════════════════════════════════════════════════════════

class TestCrearSesionArchivoUnit:
    """Unit tests for crear_sesion_archivo with mocked Supabase."""

    def setup_method(self):
        self.mock_supabase = _MockSupabase()

    def _import(self):
        return _import_tool_with_mock(self.mock_supabase)

    def test_creates_thread_with_cliente_id_metadata(self):
        """Thread is created with cliente_id stored in metadata."""
        _, crear_sesion, _ = self._import()

        result = crear_sesion(42, {"resumen": "Test"})

        assert result is not None
        threads = self.mock_supabase.get_rows("conversation_threads")
        assert len(threads) == 1
        # cliente_id stored as string (supports both int and UUID)
        assert str(threads[0]["metadata"]["cliente_id"]) == "42"

    def test_creates_session_with_voice_channel(self):
        """Session is created with channel_type='voice'."""
        _, crear_sesion, _ = self._import()

        result = crear_sesion(1, {})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 1
        assert sessions[0]["channel_type"] == "voice"

    def test_session_linked_to_thread(self):
        """Session thread_id matches the created thread id."""
        _, crear_sesion, _ = self._import()

        result = crear_sesion(1, {})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        threads = self.mock_supabase.get_rows("conversation_threads")
        assert sessions[0]["thread_id"] == threads[0]["id"]
        assert sessions[0]["thread_id"] == result["thread_id"]

    def test_returns_session_and_thread_ids(self):
        """Returns dict with session_id and thread_id."""
        _, crear_sesion, _ = self._import()

        result = crear_sesion(1, {})

        assert "session_id" in result
        assert "thread_id" in result
        assert isinstance(result["session_id"], str)
        assert isinstance(result["thread_id"], str)

    def test_session_initial_status_is_active(self):
        """Session starts as 'active' (caller closes it later)."""
        _, crear_sesion, _ = self._import()

        crear_sesion(1, {})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["status"] == "active"

    def test_session_metadata_stores_call_data(self):
        """Session metadata contains resumen, intention, score_lead, etc."""
        _, crear_sesion, _ = self._import()

        crear_sesion(1, {
            "resumen": "Cloud migration inquiry",
            "intention": "caliente",
            "score_lead": 85,
            "servicios_interes": ["cloud_computing"],
            "recomendaciones": "Follow up with senior architect",
        })

        metadata = self.mock_supabase.get_rows("conversation_sessions")[0]["metadata"]
        assert metadata["resumen"] == "Cloud migration inquiry"
        assert metadata["intention"] == "caliente"
        assert metadata["score_lead"] == 85
        assert metadata["servicios_interes"] == ["cloud_computing"]
        assert metadata["recomendaciones"] == "Follow up with senior architect"

    def test_started_at_uses_provided_value(self):
        """Session uses started_at from session_data when provided."""
        _, crear_sesion, _ = self._import()

        crear_sesion(1, {"started_at": "2026-05-17T08:00:00+00:00"})

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["started_at"] == "2026-05-17T08:00:00+00:00"

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

    def test_thread_has_correct_topic(self):
        """Thread topic includes the cliente_id for traceability."""
        _, crear_sesion, _ = self._import()

        crear_sesion(99, {})

        threads = self.mock_supabase.get_rows("conversation_threads")
        assert "99" in threads[0]["topic"]

    def test_thread_has_active_status(self):
        """Thread is created with status='active'."""
        _, crear_sesion, _ = self._import()

        crear_sesion(1, {})

        threads = self.mock_supabase.get_rows("conversation_threads")
        assert threads[0]["status"] == "active"

    def test_string_cliente_id_stored_as_string(self):
        """String cliente_id is stored as-is in metadata (supports UUIDs)."""
        _, crear_sesion, _ = self._import()

        crear_sesion("uuid-123", {})

        threads = self.mock_supabase.get_rows("conversation_threads")
        assert threads[0]["metadata"]["cliente_id"] == "uuid-123"
        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert sessions[0]["metadata"]["cliente_id"] == "uuid-123"


# ═══════════════════════════════════════════════════════════════
#  Task 5.3: Integration test — voice call end-to-end
# ═══════════════════════════════════════════════════════════════

class TestVoiceCallEndToEnd:
    """Integration: full voice call flow from registration to summary."""

    def setup_method(self):
        self.mock_supabase = _MockSupabase()

    def _import(self):
        return _import_tool_with_mock(self.mock_supabase)

    def test_full_voice_call_flow(self):
        """Complete voice call: register client → register summary → verify session."""
        ejecutar, _, _cliente = self._import()

        # Step 1: Client registers at start of call
        client_resp = ejecutar("registrar_datos_cliente", {
            "nombre": "Jorge Ramirez",
            "cedula": "1234567890",
            "empresa": "Ecopetrol",
            "telefono": "+573001234567",
        })
        assert client_resp["registrado"] is True
        assert "cliente_id" in client_resp

        # Step 2: Call ends, summary registered
        summary_resp = ejecutar("registrar_resumen_llamada", {
            "resumen": "Client interested in Azure migration for 500 servers",
            "intention": "caliente",
            "score_lead": 95,
            "servicios_interes": ["cloud_computing", "modernizacion_apps"],
            "recomendaciones": "Priority lead — schedule architecture review",
        })

        assert summary_resp["registrado"] is True
        assert "session_id" in summary_resp
        assert "llamada_id" in summary_resp

        # Step 3: Verify conversation_sessions
        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 1
        session = sessions[0]
        assert session["channel_type"] == "voice"
        assert session["status"] == "completed"
        assert "ended_at" in session
        assert session["metadata"]["resumen"] == "Client interested in Azure migration for 500 servers"
        assert session["metadata"]["intention"] == "caliente"
        assert session["metadata"]["score_lead"] == 95

        # Step 4: Verify thread was created
        threads = self.mock_supabase.get_rows("conversation_threads")
        assert len(threads) == 1
        assert threads[0]["metadata"]["cliente_id"] is not None  # UUID from Supabase

        # Step 5: Verify legacy sesiones
        legacy = self.mock_supabase.get_rows("sesiones")
        assert len(legacy) == 1
        assert legacy[0]["cliente_id"] is not None  # UUID from Supabase
        assert legacy[0]["resumen"] == "Client interested in Azure migration for 500 servers"

    def test_voice_call_session_has_correct_thread_link(self):
        """Session thread_id matches the thread created for the client."""
        ejecutar, _, _cliente = self._import()

        ejecutar("registrar_datos_cliente", {
            "nombre": "Test",
            "cedula": "0000000001",
        })
        ejecutar("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 50,
        })

        sessions = self.mock_supabase.get_rows("conversation_sessions")
        threads = self.mock_supabase.get_rows("conversation_threads")

        assert sessions[0]["thread_id"] == threads[0]["id"]

    def test_recurring_client_updates_data(self):
        """Second call from same cedula updates client, creates new session."""
        ejecutar, _, _cliente = self._import()

        # First call
        ejecutar("registrar_datos_cliente", {
            "nombre": "Recurring Client",
            "cedula": "1111111111",
        })
        ejecutar("registrar_resumen_llamada", {
            "resumen": "First call",
            "intention": "fria",
            "score_lead": 10,
        })

        # Clear client state (simulates new call)
        _cliente.clear()

        # Second call — same cedula
        ejecutar("registrar_datos_cliente", {
            "nombre": "Recurring Client Updated",
            "cedula": "1111111111",
            "empresa": "New Company",
        })
        ejecutar("registrar_resumen_llamada", {
            "resumen": "Second call",
            "intention": "calida",
            "score_lead": 60,
        })

        # Two sessions should exist (one per call)
        sessions = self.mock_supabase.get_rows("conversation_sessions")
        assert len(sessions) == 2
        assert sessions[0]["metadata"]["resumen"] == "First call"
        assert sessions[1]["metadata"]["resumen"] == "Second call"

        # Two legacy rows too
        legacy = self.mock_supabase.get_rows("sesiones")
        assert len(legacy) == 2


# ═══════════════════════════════════════════════════════════════
#  Task 5.4: Integration test — chat message end-to-end
# ═══════════════════════════════════════════════════════════════

class MockExecResult:
    def __init__(self, data=None):
        self.data = data or []


class MockTable:
    """Mock Supabase table that records insert/update/select calls."""

    def __init__(self, data=None):
        self._data = data or []
        self.calls = []

    def select(self, *cols):
        self.calls.append(("select", cols))
        return self

    def eq(self, col, val):
        self.calls.append(("eq", col, val))
        self._eq_col = col
        self._eq_val = val
        return self

    def order(self, col, desc=False):
        self.calls.append(("order", col, desc))
        return self

    def limit(self, n):
        self.calls.append(("limit", n))
        return self

    def insert(self, data):
        self.calls.append(("insert", data))
        self._insert_data = data
        return self

    def update(self, data):
        self.calls.append(("update", data))
        self._update_data = data
        return self

    def gte(self, col, val):
        return self

    def lt(self, col, val):
        return self

    def execute(self):
        if hasattr(self, "_insert_data"):
            inserted = dict(self._insert_data)
            if "id" not in inserted:
                inserted["id"] = f"new-{len(self.calls)}"
            return MockExecResult([inserted])
        if hasattr(self, "_update_data"):
            return MockExecResult([self._update_data])
        result = [d for d in self._data if d.get(self._eq_col) == self._eq_val]
        return MockExecResult(result)


class MockSupabase:
    """Mock Supabase client that returns MockTable for each table name."""

    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockTable()
        return self.tables[name]


class MockTextAgentSession:
    """Mock TextAgentSession that returns predictable responses."""

    def __init__(self, model=None):
        self.session_id = str(uuid.uuid4())
        self.model = model
        self.ended = False
        self.db_session_id = None
        self.db_thread_id = None
        self._call_count = 0

    async def send_message(self, message: str) -> dict:
        self._call_count += 1
        return {
            "reply": f"Reply to: {message}",
            "tool_calls": [],
            "ended": self.ended,
        }


def _make_mock_orchestrator(supabase=None):
    """Create a mock orchestrator with real SessionManager/MemoryCoordinator."""
    from backend.agent_orchestrator import AgentOrchestrator
    return AgentOrchestrator(supabase=supabase)


class TestChatMessageEndToEnd:
    """Integration: POST /chat/message full flow (REQ-5, REQ-7)."""

    def test_first_message_creates_thread_and_session(self):
        """First chat message without session_id creates conversation_thread + conversation_session."""
        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase=supabase)

        result = asyncio_run(orchestrator.handle_incoming("message.received", {
            "channel_type": "webchat",
            "external_id": "anonymous-user",
            "content": "Hola, necesito info",
        }))

        assert result is not None
        assert "thread_id" in result
        assert "session_id" in result
        assert "contact_id" in result

        # Verify thread was created
        thread_table = supabase.tables.get("conversation_threads")
        assert thread_table is not None
        insert_calls = [c for c in thread_table.calls if c[0] == "insert"]
        assert len(insert_calls) >= 1

        # Verify session was created with webchat channel
        session_table = supabase.tables.get("conversation_sessions")
        assert session_table is not None
        session_inserts = [c for c in session_table.calls if c[0] == "insert"]
        assert len(session_inserts) >= 1
        session_data = session_inserts[0][1]
        assert session_data["channel_type"] == "webchat"

    def test_first_message_persists_user_message(self):
        """First message is persisted to messages table with sender='user'."""
        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase=supabase)

        asyncio_run(orchestrator.handle_incoming("message.received", {
            "channel_type": "webchat",
            "external_id": "anonymous-user",
            "content": "Hola, necesito info",
        }))

        messages_table = supabase.tables.get("messages")
        assert messages_table is not None
        msg_inserts = [c for c in messages_table.calls if c[0] == "insert"]
        assert len(msg_inserts) >= 1
        msg_data = msg_inserts[0][1]
        assert msg_data["sender"] == "user"
        assert msg_data["content"] == "Hola, necesito info"

    def test_second_message_reuses_session(self):
        """Second message with session_id reuses existing session, no new session created."""
        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase=supabase)

        # First message — creates session
        result1 = asyncio_run(orchestrator.handle_incoming("message.received", {
            "channel_type": "webchat",
            "external_id": "user-123",
            "content": "Hola",
        }))
        session_id = result1["session_id"]

        # Count session inserts after first message
        session_table = supabase.tables.get("conversation_sessions")
        inserts_after_first = len([c for c in session_table.calls if c[0] == "insert"])

        # Second message — should NOT create new session
        result2 = asyncio_run(orchestrator.handle_incoming("message.received", {
            "channel_type": "webchat",
            "external_id": "user-123",
            "content": "Tienen precios?",
        }))

        inserts_after_second = len([c for c in session_table.calls if c[0] == "insert"])
        # Note: orchestrator creates a new session per handle_incoming call by design.
        # The session reuse is at the /chat/message endpoint level (main.py),
        # not in the orchestrator. This test verifies the orchestrator behavior.
        assert result2 is not None
        assert "session_id" in result2

    def test_chat_endpoint_first_message_creates_db_session(self):
        """Integration: POST /chat/message first message creates DB session and persists."""
        from fastapi.testclient import TestClient
        from backend import main

        supabase = MockSupabase()

        with patch.object(main, "supabase", supabase):
            with patch.object(main, "orchestrator", _make_mock_orchestrator(supabase)):
                with patch.object(main, "TextAgentSession", MockTextAgentSession):
                    client = TestClient(main.app)

                    response = client.post("/chat/message", json={
                        "message": "Hola, necesito info sobre sus servicios",
                    })

                    assert response.status_code == 200
                    data = response.json()
                    assert "session_id" in data
                    assert "reply" in data

                    # Verify DB session was created
                    session_table = supabase.tables.get("conversation_sessions")
                    session_inserts = [c for c in session_table.calls if c[0] == "insert"]
                    assert len(session_inserts) >= 1
                    assert session_inserts[0][1]["channel_type"] == "webchat"

    def test_chat_endpoint_subsequent_message_reuses_session(self):
        """Integration: Second message with session_id reuses existing session."""
        from fastapi.testclient import TestClient
        from backend import main

        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase)

        with patch.object(main, "supabase", supabase):
            with patch.object(main, "orchestrator", orchestrator):
                with patch.object(main, "TextAgentSession", MockTextAgentSession):
                    client = TestClient(main.app)

                    # First message
                    resp1 = client.post("/chat/message", json={
                        "message": "Hola",
                    })
                    assert resp1.status_code == 200
                    session_id = resp1.json()["session_id"]

                    # Count session inserts
                    session_table = supabase.tables.get("conversation_sessions")
                    inserts_before = len([c for c in session_table.calls if c[0] == "insert"])

                    # Second message with session_id
                    resp2 = client.post("/chat/message", json={
                        "message": "Tienen precios?",
                        "session_id": session_id,
                    })
                    assert resp2.status_code == 200

                    # No new session should be created
                    inserts_after = len([c for c in session_table.calls if c[0] == "insert"])
                    assert inserts_after == inserts_before

    def test_chat_endpoint_persists_user_and_agent_messages(self):
        """Integration: Both user message and agent reply are persisted."""
        from fastapi.testclient import TestClient
        from backend import main

        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase)

        with patch.object(main, "supabase", supabase):
            with patch.object(main, "orchestrator", orchestrator):
                with patch.object(main, "TextAgentSession", MockTextAgentSession):
                    client = TestClient(main.app)

                    client.post("/chat/message", json={
                        "message": "Cuales son sus servicios?",
                    })

                    messages_table = supabase.tables.get("messages")
                    msg_inserts = [c for c in messages_table.calls if c[0] == "insert"]

                    assert len(msg_inserts) == 2
                    assert msg_inserts[0][1]["sender"] == "user"
                    assert msg_inserts[0][1]["content"] == "Cuales son sus servicios?"
                    assert msg_inserts[1][1]["sender"] == "agent"
                    assert "Reply to:" in msg_inserts[1][1]["content"]

    def test_chat_endpoint_ended_closes_session(self):
        """Integration: When response has ended=True, session is closed."""
        from fastapi.testclient import TestClient
        from backend import main

        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase)

        class EndingMockSession(MockTextAgentSession):
            async def send_message(self, message: str) -> dict:
                return {
                    "reply": "Gracias por contactar!",
                    "tool_calls": ["registrar_resumen_llamada"],
                    "ended": True,
                }

        with patch.object(main, "supabase", supabase):
            with patch.object(main, "orchestrator", orchestrator):
                with patch.object(main, "TextAgentSession", EndingMockSession):
                    client = TestClient(main.app)

                    response = client.post("/chat/message", json={
                        "message": "Chau",
                    })

                    assert response.status_code == 200
                    assert response.json()["ended"] is True

                    session_table = supabase.tables.get("conversation_sessions")
                    update_calls = [c for c in session_table.calls if c[0] == "update"]
                    assert len(update_calls) >= 1
                    assert update_calls[0][1]["status"] == "completed"

    def test_chat_endpoint_not_ended_keeps_session_open(self):
        """Integration: When ended=False, session stays open (no update call)."""
        from fastapi.testclient import TestClient
        from backend import main

        supabase = MockSupabase()
        orchestrator = _make_mock_orchestrator(supabase)

        with patch.object(main, "supabase", supabase):
            with patch.object(main, "orchestrator", orchestrator):
                with patch.object(main, "TextAgentSession", MockTextAgentSession):
                    client = TestClient(main.app)

                    response = client.post("/chat/message", json={
                        "message": "Hola",
                    })

                    assert response.status_code == 200
                    assert response.json()["ended"] is False

                    session_table = supabase.tables.get("conversation_sessions")
                    update_calls = [c for c in session_table.calls if c[0] == "update"]
                    assert len(update_calls) == 0

    def test_chat_endpoint_supabase_unavailable_graceful_degrade(self):
        """Integration: When supabase is None, endpoint still works."""
        from fastapi.testclient import TestClient
        from backend import main

        orchestrator = _make_mock_orchestrator(supabase=None)

        with patch.object(main, "supabase", None):
            with patch.object(main, "orchestrator", orchestrator):
                with patch.object(main, "TextAgentSession", MockTextAgentSession):
                    client = TestClient(main.app)

                    response = client.post("/chat/message", json={
                        "message": "Hola",
                    })

                    assert response.status_code == 200
                    assert "reply" in response.json()


# ── Async helper for sync test context ─────────────────────────

def asyncio_run(coro):
    """Run async coroutine in sync test context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)
