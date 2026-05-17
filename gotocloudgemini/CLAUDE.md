# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Hackathon project: AI phone assistant using Gemini Live API. The goal is a voice-to-voice conversational agent that will eventually connect to Twilio for real phone calls. Currently at the Gemini Live integration stage — Twilio is not connected yet.

## Environment

- Python 3.12, venv at `venv/`
- All credentials in `backend/.env` (never commit this file)
- Always run scripts with `venv\Scripts\python`, not system Python

```powershell
# Install dependencies
venv\Scripts\pip install -r requirements.txt

# Run voice-to-voice (real-time mic + speaker)
venv\Scripts\python backend\voice_to_voice.py

# Run text-in / audio-out single turn test
venv\Scripts\python backend\test_gemini_live_text.py

# Run text-in / audio-out multi-turn test (keyboard input)
venv\Scripts\python backend\test_gemini_conversation.py
```

Listen to saved PCM audio:
```
ffplay -f s16le -ar 24000 -ac 1 gemini_response.pcm
ffplay -f s16le -ar 24000 -ac 1 turn_1.pcm
```

## Architecture

```
backend/
  gemini_live_client.py   # GeminiLiveClient — turn-based wrapper (for Twilio path)
  voice_to_voice.py       # Standalone voice-to-voice (mic → Gemini → speaker)
  test_gemini_live_text.py       # Single-turn: send text, receive audio, save .pcm
  test_gemini_conversation.py    # Multi-turn: keyboard text in, audio saved per turn
  .env                    # GEMINI_API_KEY, GEMINI_LIVE_MODEL
```

### Two usage patterns

**Turn-based** (`GeminiLiveClient`): designed for Twilio integration. Call `connect()`, then alternate `send_text()` / `send_audio_pcm16_16k()` with `receive_audio()`. The `receive_audio()` async generator yields PCM chunks and breaks on `turn_complete`.

**Real-time bidirectional** (`voice_to_voice.py`): three concurrent asyncio tasks running inside `client.aio.live.connect()`:
- `capture_and_send` — reads mic at 16kHz via `asyncio.to_thread`, calls `session.send_realtime_input(audio=Blob(...))`
- `receive_loop` — iterates `session.receive()`, puts audio in `playback_queue`, handles `interrupted` and prints transcripts
- `play_audio` — drains `playback_queue` to speaker at 24kHz; skips chunks when `interrupted` event is set

### Gemini Live SDK facts (google-genai 2.3.0)

- API version must be `v1beta`: `genai.Client(http_options={"api_version": "v1beta"})`
- Model env var: `GEMINI_LIVE_MODEL` (default `models/gemini-3.1-flash-live-preview`)
- **Real-time audio input**: `session.send_realtime_input(audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000"))` — use this, not `session.send()`
- **Text input**: `session.send(input=text, end_of_turn=True)`
- **Audio output** is in `response.server_content.model_turn.parts[*].inline_data.data` (PCM16 24kHz)
- `response.data` is a shorthand that also works but triggers an SDK warning about non-text parts
- **Turn detection**: `response.server_content.turn_complete` / `response.server_content.interrupted`
- `input_audio_transcription` and `output_audio_transcription` require `types.AudioTranscriptionConfig()`
- Built-in VAD configured via `types.RealtimeInputConfig(turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY")`

### Audio format chain (future Twilio path)

```
Twilio → mulaw 8kHz → [convert] → PCM16 16kHz → Gemini Live
Gemini Live → PCM16 24kHz → [convert] → mulaw 8kHz → Twilio
```

`send_audio_pcm16_16k()` in `GeminiLiveClient` already expects pre-converted PCM16 16kHz. The mulaw ↔ PCM conversion (via `audioop` or similar) is the next piece to add for Twilio.
