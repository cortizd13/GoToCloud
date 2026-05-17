# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo structure

Two independent sub-projects — each has its own `CLAUDE.md` with detailed guidance:

| Directory | What it is |
|-----------|-----------|
| `gotocloud-frontend/` | React 19 + TypeScript + Vite — static visual replica of the GoToCloud contact page |
| `gotocloudgemini/` | Python 3.12 + FastAPI — AI phone/chat assistant "Camila" using Gemini Live API |

The sub-projects share no code and are deployed independently.

## Frontend (`gotocloud-frontend/`)

```bash
cd gotocloud-frontend
npm install
npm run dev        # local dev server
npm run lint       # ESLint
npm run build      # tsc -b && vite build (typecheck + bundle)
```

Architecture follows domain → infrastructure → application → presentation layering. Static content is separated from components. No backend, no auth, no new dependencies without clear need. See `gotocloud-frontend/CLAUDE.md` for full details.

## Backend (`gotocloudgemini/`)

```powershell
cd gotocloudgemini

# Install
venv\Scripts\pip install -r requirements.txt

# Run FastAPI server (Twilio + webchat bridge)
venv\Scripts\python -m uvicorn backend.main:app --reload

# Run voice-to-voice (real-time mic → Gemini → speaker)
venv\Scripts\python backend\voice_to_voice.py

# Run interactive text agent (CLI)
venv\Scripts\python backend\text_agent.py

# Run pytest (only tests/ directory)
venv\Scripts\python -m pytest
```

Always use `venv\Scripts\python`, not system Python.

Credentials go in `backend/.env` (never commit). Required vars: `GEMINI_API_KEY`, `GEMINI_LIVE_MODEL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `PUBLIC_URL`. See `gotocloudgemini/.env.example`.

### Architecture

The backend has two runtime patterns:

**Real-time bidirectional** (`voice_to_voice.py`): three concurrent asyncio tasks (capture/send mic audio, receive Gemini audio, playback). Used for standalone local testing with mic + speaker.

**WebSocket bridge** (`backend/main.py` — FastAPI): bridges two channels:
- `/twilio-stream` — Twilio phone calls (mulaw 8kHz ↔ PCM16 conversion via `audio_codec.py`)
- `/web-stream` — browser WebSocket (PCM16 16kHz in, PCM16 24kHz out)
- `/chat/message` — text chat REST endpoint (used by the frontend `ChatbotWidget`)
- `/dashboard/summary` — analytics pulled from Supabase

Both WebSocket paths use `GeminiLiveClient` (`gemini_live_client.py`), which handles tool calls internally inside `receive_audio()`.

**Key modules:**
- `service/gotocloud_voicebot_tool.py` — single source for `GOTOCLOUD_KB`, `GOTOCLOUD_TOOLS`, `SYSTEM_PROMPT`, and `ejecutar_tool`. If missing, `main.py` runs without tools (graceful degrade).
- `backend/agent_orchestrator.py` — `AgentOrchestrator` coordinates contact resolution, thread/session lifecycle, and 3-tier memory across channels.
- `backend/memory/` — `MemoryCoordinator` wires Tier 1 (in-memory, last 20 msgs), Tier 2 (Supabase `memory_summaries`), Tier 3 (RAG embeddings).
- `backend/channel_adapter.py` — `ChannelAdapterFactory` for multi-channel abstraction.
- `backend/event_bus.py` — async event bus used by the orchestrator.

**Non-obvious facts:**
- Files `backend/test_gemini_*.py` are standalone scripts (`asyncio.run(main())`), **not pytest**. Run with `python`, not `pytest`.
- `pytest` only discovers `tests/` (set in `pytest.ini`).
- `.env` is inside `backend/`, not the project root. Scripts load it via `load_dotenv(Path(__file__).parent / ".env")`.
- Gemini Live SDK requires `api_version="v1beta"`. Audio input uses `session.send_realtime_input(audio=types.Blob(...))`, not `session.send()`.
- The agent persona is "Camila", a Spanish (Colombian) assistant for GoToCloud.
- Supabase schema lives in `supabase/schema.sql`; seed with `backend/seed_kb.py`.

See `gotocloudgemini/CLAUDE.md` and `gotocloudgemini/AGENTS.md` for additional Gemini SDK details and audio format chain.
