# Tests for Tier2SummaryMemory
# Phase 6 — Tests & Verification

import asyncio
from backend.memory.tier2_summaries import Tier2SummaryMemory


class MockTable:
    """Mock for supabase table chain."""
    def __init__(self, data=None, error=None):
        self._data = data or []
        self._error = error
        self._filters = {}
        self._order_col = None
        self._order_desc = False
        self._limit_val = None

    def select(self, *cols):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, col, desc=False):
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def insert(self, data):
        if self._error:
            raise self._error
        self._insert_result = MockExecResult([{"id": "new-id"}])
        return self

    def execute(self):
        if self._error:
            raise self._error
        if hasattr(self, "_insert_result"):
            return self._insert_result
        # Filter data based on eq filters
        result = [d for d in self._data if all(d.get(k) == v for k, v in self._filters.items())]
        if self._order_col and self._order_desc:
            result = list(reversed(result))
        if self._limit_val:
            result = result[:self._limit_val]
        return MockExecResult(result)


class MockExecResult:
    def __init__(self, data):
        self.data = data


class MockSupabase:
    def __init__(self, data=None, error=None):
        self._data = data or []
        self._error = error

    def table(self, name):
        return MockTable(self._data, self._error)


def test_get_latest_returns_summary():
    supabase = MockSupabase([
        {"summary_text": "Earlier summary", "thread_id": "thread-1", "created_at": "2024-01-01"},
        {"summary_text": "Latest summary", "thread_id": "thread-1", "created_at": "2024-01-02"},
    ])

    memory = Tier2SummaryMemory(supabase)

    result = asyncio.run(memory.get_latest("thread-1"))
    assert result == "Latest summary"


def test_get_latest_returns_none_when_empty():
    supabase = MockSupabase([])
    memory = Tier2SummaryMemory(supabase)

    result = asyncio.run(memory.get_latest("thread-1"))
    assert result is None


def test_get_latest_graceful_without_supabase():
    memory = Tier2SummaryMemory(supabase=None)
    result = asyncio.run(memory.get_latest("thread-1"))
    assert result is None


def test_save_persists_summary():
    supabase = MockSupabase()
    memory = Tier2SummaryMemory(supabase)

    asyncio.run(memory.save("thread-1", "Test summary"))
    # No exception means success


def test_get_all_returns_ordered_summaries():
    supabase = MockSupabase([
        {"summary_text": "Old", "thread_id": "thread-1", "created_at": "2024-01-01"},
        {"summary_text": "New", "thread_id": "thread-1", "created_at": "2024-01-02"},
    ])

    memory = Tier2SummaryMemory(supabase)
    result = asyncio.run(memory.get_all("thread-1", limit=2))

    assert len(result) == 2
    assert result[0]["summary_text"] == "New"


def test_generate_summary_with_summarizer():
    async def my_summarizer(text):
        return f"SUMMARY: {text[:20]}"

    memory = Tier2SummaryMemory(summarizer=my_summarizer)
    result = asyncio.run(memory.generate_summary("This is a long conversation..."))
    assert result.startswith("SUMMARY:")