# Tests for EventBus
# Phase 6 — Tests & Verification

import asyncio
from backend.event_bus import EventBus


class MockSupabase:
    """Minimal mock for supabase client."""
    def __init__(self):
        self.inserted = []

    def table(self, name):
        return self


def test_event_bus_subscribe_and_publish():
    bus = EventBus()
    results = []

    def handler(payload):
        results.append(payload)

    bus.subscribe("test.event", handler)
    asyncio.run(bus.publish("test.event", {"key": "value"}))

    assert len(results) == 1
    assert results[0]["key"] == "value"


def test_event_bus_multiple_handlers():
    bus = EventBus()
    results = []

    bus.subscribe("test.event", lambda p: results.append(p.get("a")))
    bus.subscribe("test.event", lambda p: results.append(p.get("b")))

    asyncio.run(bus.publish("test.event", {"a": 1, "b": 2}))
    assert results == [1, 2]


def test_event_bus_unsubscribe():
    bus = EventBus()
    results = []

    def handler(payload):
        results.append(payload)

    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)
    asyncio.run(bus.publish("test.event", {"test": True}))

    assert len(results) == 0


def test_event_bus_handler_error_isolation():
    bus = EventBus()
    results = []

    def bad_handler(payload):
        raise RuntimeError("Handler error")

    bus.subscribe("test.event", bad_handler)
    bus.subscribe("test.event", lambda p: results.append(p))

    # Should not raise, error is caught internally
    asyncio.run(bus.publish("test.event", {"ok": True}))
    assert results[0]["ok"] == True


def test_event_bus_lifecycle():
    bus = EventBus(supabase=MockSupabase())

    async def check_start():
        await bus.start()
        assert bus._running == True

        await bus.stop()
        assert bus._running == False

    asyncio.run(check_start())


def test_event_bus_get_subscribers():
    bus = EventBus()
    bus.subscribe("event1", lambda p: p)
    bus.subscribe("event1", lambda p: p)

    assert bus.get_subscribers("event1") == 2
    assert bus.get_subscribers("nonexistent") == 0


def test_event_bus_list_event_types():
    bus = EventBus()
    bus.subscribe("event_a", lambda p: p)
    bus.subscribe("event_b", lambda p: p)

    types = bus.list_event_types()
    assert "event_a" in types
    assert "event_b" in types