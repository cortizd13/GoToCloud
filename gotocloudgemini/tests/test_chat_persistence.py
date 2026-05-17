# Tests for PR #3: Chat Persistence
# Wire /chat/message endpoint to persist messages to Supabase

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
        import uuid
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


# ═══════════════════════════════════════════════════════════════
#  Task 3.1: First message creates thread + session (webchat)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_first_message_creates_thread_and_session():
    """First chat message without session_id creates conversation_thread + conversation_session."""
    supabase = MockSupabase()
    orchestrator = _make_mock_orchestrator(supabase=supabase)

    result = await orchestrator.handle_incoming("message.received", {
        "channel_type": "webchat",
        "external_id": "anonymous-user",
        "content": "Hola, necesito info",
    })

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


@pytest.mark.asyncio
async def test_first_message_persists_user_message():
    """First message is persisted to messages table with sender='user'."""
    supabase = MockSupabase()
    orchestrator = _make_mock_orchestrator(supabase=supabase)

    await orchestrator.handle_incoming("message.received", {
        "channel_type": "webchat",
        "external_id": "anonymous-user",
        "content": "Hola, necesito info",
    })

    # Verify message was persisted
    messages_table = supabase.tables.get("messages")
    assert messages_table is not None
    msg_inserts = [c for c in messages_table.calls if c[0] == "insert"]
    assert len(msg_inserts) >= 1
    msg_data = msg_inserts[0][1]
    assert msg_data["sender"] == "user"
    assert msg_data["content"] == "Hola, necesito info"


# ═══════════════════════════════════════════════════════════════
#  Task 3.2: Sender classification for agent responses
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_agent_message_persisted_with_sender_agent():
    """Agent responses are persisted with sender='agent'."""
    supabase = MockSupabase()
    orchestrator = _make_mock_orchestrator(supabase=supabase)

    # First persist a user message to get a session
    result = await orchestrator.handle_incoming("message.received", {
        "channel_type": "webchat",
        "external_id": "anonymous-user",
        "content": "Hola",
    })
    session_id = result["session_id"]

    # Now persist an agent response
    await orchestrator.memory.add_message(
        session_id, "agent", "Hola! Como puedo ayudarte?"
    )

    messages_table = supabase.tables.get("messages")
    msg_inserts = [c for c in messages_table.calls if c[0] == "insert"]

    # Should have at least 2 messages: user + agent
    assert len(msg_inserts) >= 2
    agent_msg = msg_inserts[1][1]
    assert agent_msg["sender"] == "agent"
    assert agent_msg["content"] == "Hola! Como puedo ayudarte?"


@pytest.mark.asyncio
async def test_system_message_persisted_with_sender_system():
    """System events are persisted with sender='system'."""
    supabase = MockSupabase()
    orchestrator = _make_mock_orchestrator(supabase=supabase)

    result = await orchestrator.handle_incoming("message.received", {
        "channel_type": "webchat",
        "external_id": "anonymous-user",
        "content": "Hola",
    })
    session_id = result["session_id"]

    await orchestrator.memory.add_message(
        session_id, "system", "Session started"
    )

    messages_table = supabase.tables.get("messages")
    msg_inserts = [c for c in messages_table.calls if c[0] == "insert"]

    system_msgs = [c for c in msg_inserts if c[1].get("sender") == "system"]
    assert len(system_msgs) >= 1
    assert system_msgs[0][1]["content"] == "Session started"


# ═══════════════════════════════════════════════════════════════
#  Task 3.3: Session lifecycle — close session on ended
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_close_session_marks_completed():
    """Closing a session updates status to 'completed' and sets ended_at."""
    supabase = MockSupabase()
    orchestrator = _make_mock_orchestrator(supabase=supabase)

    result = await orchestrator.handle_incoming("message.received", {
        "channel_type": "webchat",
        "external_id": "anonymous-user",
        "content": "Hola",
    })
    session_id = result["session_id"]

    await orchestrator.session_manager.close_session(session_id)

    session_table = supabase.tables.get("conversation_sessions")
    update_calls = [c for c in session_table.calls if c[0] == "update"]
    assert len(update_calls) >= 1
    update_data = update_calls[0][1]
    assert update_data["status"] == "completed"
    assert "ended_at" in update_data


@pytest.mark.asyncio
async def test_close_session_without_supabase_no_crash():
    """Closing session without Supabase is a no-op (graceful degrade)."""
    orchestrator = _make_mock_orchestrator(supabase=None)

    # Should not raise
    await orchestrator.session_manager.close_session("some-session-id")


# ═══════════════════════════════════════════════════════════════
#  Integration: full chat flow through endpoint
# ═══════════════════════════════════════════════════════════════

def test_chat_endpoint_first_message_persistence():
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


def test_chat_endpoint_subsequent_message_reuses_session():
    """Integration: Second message reuses existing session, doesn't create new one."""
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

                # Reset call counts to track new inserts
                session_table = supabase.tables.get("conversation_sessions")
                session_inserts_before = len([c for c in session_table.calls if c[0] == "insert"])

                # Second message with session_id
                resp2 = client.post("/chat/message", json={
                    "message": "Tienen precios?",
                    "session_id": session_id,
                })
                assert resp2.status_code == 200

                # No new session should be created
                session_inserts_after = len([c for c in session_table.calls if c[0] == "insert"])
                assert session_inserts_after == session_inserts_before


def test_chat_endpoint_ended_closes_session():
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

                # Session should be closed
                session_table = supabase.tables.get("conversation_sessions")
                update_calls = [c for c in session_table.calls if c[0] == "update"]
                assert len(update_calls) >= 1
                assert update_calls[0][1]["status"] == "completed"


# ═══════════════════════════════════════════════════════════════
#  Triangulation: edge cases
# ═══════════════════════════════════════════════════════════════

def test_chat_endpoint_not_ended_does_not_close_session():
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

                # Session should NOT be closed
                session_table = supabase.tables.get("conversation_sessions")
                update_calls = [c for c in session_table.calls if c[0] == "update"]
                assert len(update_calls) == 0


def test_chat_endpoint_persists_both_user_and_agent_messages():
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

                # Should have exactly 2 messages: user + agent
                assert len(msg_inserts) == 2
                assert msg_inserts[0][1]["sender"] == "user"
                assert msg_inserts[0][1]["content"] == "Cuales son sus servicios?"
                assert msg_inserts[1][1]["sender"] == "agent"
                assert "Reply to:" in msg_inserts[1][1]["content"]


def test_chat_endpoint_supabase_unavailable_graceful_degrade():
    """Integration: When supabase is None, endpoint still works (graceful degrade)."""
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

                # Should still return a valid response
                assert response.status_code == 200
                assert "reply" in response.json()
