"""Tier 1: Session Context - In-memory LRU cache for active conversations."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_SESSION_MESSAGES = 50


@dataclass
class MessageEntry:
    role: str  # 'user', 'agent', 'system'
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Tier1SessionMemory:
    """Tier 1: In-memory LRU session context."""

    def __init__(self, max_messages: int = MAX_SESSION_MESSAGES):
        self._sessions: dict[str, list[MessageEntry]] = {}
        self._max = max_messages

    def add(self, session_id: str, role: str, content: str, metadata: dict | None = None):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(MessageEntry(
            role=role, content=content, metadata=metadata or {}
        ))
        # Trim to max size
        if len(self._sessions[session_id]) > self._max:
            self._sessions[session_id] = self._sessions[session_id][-self._max:]

    def get_context(self, session_id: str, limit: int = 10) -> str:
        """Get recent messages as formatted text for LLM context."""
        messages = self._sessions.get(session_id, [])
        return "\n".join(
            f"{m.role}: {m.content}" for m in messages[-limit:]
        )

    def get_recent(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent messages as structured list."""
        messages = self._sessions.get(session_id, [])
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in messages[-limit:]
        ]

    def clear_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def clear_all(self):
        self._sessions.clear()