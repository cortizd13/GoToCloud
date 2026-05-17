"""Tier 3: RAG Memory - Semantic search with embeddings and pgvector."""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Tier3RAGMemory:
    """Tier 3: Semantic memory with embeddings + pgvector."""

    def __init__(self, supabase=None, embedder=None):
        self.supabase = supabase
        self.embedder = embedder  # Optional: function(text) → list[float]

    async def store_chunk(self, thread_id: str, message_id: str | None,
                          content: str, embedding: list[float] | None = None,
                          model: str = "text-embedding-3-small") -> dict | None:
        """Store a message chunk with its embedding."""
        if not self.supabase:
            return None

        data = {
            "thread_id": thread_id,
            "content_chunk": content,
            "model": model,
        }
        if message_id:
            data["message_id"] = message_id
        if embedding:
            data["embedding"] = embedding

        try:
            result = self.supabase.table("memory_embeddings").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning(f"Tier3 store_chunk error: {e}")
            return None

    async def search_similar(self, query_embedding: list[float],
                             thread_id: str | None = None,
                             limit: int = 5) -> list[dict[str, Any]]:
        """Search for semantically similar content. For MVP with pgvector."""
        if not self.supabase:
            return []

        try:
            # Note: pgvector support depends on Supabase client version
            # For actual similarity: order(embedding.op('<->')(query_embedding))
            query = self.supabase.table("memory_embeddings")\
                .select("*")\
                .order("embedding", desc=True)\
                .limit(limit)

            if thread_id:
                query = query.eq("thread_id", thread_id)

            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Tier3 search error: {e}")
            return []

    async def delete_thread_embeddings(self, thread_id: str):
        """Clean up embeddings when a thread is archived."""
        if not self.supabase:
            return
        try:
            self.supabase.table("memory_embeddings")\
                .delete()\
                .eq("thread_id", thread_id)\
                .execute()
        except Exception as e:
            logger.warning(f"Tier3 delete error: {e}")