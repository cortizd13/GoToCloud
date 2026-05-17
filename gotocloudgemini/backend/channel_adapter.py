# Channel Adapter Interface + Event Model
# Phase 2 — Core Abstractions

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """Supported channel types for multi-channel AI agent."""
    VOICE = "voice"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEBCHAT = "webchat"
    SMS = "sms"


@dataclass
class ChannelEvent:
    """
    Canonical event format that ALL channel adapters produce.

    This is the unified event structure that abstracts away the differences
    between voice (audio), WhatsApp (text/media), Telegram, webchat, and SMS.
    """
    channel_type: ChannelType
    external_id: str  # Phone number, WhatsApp ID, Telegram chat ID, etc.
    content: str | None = None  # Text content (None for voice audio)
    audio_pcm: bytes | None = None  # PCM16 audio chunks (for voice channel)
    content_type: str = "text"  # "text" | "audio" | "event"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IChannelAdapter(ABC):
    """
    Abstract base for all channel adapters.

    Each adapter implements the specific protocol for its channel:
    - Twilio WebSocket for voice
    - WhatsApp Business API
    - Telegram Bot API
    - WebSocket for webchat
    - SMS gateway (Twilio/others)
    """

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """Return the channel type this adapter handles."""
        ...

    @abstractmethod
    async def send_message(
        self,
        contact_external_id: str,
        content: str,
        metadata: dict | None = None
    ) -> dict:
        """
        Send a message to a contact on this channel.

        Args:
            contact_external_id: The external identifier (phone, chat_id, etc.)
            content: The message content to send
            metadata: Optional metadata (attachments, buttons, etc.)

        Returns:
            dict with at least 'success' key, plus channel-specific response data
        """
        ...

    @abstractmethod
    async def receive_events(self) -> AsyncIterator[ChannelEvent]:
        """
        Yield incoming events from this channel.

        This is a long-running async iterator that should run until cancelled.
        Each yielded ChannelEvent represents an incoming message or event.
        """
        ...


class ChannelAdapterFactory:
    """
    Registry + factory for channel adapters.

    Allows dynamic registration and retrieval of adapters by channel type.
    Supports pluggable channel backends.
    """
    _adapters: dict[ChannelType, type[IChannelAdapter]] = {}

    @classmethod
    def register(
        cls,
        channel_type: ChannelType,
        adapter_cls: type[IChannelAdapter]
    ) -> None:
        """Register an adapter class for a channel type."""
        cls._adapters[channel_type] = adapter_cls
        logger.info(f"Registered adapter {adapter_cls.__name__} for {channel_type.value}")

    @classmethod
    def get_adapter(cls, channel_type: ChannelType) -> IChannelAdapter:
        """Get an instance of the adapter for the given channel type."""
        if channel_type not in cls._adapters:
            raise ValueError(
                f"No adapter registered for channel type: {channel_type.value}. "
                f"Available: {[ct.value for ct in cls._adapters.keys()]}"
            )
        return cls._adapters[channel_type]()

    @classmethod
    def list_registered(cls) -> list[ChannelType]:
        """Return list of registered channel types."""
        return list(cls._adapters.keys())

    @classmethod
    def list_channels(cls) -> list[str]:
        """Return list of registered channel type values as strings."""
        return [c.value for c in cls._adapters.keys()]

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (useful for testing)."""
        cls._adapters.clear()