# Twilio Voice Channel Adapter
# Phase 3 — Channel Adapters

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import WebSocket

from ..channel_adapter import IChannelAdapter, ChannelEvent, ChannelType

logger = logging.getLogger(__name__)


class TwilioAdapter(IChannelAdapter):
    """Channel adapter for Twilio voice calls (WebSocket Media Stream)."""

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.VOICE

    def __init__(self):
        self._websocket: WebSocket | None = None
        self._stream_sid: str | None = None
        self._stop_event = asyncio.Event()

    async def connect_websocket(self, websocket: WebSocket) -> None:
        """Bind to an active Twilio WebSocket connection."""
        self._websocket = websocket
        self._stream_sid = None
        self._stop_event.clear()

    async def send_message(
        self,
        contact_external_id: str,
        content: str,
        metadata: dict | None = None
    ) -> dict:
        """
        Send a message through Twilio voice channel.

        For voice, this returns a notice that audio streaming is required.
        Use send_audio() for actual audio transmission.
        """
        return {
            "status": "voice_channel_requires_audio_stream",
            "contact_external_id": contact_external_id,
        }

    async def send_audio(self, pcm_chunk: bytes, input_rate: int = 24000) -> None:
        """Send PCM audio chunk to Twilio via WebSocket."""
        if not self._websocket or not self._stream_sid:
            logger.warning("TwilioAdapter.send_audio: no websocket or stream_sid")
            return

        try:
            from ..audio_codec import gemini_pcm_to_twilio_payload
            payload_b64 = gemini_pcm_to_twilio_payload(pcm_chunk, input_rate=input_rate)
            await self._websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": self._stream_sid,
                "media": {"payload": payload_b64},
            }))
        except Exception as e:
            logger.warning(f"TwilioAdapter.send_audio error: {e}")

    async def receive_events(self) -> AsyncIterator[ChannelEvent]:
        """
        Receive audio events from Twilio WebSocket Media Stream.

        Yields:
            ChannelEvent for each incoming audio chunk from Twilio
        """
        if not self._websocket:
            logger.warning("TwilioAdapter.receive_events: no websocket connected")
            return

        try:
            while not self._stop_event.is_set():
                raw = await self._websocket.receive_text()
                msg = json.loads(raw)
                event = msg.get("event")

                if event == "start":
                    self._stream_sid = msg["start"]["streamSid"]
                    logger.info(f"TwilioAdapter: stream started, streamSid={self._stream_sid}")
                    yield ChannelEvent(
                        channel_type=ChannelType.VOICE,
                        external_id=self._stream_sid,
                        content=None,
                        audio_pcm=None,
                        content_type="event",
                        metadata={"event": "start", "stream_sid": self._stream_sid},
                    )

                elif event == "media":
                    payload_b64 = msg["media"]["payload"]
                    try:
                        from ..audio_codec import twilio_payload_to_gemini_pcm
                        pcm = twilio_payload_to_gemini_pcm(payload_b64)
                        yield ChannelEvent(
                            channel_type=ChannelType.VOICE,
                            external_id=self._stream_sid or "unknown",
                            content=None,
                            audio_pcm=pcm,
                            content_type="audio",
                            metadata={"stream_sid": self._stream_sid},
                        )
                    except Exception as e:
                        logger.warning(f"TwilioAdapter: audio conversion error: {e}")

                elif event == "mark":
                    # Twilio mark messages (debugging/flow control)
                    mark_name = msg.get("mark", {}).get("name", "")
                    logger.debug(f"TwilioAdapter: mark received: {mark_name}")

                elif event == "stop":
                    logger.info("TwilioAdapter: stream stopped")
                    self._stop_event.set()
                    yield ChannelEvent(
                        channel_type=ChannelType.VOICE,
                        external_id=self._stream_sid or "unknown",
                        content=None,
                        audio_pcm=None,
                        content_type="event",
                        metadata={"event": "stop"},
                    )
                    break

        except Exception as e:
            logger.info(f"TwilioAdapter: connection closed: {e}")
        finally:
            self._stop_event.set()

    async def close(self) -> None:
        """Close the adapter and stop event processing."""
        self._stop_event.set()
        logger.info("TwilioAdapter: closed")


# Register adapter with factory
from ..channel_adapter import ChannelAdapterFactory

ChannelAdapterFactory.register(ChannelType.VOICE, TwilioAdapter)
logger.info("TwilioAdapter registered with ChannelAdapterFactory")