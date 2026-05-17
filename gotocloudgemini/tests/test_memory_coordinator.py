# Tests for MemoryCoordinator
# Phase 6 — Tests & Verification

import asyncio
from backend.memory.coordinator import MemoryCoordinator


class MockTable:
    def __init__(self, data=None):
        self._data = data or []

    def insert(self, data):
        return MockExecResult([{"id": "msg-id"}])

    def execute(self):
        return MockExecResult(self._data)


class MockExecResult:
    def __init__(self, data):
        self.data = data


class MockSupabase:
    def __init__(self):
        pass

    def table(self, name):
        return MockTable()


def test_add_message_uses_tier1():
    coord = MemoryCoordinator()
    asyncio.run(coord.add_message("session-1", "thread-1", "user", "Hello"))

    context = coord.tier1.get_context("session-1")
    assert "Hello" in context


async def _mock_get_latest_old(tid):
    return "Old summary"

def test_get_context_returns_recent_and_summary():
    supabase = MockSupabase()
    coord = MemoryCoordinator(supabase=supabase)

    coord.tier1.add("session-1", "user", "Recent message")

    # Mock tier2 to return summary
    coord.tier2.get_latest = _mock_get_latest_old

    result = asyncio.run(coord.get_context("session-1", "thread-1"))

    assert "recent_messages" in result
    assert "summary" in result


async def _mock_get_latest_earlier(tid):
    return "Earlier summary"

def test_build_prompt_context_formats_correctly():
    supabase = MockSupabase()
    coord = MemoryCoordinator(supabase=supabase)

    coord.tier1.add("session-1", "user", "Hi")
    coord.tier1.add("session-1", "agent", "Hello")

    coord.tier2.get_latest = _mock_get_latest_earlier

    result = asyncio.run(coord.build_prompt_context("session-1", "thread-1"))

    assert "Earlier summary" in result
    assert "Hi" in result
    assert "Hello" in result


def test_clear_session_works():
    coord = MemoryCoordinator()
    coord.tier1.add("session-1", "user", "Test")

    coord.clear_session("session-1")

    context = coord.tier1.get_context("session-1")
    assert context == ""