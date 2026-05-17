# AGENTS.md — GoToCloud Voicebot (Gemini Live)

AI phone assistant using **Gemini Live API** (voice-to-voice). Hackathon project. Twilio not yet connected.

## Quick start

```powershell
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python backend\voice_to_voice.py          # mic → Gemini → speaker
venv\Scripts\python backend\test_gemini_live_text.py    # 1-turn text → audio .pcm
venv\Scripts\python backend\test_gemini_conversation.py # multi-turn keyboard → audio .pcm
venv\Scripts\python backend\main.py                     # FastAPI (Twilio bridge)
venv\Scripts\python backend\seed_kb.py                  # populate Supabase KB tables
venv\Scripts\python -m pytest                           # only tests/test_audio_codec.py
```

Listen to saved PCM: `ffplay -f s16le -ar 24000 -ac 1 gemini_response.pcm`

## Architecture

```
backend/
  __init__.py               # package marker
  .env                      # GEMINI_API_KEY, GEMINI_LIVE_MODEL, PUBLIC_URL, SUPABASE_*
  gemini_live_client.py     # GeminiLiveClient — turn-based wrapper (Twilio path)
  voice_to_voice.py         # standalone: mic → Gemini → speaker, 3 concurrent tasks
  main.py                   # FastAPI — WebSocket bridge for Twilio
  audio_codec.py            # mulaw 8kHz ↔ PCM16 16kHz ↔ PCM16 24kHz (audioop)
  test_gemini_live_text.py  # standalone script, NOT pytest
  test_gemini_conversation.py   # standalone script, NOT pytest
  seed_kb.py                # populate Supabase KB tables from GOTOCLOUD_KB dict
  supabase_client.py        # singleton client, loads .env itself
service/
  __init__.py
  gotocloud_voicebot_tool.py  # GOTOCLOUD_KB, function tools, "Camila" system prompt
tests/
  __init__.py
  test_audio_codec.py       # pytest — codec round-trips
supabase/
  schema.sql                # run in Supabase SQL Editor before seed_kb.py
.env.example                # root-level template
```

## Non-obvious facts

- **`.env` is in `backend/`**, not project root. Scripts load via `load_dotenv(Path(__file__).parent / ".env")`.
- **Files named `test_*.py` in `backend/` are NOT pytest tests.** Standalone scripts (`asyncio.run(main())` at module level). Run with `python`, never `pytest`.
- **`pytest` only discovers `tests/`** (set in `pytest.ini`). No conftest, no fixtures.
- **Import strategy differs by entrypoint:** `main.py` uses package-relative (`from .gemini_live_client import`). Standalone scripts (`voice_to_voice.py`, `seed_kb.py`) insert project root into `sys.path` first. `service/gotocloud_voicebot_tool.py` supports both patterns via a try/except with fallback.
- **`service/gotocloud_voicebot_tool.py`** is the single source for KB data, function tools, and system prompt. If missing, `main.py` runs Gemini without tools (graceful degrade).
- **`voice_to_voice.py`** has `input_audio_transcription` / `output_audio_transcription` + VAD config (`RealtimeInputConfig`). The turn-based `GeminiLiveClient` does not — transcription is only in the standalone path.
- **Audio codec** uses `audioop` (stdlib, zero deps). Chain: mulaw 8kHz → PCM16 8kHz → ratecv → PCM16 16kHz (Twilio→Gemini), reverse for Gemini→Twilio.
- **`gemini_live_client.py`** handles tool calls internally inside `receive_audio()` — executes handler, sends function response, continues. Caller just iterates chunks.
- **Gemini Live SDK** (`google-genai`): API version must be `v1beta`. Audio input via `session.send_realtime_input(audio=types.Blob(...))`, not `session.send()`. Text input is `session.send(input=text, end_of_turn=True)`. Output audio is PCM16 24kHz in `response.server_content.model_turn.parts[*].inline_data.data`. Turn boundaries: `turn_complete` / `interrupted`.
- **Spanish (Colombian) — "Camila"** is the agent persona for GoToCloud, a Colombian cloud services company.
- **Supabase** tables: `empresa`, `servicios`, `metricas`, `productos_saas`, `clientes`. Schema in `supabase/schema.sql`. Anonymous RLS enabled. Seed via `seed_kb.py`.

## Two usage patterns

| Pattern | Entrypoint | Use case |
|---------|-----------|----------|
| Real-time bidir | `voice_to_voice.py` | Standalone mic→speaker, VAD-driven |
| Turn-based bridge | `main.py` (FastAPI) | Twilio via WebSocket, uses `GeminiLiveClient` |
