# Tests for AgentOrchestrator
# Phase 6 — Tests & Verification

import asyncio
from backend.agent_orchestrator import AgentOrchestrator, AgentRegistry, SessionManager, AgentConfig


class MockTable:
    def __init__(self, data=None):
        self._data = data or []

    def select(self, *cols):
        return self

    def eq(self, col, val):
        self._eq_col = col
        self._eq_val = val
        return self

    def order(self, col, desc=False):
        return self

    def limit(self, n):
        return self

    def insert(self, data):
        self._insert_result = MockExecResult([{"id": "new-id"}])
        return self

    def update(self, data):
        return self

    def execute(self):
        if hasattr(self, "_insert_result"):
            return self._insert_result
        result = [d for d in self._data if d.get(self._eq_col) == self._eq_val]
        return MockExecResult(result)


class MockExecResult:
    def __init__(self, data):
        self.data = data


class MockSupabase:
    def __init__(self, agents=None, threads=None, sessions=None, contacts=None):
        self._agents = agents or []
        self._threads = threads or []
        self._sessions = sessions or []
        self._contacts = contacts or []

    def table(self, name):
        if name == "agents":
            return MockTable(self._agents)
        if name == "conversation_threads":
            return MockTable(self._threads)
        if name == "conversation_sessions":
            return MockTable(self._sessions)
        if name == "contacts":
            return MockTable(self._contacts)
        if name == "channel_identities":
            return MockTable([])
        if name == "messages":
            return MockTable([])
        return MockTable()


def test_agent_registry_cache():
    supabase = MockSupabase(agents=[
        {"id": "agent-1", "name": "Camila", "model": "gemini-2.0", "system_prompt": "You are Camila", "config": {}}
    ])
    registry = AgentRegistry(supabase)

    # First call - loads from DB
    config1 = asyncio.run(registry.get_agent("agent-1"))
    assert config1 is not None
    assert config1.name == "Camila"

    # Second call - from cache
    config2 = asyncio.run(registry.get_agent("agent-1"))
    assert config2 is not None
    assert config2.name == "Camila"


def test_agent_registry_missing():
    registry = AgentRegistry()
    result = asyncio.run(registry.get_agent("nonexistent"))
    assert result is None


def test_session_manager_find_or_create_thread():
    supabase = MockSupabase(threads=[
        {"id": "thread-1", "contact_id": "contact-1", "status": "active"}
    ])
    manager = SessionManager(supabase)

    result = asyncio.run(manager.find_or_create_thread("contact-1"))
    assert result["id"] == "thread-1"


def test_session_manager_creates_new_thread():
    supabase = MockSupabase()
    manager = SessionManager(supabase)

    result = asyncio.run(manager.find_or_create_thread("new-contact"))
    assert result["id"] == "new-id"


def test_session_manager_no_supabase():
    manager = SessionManager(supabase=None)
    result = asyncio.run(manager.find_or_create_thread("contact-1"))
    assert result["id"] == "new-thread"


def test_orchestrator_handle_incoming_creates_thread_and_session():
    supabase = MockSupabase(contacts=[{"id": "contact-1"}])
    orchestrator = AgentOrchestrator(supabase=supabase)

    result = asyncio.run(orchestrator.handle_incoming(
        "message.received",
        {
            "channel_type": "voice",
            "external_id": "+573001234567",
            "content": "Hello"
        }
    ))

    assert result is not None
    assert "thread_id" in result
    assert "session_id" in result
    assert "contact_id" in result


def test_orchestrator_missing_payload_fields():
    orchestrator = AgentOrchestrator(supabase=None)

    result = asyncio.run(orchestrator.handle_incoming(
        "message.received",
        {}  # Empty payload
    ))

    assert result is None