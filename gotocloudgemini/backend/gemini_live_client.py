import os
from typing import AsyncIterator, Callable, Any

from google import genai
from google.genai import types


MODEL = os.getenv("GEMINI_LIVE_MODEL", "models/gemini-3.1-flash-live-preview")

_DEFAULT_SYSTEM_INSTRUCTION = (
    "Eres un asistente telefónico de IA para negocios. "
    "Hablas en español colombiano, de forma breve, natural y útil. "
    "Haz una pregunta a la vez. "
    "Si no sabes algo, ofrece pasar con un humano."
)


class GeminiLiveClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")

        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )
        self.session = None
        self._ctx = None
        self._tool_handler: Callable[[str, dict], Any] | None = None

    async def connect(
        self,
        tools: list[dict] | None = None,
        tool_handler: Callable[[str, dict], Any] | None = None,
        system_instruction: str | None = None,
        voice_name: str = "Zephyr",
    ):
        self._tool_handler = tool_handler

        gemini_tools = None
        if tools:
            declarations = [types.FunctionDeclaration(**t) for t in tools]
            gemini_tools = [types.Tool(function_declarations=declarations)]

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
            system_instruction=system_instruction or _DEFAULT_SYSTEM_INSTRUCTION,
            tools=gemini_tools,
        )

        self._ctx = self.client.aio.live.connect(model=MODEL, config=config)
        self.session = await self._ctx.__aenter__()
        return self

    async def close(self):
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None
            self.session = None

    async def send_text(self, text: str):
        if not self.session:
            raise RuntimeError("Gemini Live session is not connected")
        await self.session.send(input=text, end_of_turn=True)

    async def send_audio_pcm16_16k(self, pcm: bytes):
        """PCM16 16kHz mono little-endian → Gemini (desde Twilio)."""
        if not self.session:
            raise RuntimeError("Gemini Live session is not connected")
        await self.session.send_realtime_input(
            audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
        )

    async def receive_audio(self) -> AsyncIterator[bytes]:
        """
        Devuelve chunks PCM16 24kHz. Maneja tool_calls internamente.
        Se detiene en turn_complete — llama en loop para multi-turno.
        """
        if not self.session:
            raise RuntimeError("Gemini Live session is not connected")

        async for response in self.session.receive():

            # ── Tool call: ejecutar y responder a Gemini ──────────────
            if response.tool_call and self._tool_handler:
                responses = []
                for fc in response.tool_call.function_calls:
                    result = self._tool_handler(fc.name, dict(fc.args or {}))
                    responses.append(
                        types.FunctionResponse(
                            id=fc.id,
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                await self.session.send(
                    input=types.LiveClientToolResponse(function_responses=responses)
                )
                continue  # no yield, esperar respuesta de audio

            # ── Audio de respuesta ────────────────────────────────────
            if data := response.data:
                yield data

            if response.server_content and response.server_content.turn_complete:
                break
