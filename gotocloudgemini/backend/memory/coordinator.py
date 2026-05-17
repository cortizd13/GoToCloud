"""Memory Coordinator - Wires all 3 memory tiers together."""

from __future__ import annotations
import logging
from typing import Any, Callable, Awaitable

from .tier1_session import Tier1SessionMemory
from .tier2_summaries import Tier2SummaryMemory
from .tier3_rag import Tier3RAGMemory

logger = logging.getLogger(__name__)


class MemoryCoordinator:
    """Coordinates all 3 memory tiers for a conversation."""

    def __init__(self, supabase=None, summarizer: Callable[[str], Awaitable[str]] | None = None,
                 embedder=None):
        self.tier1 = Tier1SessionMemory()
        self.tier2 = Tier2SummaryMemory(supabase, summarizer=summarizer)
        self.tier3 = Tier3RAGMemory(supabase, embedder=embedder)
        self.supabase = supabase

    async def add_message(self, session_id: str, thread_id: str | None,
                          role: str, content: str,
                          metadata: dict | None = None):
        """Add a message to all applicable tiers."""
        # Tier 1: always
        self.tier1.add(session_id, role, content, metadata)

        # Tier 2/3: persist to DB
        if self.supabase and thread_id:
            try:
                # Also persist to messages table
                msg_result = self.supabase.table("messages").insert({
                    "session_id": session_id,
                    "sender": role,
                    "content": content,
                    "metadata": metadata or {},
                }).execute()

                if msg_result.data and self.tier3:
                    message_id = msg_result.data[0]["id"]
                    # Store chunk for RAG (embedding generation deferred)
                    await self.tier3.store_chunk(thread_id, message_id, content)
            except Exception as e:
                logger.warning(f"MemoryCoordinator persist error: {e}")

    async def get_context(self, session_id: str, thread_id: str | None = None) -> dict[str, Any]:
        """Build context from all tiers for LLM injection."""
        context = {}

        # Tier 1: recent session messages
        context["recent_messages"] = self.tier1.get_recent(session_id, limit=10)

        # Tier 2: persistent summary
        if thread_id:
            summary = await self.tier2.get_latest(thread_id)
            if summary:
                context["summary"] = summary

        return context

    async def build_prompt_context(self, session_id: str, thread_id: str | None = None) -> str:
        """Build a formatted context string for LLM system prompt injection."""
        parts = []

        # Tier 2: persistent summary (long-term context)
        if thread_id:
            summary = await self.tier2.get_latest(thread_id)
            if summary:
                parts.append(f"[Contexto previo de la conversación: {summary}]")

        # Tier 1: recent messages (short-term context)
        recent = self.tier1.get_context(session_id, limit=5)
        if recent:
            parts.append(f"[Mensajes recientes:\n{recent}]")

        return "\n\n".join(parts)

    async def generate_and_save_summary(self, thread_id: str, session_id: str):
        """Generate a summary from session context and persist to Tier 2."""
        context = self.tier1.get_context(session_id, limit=50)
        if context:
            summary = await self.tier2.generate_summary(context)
            await self.tier2.save(thread_id, summary)
            logger.info(f"Summary generated for thread {thread_id}")

    def clear_session(self, session_id: str):
        self.tier1.clear_session(session_id)