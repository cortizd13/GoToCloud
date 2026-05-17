# Tests for Tier3RAGMemory
# Phase 6 — Tests & Verification

import asyncio
from backend.memory.tier3_rag import Tier3RAGMemory


class MockTable:
    def __init__(self, data=None, error=None):
        self._data = data or []
        self._error = error

    def select(self, *cols):
        return self

    def eq(self, col, val):
        self._col = col
        self._val = val
        return self

    def order(self, col, desc=True):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def insert(self, data):
        self._insert_result = MockExecResult([{"id": "embed-1"}])
        return self

    def delete(self):
        return self

    def execute(self):
        if hasattr(self, "_insert_result"):
            return self._insert_result
        if self._error:
            raise self._error
        result = self._data
        if hasattr(self, '_col') and hasattr(self, '_val'):
            result = [d for d in result if d.get(self._col) == self._val]
        if hasattr(self, '_limit'):
            result = result[:self._limit]
        return MockExecResult(result)


class MockExecResult:
    def __init__(self, data):
        self.data = data


class MockSupabase:
    def __init__(self, data=None):
        self._data = data or []

    def table(self, name):
        return MockTable(self._data)


def test_store_chunk_saves_to_db():
    supabase = MockSupabase()
    memory = Tier3RAGMemory(supabase)

    result = asyncio.run(memory.store_chunk("thread-1", "msg-1", "Hello world"))
    assert result is not None


def test_store_chunk_returns_none_without_supabase():
    memory = Tier3RAGMemory(supabase=None)
    result = asyncio.run(memory.store_chunk("thread-1", "msg-1", "Hello"))
    assert result is None


def test_search_similar_returns_results():
    supabase = MockSupabase([
        {"content_chunk": "First chunk", "thread_id": "thread-1"},
        {"content_chunk": "Second chunk", "thread_id": "thread-1"},
    ])

    memory = Tier3RAGMemory(supabase)
    result = asyncio.run(memory.search_similar([0.1, 0.2], thread_id="thread-1"))

    assert len(result) == 2


def test_search_similar_empty_without_supabase():
    memory = Tier3RAGMemory(supabase=None)
    result = asyncio.run(memory.search_similar([0.1, 0.2]))
    assert result == []


def test_delete_thread_embeddings():
    supabase = MockSupabase()
    memory = Tier3RAGMemory(supabase)

    # Should not raise
    asyncio.run(memory.delete_thread_embeddings("thread-1"))


def test_delete_thread_embeddings_no_crash_without_supabase():
    memory = Tier3RAGMemory(supabase=None)
    asyncio.run(memory.delete_thread_embeddings("thread-1"))