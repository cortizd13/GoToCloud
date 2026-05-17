# Agent Orchestrator — Main Coordinator
# Phase 2 — Core Abstractions

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an AI agent."""
    agent_id: str
    name: str
    model: str
    system_prompt: str
    tools: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)


class AgentRegistry:
    """
    Registry for AI agents across companies.

    Provides lookup and caching for agent configurations,
    loading from the agents table and associated tools.
    """

    def __init__(self, supabase=None):
        self.supabase = supabase
        self._cache: dict[str, AgentConfig] = {}

    async def get_agent(self, agent_id: str) -> AgentConfig | None:
        """
        Look up agent by ID, with caching.

        Args:
            agent_id: The UUID of the agent

        Returns:
            AgentConfig if found, None otherwise
        """
        # Check cache first
        if agent_id in self._cache:
            logger.debug(f"AgentRegistry cache hit: {agent_id}")
            return self._cache[agent_id]

        if not self.supabase:
            return None

        try:
            result = self.supabase.table("agents").select("*").eq("id", agent_id).execute()

            if result.data:
                row = result.data[0]
                config = AgentConfig(
                    agent_id=row["id"],
                    name=row["name"],
                    model=row["model"],
                    system_prompt=row.get("system_prompt", ""),
                    tools=[],
                    config=row.get("config", {}),
                )

                # Load tools for this agent
                tools_result = self.supabase.table("agent_tools").select("*").eq("agent_id", agent_id).execute()
                config.tools = tools_result.data or []

                # Cache the config
                self._cache[agent_id] = config
                logger.info(f"AgentRegistry loaded agent: {agent_id} ({config.name})")
                return config

        except Exception as e:
            logger.warning(f"AgentRegistry lookup error for {agent_id}: {e}")

        return None

    async def find_agent_for_company(self, company_id: str) -> AgentConfig | None:
        """
        Find the default agent for a company.

        Args:
            company_id: The UUID of the company

        Returns:
            AgentConfig for the company's default agent, or None
        """
        if not self.supabase:
            return None

        try:
            result = self.supabase.table("agents").select("*").eq("company_id", company_id).limit(1).execute()

            if result.data:
                return await self.get_agent(result.data[0]["id"])

        except Exception as e:
            logger.warning(f"AgentRegistry company lookup error for {company_id}: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear the agent cache (useful for testing or refresh)."""
        self._cache.clear()
        logger.info("AgentRegistry cache cleared")


class SessionManager:
    """
    Manages conversation threads + sessions lifecycle.

    Handles the creation and retrieval of conversation threads
    and sessions across all channels.
    """

    def __init__(self, supabase=None):
        self.supabase = supabase

    async def find_or_create_thread(
        self,
        contact_id: str,
        company_id: str | None = None,
        topic: str | None = None
    ) -> dict:
        """
        Find active thread for contact, or create new one.

        Args:
            contact_id: The UUID of the contact
            company_id: Optional company UUID
            topic: Optional topic/title for new thread

        Returns:
            Thread record dict with at least 'id' key
        """
        logger.info(f"SessionManager: find_or_create_thread contact={contact_id}")

        if not self.supabase:
            return {"id": "new-thread", "contact_id": contact_id}

        try:
            # Search for active thread
            result = (
                self.supabase.table("conversation_threads")
                .select("*")
                .eq("contact_id", contact_id)
                .eq("status", "active")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                thread = result.data[0]
                logger.debug(f"Found existing thread: {thread['id']}")
                return thread

            # Create new thread
            data: dict[str, Any] = {"contact_id": contact_id}
            if company_id:
                data["company_id"] = company_id
            if topic:
                data["topic"] = topic

            new_thread = self.supabase.table("conversation_threads").insert(data).execute()
            thread = new_thread.data[0]
            logger.info(f"Created new thread: {thread['id']}")
            return thread

        except Exception as e:
            logger.warning(f"SessionManager thread error: {e}")
            return {"id": "new-thread", "contact_id": contact_id}

    async def create_session(
        self,
        thread_id: str,
        channel_type: str,
        channel_identity_id: str | None = None
    ) -> dict:
        """
        Create a new session within a thread.

        Args:
            thread_id: The UUID of the conversation thread
            channel_type: The channel type (voice, whatsapp, etc.)
            channel_identity_id: Optional channel identity UUID

        Returns:
            Session record dict with at least 'id' key
        """
        if not self.supabase:
            return {"id": "new-session", "thread_id": thread_id}

        try:
            data: dict[str, Any] = {
                "thread_id": thread_id,
                "channel_type": channel_type,
            }
            if channel_identity_id:
                data["channel_identity_id"] = channel_identity_id

            result = self.supabase.table("conversation_sessions").insert(data).execute()
            session = result.data[0]
            logger.info(f"Created session: {session['id']} for thread {thread_id}")
            return session

        except Exception as e:
            logger.warning(f"SessionManager session create error: {e}")
            return {"id": "new-session", "thread_id": thread_id}

    async def close_session(self, session_id: str) -> None:
        """
        Mark session as completed.

        Args:
            session_id: The UUID of the session to close
        """
        if not self.supabase:
            return

        try:
            self.supabase.table("conversation_sessions").update({
                "status": "completed",
                "ended_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            logger.info(f"Session closed: {session_id}")
        except Exception as e:
            logger.warning(f"SessionManager close error: {e}")


class MemoryCoordinator:
    """
    Coordinates 3-tier memory:
    - Tier 1: In-memory session context (last 20 messages)
    - Tier 2: Persistent summaries (memory_summaries table)
    - Tier 3: RAG embeddings (memory_embeddings table)
    """

    def __init__(self, supabase=None):
        self.supabase = supabase
        self._session_context: dict[str, list[dict]] = {}  # Tier 1: in-memory

    async def add_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """
        Add message to session context (Tier 1) and persist (Tier 2).

        Args:
            session_id: The UUID of the session
            sender: The sender role (user, agent, system)
            content: The message content
            metadata: Optional message metadata
        """
        # Tier 1: in-memory context
        if session_id not in self._session_context:
            self._session_context[session_id] = []

        self._session_context[session_id].append({
            "role": sender,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep only last 20 messages in memory
        if len(self._session_context[session_id]) > 20:
            self._session_context[session_id] = self._session_context[session_id][-20:]

        # Tier 2: persist to messages table
        if self.supabase:
            try:
                self.supabase.table("messages").insert({
                    "session_id": session_id,
                    "sender": sender,
                    "content": content,
                    "metadata": metadata or {},
                }).execute()
                logger.debug(f"Message persisted to session {session_id}")
            except Exception as e:
                logger.warning(f"MemoryCoordinator persist error: {e}")

    async def get_context(self, session_id: str) -> str:
        """
        Get recent context for session (Tier 1).

        Returns last 10 messages formatted as conversation.
        """
        messages = self._session_context.get(session_id, [])
        recent = messages[-10:] if len(messages) > 10 else messages
        return "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    async def get_summary(self, thread_id: str) -> str | None:
        """
        Get latest persistent summary (Tier 2).

        Returns the most recent summary text for the thread, or None.
        """
        if not self.supabase:
            return None

        try:
            result = (
                self.supabase.table("memory_summaries")
                .select("summary_text")
                .eq("thread_id", thread_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]["summary_text"]
        except Exception as e:
            logger.warning(f"MemoryCoordinator summary error: {e}")

        return None

    async def save_summary(self, thread_id: str, summary: str) -> None:
        """
        Persist a contextual summary (Tier 2).

        Args:
            thread_id: The UUID of the thread
            summary: The summary text to store
        """
        if not self.supabase:
            return

        try:
            self.supabase.table("memory_summaries").insert({
                "thread_id": thread_id,
                "summary_text": summary,
            }).execute()
            logger.info(f"Summary saved for thread {thread_id}")
        except Exception as e:
            logger.warning(f"MemoryCoordinator save summary error: {e}")


class AgentOrchestrator:
    """
    Main coordinator — ties adapters, agents, memory, and session lifecycle.

    This is the central entry point for handling incoming events from
    any channel, orchestrating the full flow from contact resolution
    to agent response generation.
    """

    def __init__(self, supabase=None, event_bus=None):
        self.supabase = supabase
        self.event_bus = event_bus
        self.agent_registry = AgentRegistry(supabase)
        self.session_manager = SessionManager(supabase)
        self.memory = MemoryCoordinator(supabase)

    async def handle_incoming(self, event_type: str, payload: dict) -> dict | None:
        """
        Main entry point for incoming events from any channel.

        Args:
            event_type: The type of event (e.g., "message.received")
            payload: Event payload containing channel_type, external_id, content, etc.

        Returns:
            Dict with thread_id, session_id, contact_id, context, summary,
            or None if contact resolution failed
        """
        logger.info(f"Orchestrator handling event: {event_type}")

        # 1. Extract contact info
        channel_type = payload.get("channel_type")
        external_id = payload.get("external_id")
        content = payload.get("content", "")

        if not channel_type or not external_id:
            logger.warning("Orchestrator: missing channel_type or external_id in payload")
            return None

        # 2. Find/create contact via channel_identity
        contact_id = await self._resolve_contact(channel_type, external_id)
        if not contact_id:
            logger.warning(f"Could not resolve contact for {channel_type}:{external_id}")
            return None

        # 3. Find/create thread
        thread = await self.session_manager.find_or_create_thread(
            contact_id,
            company_id=payload.get("company_id"),
            topic=payload.get("topic")
        )

        # 4. Create session
        session = await self.session_manager.create_session(
            thread["id"],
            channel_type,
            channel_identity_id=payload.get("channel_identity_id")
        )

        # 5. Add message to memory
        await self.memory.add_message(
            session["id"],
            "user",
            content,
            metadata=payload.get("metadata")
        )

        # 6. Get context for agent
        summary = await self.memory.get_summary(thread["id"])
        context = await self.memory.get_context(session["id"])

        logger.info(
            f"Orchestrator: thread={thread['id']}, session={session['id']}, "
            f"context_length={len(context)}, summary={'present' if summary else 'none'}"
        )

        return {
            "thread_id": thread["id"],
            "session_id": session["id"],
            "contact_id": contact_id,
            "context": context,
            "summary": summary,
        }

    async def _resolve_contact(
        self,
        channel_type: str,
        external_id: str
    ) -> str | None:
        """
        Resolve channel identity to unified contact.

        Creates new contact and channel_identity if not found.
        """
        if not self.supabase:
            # Return placeholder for testing without DB
            return "unresolved-contact"

        try:
            # Try to find existing channel identity
            result = (
                self.supabase.table("channel_identities")
                .select("contact_id")
                .eq("channel_type", channel_type)
                .eq("external_id", external_id)
                .limit(1)
                .execute()
            )

            if result.data:
                contact_id = result.data[0]["contact_id"]
                logger.debug(f"Resolved existing contact: {contact_id}")
                return contact_id

            # Create new contact + channel identity
            # Determine which fields to populate based on channel
            contact_data: dict[str, Any] = {}
            if channel_type in ("voice", "whatsapp", "sms"):
                contact_data["phones"] = [external_id]
            elif channel_type in ("telegram", "webchat"):
                contact_data["metadata"] = {"chat_id": external_id}

            new_contact = self.supabase.table("contacts").insert(contact_data).execute()
            contact_id = new_contact.data[0]["id"]

            # Create channel identity linking contact to external ID
            self.supabase.table("channel_identities").insert({
                "contact_id": contact_id,
                "channel_type": channel_type,
                "external_id": external_id,
            }).execute()

            logger.info(f"Created new contact {contact_id} for {channel_type}:{external_id}")
            return contact_id

        except Exception as e:
            logger.warning(f"Contact resolution error: {e}")
            return None

    async def start(self) -> None:
        """Start the orchestrator."""
        logger.info("AgentOrchestrator started")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        logger.info("AgentOrchestrator stopped")