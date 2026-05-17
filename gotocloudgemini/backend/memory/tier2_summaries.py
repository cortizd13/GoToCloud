"""Tier 2: Persistent Summaries - PostgreSQL-backed conversation summaries."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class Tier2SummaryMemory:
    """Tier 2: Persistent conversation summaries in PostgreSQL."""

    def __init__(self, supabase=None, summarizer: Callable[[str], Awaitable[str]] | None = None):
        self.supabase = supabase
        self.summarizer = summarizer  # Optional: AI summarization function

    async def get_latest(self, thread_id: str) -> str | None:
        """Get the most recent summary for a thread."""
        if not self.supabase:
            return None
        try:
            result = self.supabase.table("memory_summaries")\
                .select("summary_text")\
                .eq("thread_id", thread_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            return result.data[0]["summary_text"] if result.data else None
        except Exception as e:
            logger.warning(f"Tier2 get_latest error: {e}")
            return None

    async def save(self, thread_id: str, summary_text: str):
        """Persist a new summary."""
        if not self.supabase:
            return
        try:
            self.supabase.table("memory_summaries").insert({
                "thread_id": thread_id,
                "summary_text": summary_text,
            }).execute()
            logger.info(f"Tier2 summary saved for thread {thread_id}")
        except Exception as e:
            logger.warning(f"Tier2 save error: {e}")

    async def generate_summary(self, conversation_text: str) -> str:
        """Generate a summary from conversation text using the configured summarizer."""
        if self.summarizer:
            return await self.summarizer(conversation_text)
        # Fallback: simple truncation
        return conversation_text[:500] + ("..." if len(conversation_text) > 500 else "")

    async def get_all(self, thread_id: str, limit: int = 5) -> list[dict]:
        """Get recent summaries for context building."""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("memory_summaries")\
                .select("*")\
                .eq("thread_id", thread_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Tier2 get_all error: {e}")
            return []