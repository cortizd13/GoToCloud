# Tests for channel adapter core abstractions
# Phase 6 — Tests & Verification

from backend.channel_adapter import ChannelType, ChannelEvent, IChannelAdapter, ChannelAdapterFactory
from abc import abstractmethod


# ── ChannelType enum ────────────────────────────────────────────────────────────

def test_channel_type_values():
    assert ChannelType.VOICE.value == "voice"
    assert ChannelType.WHATSAPP.value == "whatsapp"
    assert ChannelType.TELEGRAM.value == "telegram"
    assert ChannelType.WEBCHAT.value == "webchat"
    assert ChannelType.SMS.value == "sms"


# ── ChannelEvent dataclass ──────────────────────────────────────────────────────

def test_channel_event_text():
    event = ChannelEvent(
        channel_type=ChannelType.WHATSAPP,
        external_id="+573001234567",
        content="Hello",
        content_type="text"
    )
    assert event.channel_type == ChannelType.WHATSAPP
    assert event.external_id == "+573001234567"
    assert event.content == "Hello"
    assert event.content_type == "text"


def test_channel_event_audio():
    audio_data = b"\x00\x01\x02\x03"
    event = ChannelEvent(
        channel_type=ChannelType.VOICE,
        external_id="+573001234567",
        audio_pcm=audio_data,
        content_type="audio"
    )
    assert event.audio_pcm == audio_data
    assert event.content_type == "audio"


def test_channel_event_with_metadata():
    event = ChannelEvent(
        channel_type=ChannelType.TELEGRAM,
        external_id="123456789",
        content="Callback query",
        metadata={"callback_id": "abc123", "button": "confirm"}
    )
    assert event.metadata["callback_id"] == "abc123"


# ── IChannelAdapter ABC ─────────────────────────────────────────────────────────

def test_ichannel_adapter_is_abc():
    # Verify it's an abstract base class
    assert hasattr(IChannelAdapter, 'channel_type')
    assert hasattr(IChannelAdapter, 'send_message')
    assert hasattr(IChannelAdapter, 'receive_events')


# ── ChannelAdapterFactory ───────────────────────────────────────────────────────

def test_factory_register_and_get():
    class DummyAdapter(IChannelAdapter):
        @property
        def channel_type(self):
            return ChannelType.WEBCHAT

        async def send_message(self, contact_external_id, content, metadata=None):
            return {"success": True}

        async def receive_events(self):
            yield None

    ChannelAdapterFactory.register(ChannelType.WEBCHAT, DummyAdapter)
    adapter = ChannelAdapterFactory.get_adapter(ChannelType.WEBCHAT)
    assert isinstance(adapter, DummyAdapter)


def test_factory_list_channels():
    class DummyAdapter(IChannelAdapter):
        @property
        def channel_type(self):
            return ChannelType.VOICE
        async def send_message(self, contact_external_id, content, metadata=None):
            return {"success": True}
        async def receive_events(self):
            yield None

    ChannelAdapterFactory.clear()
    ChannelAdapterFactory.register(ChannelType.VOICE, DummyAdapter)
    channels = ChannelAdapterFactory.list_channels()
    assert "voice" in channels


def test_factory_unregistered_raises():
    ChannelAdapterFactory.clear()
    try:
        ChannelAdapterFactory.get_adapter(ChannelType.SMS)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No adapter registered" in str(e)