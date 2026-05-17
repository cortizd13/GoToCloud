"""
Audio codec — mulaw 8kHz ↔ PCM16 16kHz ↔ PCM16 24kHz.
Usa polyfills puros de Python (compatible con 3.13+ donde se eliminó audioop).
"""

import base64
import math

# ── µ-law polyfills (reemplazan audioop.ulaw2lin / lin2ulaw) ────────────

_BIAS = 0x84
_QUANT_MASK = 0x0F
_SEG_MASK = 0x70
_SEG_SHIFT = 4
_SIGN_BIT = 0x80
_CLIP = 32635

# Tabla de decodificación µ-law → PCM16 (precomputada)
_ULAW_DECODE_TABLE: list[int] = []
for _i in range(256):
    _byte = ~_i & 0xFF
    _sign = -1 if (_byte & _SIGN_BIT) else 1
    _segment = (_byte & _SEG_MASK) >> _SEG_SHIFT
    _quant = _byte & _QUANT_MASK
    _value = ((_quant << 1) + 33) << _segment
    _value = _value - 33
    _ULAW_DECODE_TABLE.append(_sign * _value)


def _ulaw2lin(data: bytes, width: int) -> bytes:
    """µ-law → PCM16 lineal (compatible con audioop.ulaw2lin)."""
    if width != 2:
        raise ValueError("ulaw2lin solo soporta width=2 (16-bit)")
    result = bytearray()
    for byte in data:
        sample = _ULAW_DECODE_TABLE[byte]
        # Clampear a 16-bit signed
        if sample > 32767:
            sample = 32767
        elif sample < -32768:
            sample = -32768
        result.extend(sample.to_bytes(2, "little", signed=True))
    return bytes(result)


def _lin2ulaw(data: bytes, width: int) -> bytes:
    """PCM16 lineal → µ-law (compatible con audioop.lin2ulaw)."""
    if width != 2:
        raise ValueError("lin2ulaw solo soporta width=2 (16-bit)")
    result = bytearray()
    for i in range(0, len(data), 2):
        sample = int.from_bytes(data[i : i + 2], "little", signed=True)
        # µ-law compression (G.711)
        sign = 0 if sample < 0 else _SIGN_BIT
        if sample < 0:
            sample = -sample
        if sample > _CLIP:
            sample = _CLIP
        sample += _BIAS
        exponent = 0
        if sample > 0:
            exponent = 7
            while sample < (1 << (exponent + 4)):
                exponent -= 1
        mantissa = (sample >> (exponent + 3)) & 0x0F
        ulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
        result.append(ulaw_byte)
    return bytes(result)


# ── ratecv polyfill ─────────────────────────────────────────────────────

def _ratecv(data: bytes, width: int, nchannels: int, inrate: int, outrate: int, state: object) -> tuple[bytes, object]:
    """Conversión de sample rate por interpolación lineal (compatible con audioop.ratecv)."""
    if width != 2:
        raise ValueError("ratecv solo soporta width=2 (16-bit)")
    if inrate == outrate:
        return data, state

    ratio = inrate / outrate
    total_samples = len(data) // (width * nchannels)
    out_samples = max(1, int(total_samples / ratio))

    result = bytearray()
    samples_in = [
        int.from_bytes(data[j * 2 : j * 2 + 2], "little", signed=True)
        for j in range(total_samples)
    ]

    for i in range(out_samples):
        pos = i * ratio
        idx = int(pos)
        frac = pos - idx
        idx0 = min(idx, total_samples - 1)
        idx1 = min(idx + 1, total_samples - 1)
        interp = int(samples_in[idx0] + frac * (samples_in[idx1] - samples_in[idx0]))
        if interp > 32767:
            interp = 32767
        elif interp < -32768:
            interp = -32768
        result.extend(interp.to_bytes(2, "little", signed=True))

    tail = b""
    # Devolver sobrante como tupla de bytes para compatibilidad con la API
    if state is not None:
        tail = state  # type: ignore[assignment]

    return bytes(result), tail


# ── API pública (misma interfaz que antes) ───────────────────────────────

def twilio_payload_to_gemini_pcm(payload_b64: str) -> bytes:
    """
    Twilio base64 mulaw 8kHz → PCM16 16kHz para Gemini.
    """
    mulaw_8k = base64.b64decode(payload_b64)
    pcm_8k = _ulaw2lin(mulaw_8k, 2)
    pcm_16k, _ = _ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k


def gemini_pcm_to_twilio_payload(pcm: bytes, input_rate: int = 24000) -> str:
    """
    PCM16 de Gemini (default 24kHz) → base64 mulaw 8kHz para Twilio.
    """
    pcm_8k, _ = _ratecv(pcm, 2, 1, input_rate, 8000, None)
    mulaw_8k = _lin2ulaw(pcm_8k, 2)
    return base64.b64encode(mulaw_8k).decode("ascii")
