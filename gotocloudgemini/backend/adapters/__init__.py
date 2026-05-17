# Adapters package — placeholder for channel-specific adapter implementations
# Phase 2 — Core Abstractions

# Future adapter implementations can be added here:
# - adapters/voice_adapter.py (Twilio WebSocket)
# - adapters/whatsapp_adapter.py (WhatsApp Business API)
# - adapters/telegram_adapter.py (Telegram Bot API)
# - adapters/webchat_adapter.py (WebSocket)
# - adapters/sms_adapter.py (Twilio SMS)

from backend.channel_adapter import ChannelType, ChannelEvent, IChannelAdapter, ChannelAdapterFactory

__all__ = [
    "ChannelType",
    "ChannelEvent",
    "IChannelAdapter",
    "ChannelAdapterFactory",
]