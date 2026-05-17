import audioop
import base64

from backend.audio_codec import gemini_pcm_to_twilio_payload, twilio_payload_to_gemini_pcm


def _mulaw_payload(n_samples: int = 160) -> str:
    """Payload base64 de mulaw silencio (valor 0x7F) a 8kHz."""
    return base64.b64encode(bytes([0x7F] * n_samples)).decode("ascii")


def _pcm16_silence(n_samples: int, rate: int = 24000) -> bytes:
    """PCM16 silencio (ceros)."""
    return bytes(n_samples * 2)


# ── Twilio → Gemini ────────────────────────────────────────────────────────────

def test_twilio_to_gemini_returns_bytes():
    result = twilio_payload_to_gemini_pcm(_mulaw_payload(160))
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_twilio_to_gemini_upsamples_2x():
    # 160 mulaw → 160 PCM16 8kHz samples → ~320 PCM16 16kHz samples (~640 bytes)
    # audioop.ratecv puede producir 1-2 samples menos por artefacto de interpolación
    result = twilio_payload_to_gemini_pcm(_mulaw_payload(160))
    assert 630 <= len(result) <= 642


def test_twilio_to_gemini_empty_payload():
    # payload vacío → bytes vacíos, sin crash
    result = twilio_payload_to_gemini_pcm(base64.b64encode(b"").decode())
    assert result == b""


# ── Gemini → Twilio ────────────────────────────────────────────────────────────

def test_gemini_to_twilio_returns_str():
    result = gemini_pcm_to_twilio_payload(_pcm16_silence(960, 24000), input_rate=24000)
    assert isinstance(result, str)
    assert len(result) > 0


def test_gemini_to_twilio_valid_base64():
    result = gemini_pcm_to_twilio_payload(_pcm16_silence(960, 24000), input_rate=24000)
    decoded = base64.b64decode(result)
    # 960 samples 24kHz → 320 samples 8kHz → 320 mulaw bytes
    assert len(decoded) == 320


def test_gemini_to_twilio_downsamples_3x():
    # 960 PCM16 24kHz samples → 320 mulaw 8kHz bytes
    pcm = _pcm16_silence(960, 24000)
    payload = gemini_pcm_to_twilio_payload(pcm, input_rate=24000)
    assert len(base64.b64decode(payload)) == 320


def test_gemini_to_twilio_different_rate():
    # 320 PCM16 16kHz samples → 160 mulaw 8kHz bytes
    pcm = _pcm16_silence(320, 16000)
    payload = gemini_pcm_to_twilio_payload(pcm, input_rate=16000)
    assert len(base64.b64decode(payload)) == 160
