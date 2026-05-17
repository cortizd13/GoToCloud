# Tests for Tier1SessionMemory
# Phase 6 — Tests & Verification

from backend.memory.tier1_session import Tier1SessionMemory, MAX_SESSION_MESSAGES


def test_add_and_get_context():
    memory = Tier1SessionMemory()
    memory.add("session-1", "user", "Hello")
    memory.add("session-1", "agent", "Hi there")

    context = memory.get_context("session-1")
    assert "user: Hello" in context
    assert "agent: Hi there" in context


def test_get_recent():
    memory = Tier1SessionMemory()
    memory.add("session-1", "user", "First")
    memory.add("session-1", "user", "Second")
    memory.add("session-1", "user", "Third")

    recent = memory.get_recent("session-1", limit=2)
    assert len(recent) == 2
    assert recent[0]["content"] == "Second"
    assert recent[1]["content"] == "Third"


def test_max_session_messages_enforced():
    memory = Tier1SessionMemory(max_messages=3)

    for i in range(5):
        memory.add("session-1", "user", f"Message {i}")

    recent = memory.get_recent("session-1", limit=10)
    # Should keep only last 3
    assert len(recent) == 3
    assert recent[0]["content"] == "Message 2"


def test_clear_session():
    memory = Tier1SessionMemory()
    memory.add("session-1", "user", "Test")
    memory.clear_session("session-1")

    context = memory.get_context("session-1")
    assert context == ""


def test_get_context_with_limit():
    memory = Tier1SessionMemory()
    for i in range(10):
        memory.add("session-1", "user", f"Msg {i}")

    context = memory.get_context("session-1", limit=3)
    lines = context.split("\n")
    assert len(lines) == 3
    assert "Msg 9" in lines[-1]