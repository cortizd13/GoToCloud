# Event Bus using PostgreSQL LISTEN/NOTIFY pattern
# Phase 2 — Core Abstractions

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    """
    Async event bus using PostgreSQL LISTEN/NOTIFY.

    MVP implementation — designed for future migration to Redis/Kafka.
    Currently uses analytics_events table for persistence and
    in-memory handlers for immediate processing.

    The LISTEN/NOTIFY pattern requires raw PostgreSQL connection,
    but Supabase client uses REST API. For MVP, we:
    1. Persist events to analytics_events table
    2. Execute registered handlers synchronously

    Future: Add proper LISTEN via supabase-py's realtime or raw connection.
    """

    def __init__(
        self,
        supabase=None,
        channel_name: str = "multichannel_events"
    ):
        self.supabase = supabase
        self.channel_name = channel_name
        self._handlers: dict[str, list[Callable]] = {}
        self._running = False
        self._listener_task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for a specific event type.

        Args:
            event_type: The event type to listen for (e.g., "message.received")
            handler: Callable to execute when event is published.
                     Can be sync or async.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to event type: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a handler for a specific event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from event type: {event_type}")
            except ValueError:
                pass  # Handler not in list

    async def publish(self, event_type: str, payload: dict) -> None:
        """
        Publish an event to the bus.

        Args:
            event_type: The type of event (e.g., "message.received", "call.started")
            payload: Event data as a dictionary
        """
        logger.info(f"EventBus publish: {event_type}")

        # 1. Persist to analytics_events table
        if self.supabase:
            try:
                self.supabase.table("analytics_events").insert({
                    "event_type": event_type,
                    "payload": payload,
                    "channel": self.channel_name,
                }).execute()
                logger.debug(f"Event persisted to analytics_events: {event_type}")
            except Exception as e:
                logger.warning(f"EventBus persist error: {e}")

        # 2. Execute registered handlers (sync for MVP)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Fire-and-forget for async handlers to not block publish
                    asyncio.create_task(handler(payload))
                    logger.debug(f"Async handler triggered for: {event_type}")
                else:
                    # Sync handlers execute immediately
                    handler(payload)
                    logger.debug(f"Sync handler executed for: {event_type}")
            except Exception as e:
                logger.error(f"EventBus handler error for {event_type}: {e}")

    async def start(self) -> None:
        """
        Start the event bus.

        Note: Full LISTEN/NOTIFY would require raw PostgreSQL connection.
        This MVP just sets the running flag.
        """
        self._running = True
        logger.info(f"EventBus started on channel: {self.channel_name}")

    async def stop(self) -> None:
        """Stop the event bus and cancel any listener tasks."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info(f"EventBus stopped: {self.channel_name}")

    def get_subscribers(self, event_type: str) -> int:
        """Return the number of subscribers for an event type."""
        return len(self._handlers.get(event_type, []))

    def list_event_types(self) -> list[str]:
        """Return list of event types with registered handlers."""
        return list(self._handlers.keys())