"""
Sistema conversacional voice-to-voice con Gemini Live — GoToCloud Voicebot.

Arquitectura (3 tasks concurrentes):
  capture_and_send  — lee micrófono (PCM16 16kHz) → send_realtime_input
  receive_loop      — recibe respuestas de Gemini → cola de reproducción + transcripts
  play_audio        — lee la cola → speaker (PCM16 24kHz)

Uso:
  venv\\Scripts\\python backend\\voice_to_voice.py
  Habla. Ctrl+C para salir.
"""
import asyncio
import os
import sys
from pathlib import Path

# Asegura que el raíz del proyecto esté en sys.path para importar service/
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyaudio
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

from service.gotocloud_voicebot_tool import (
    GOTOCLOUD_TOOLS,
    SYSTEM_PROMPT,
    ejecutar_tool,
)

MODEL = os.getenv("GEMINI_LIVE_MODEL", "models/gemini-3.1-flash-live-preview")

MIC_RATE = 16000
SPEAKER_RATE = 24000
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1


async def run():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no está configurada en .env")

    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )

    declarations = [types.FunctionDeclaration(**t) for t in GOTOCLOUD_TOOLS]
    tools = [types.Tool(function_declarations=declarations)]

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
        ),
        system_instruction=SYSTEM_PROMPT,
        tools=tools,
    )

    pa = pyaudio.PyAudio()
    playback_queue: asyncio.Queue[bytes] = asyncio.Queue()
    interrupted = asyncio.Event()

    mic_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=MIC_RATE,
        input=True, frames_per_buffer=CHUNK,
    )
    speaker_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=SPEAKER_RATE,
        output=True,
    )

    print(f"Modelo: {MODEL}")
    print(f"Tools: {len(GOTOCLOUD_TOOLS)} cargados")
    print("Conectando como Camila (GoToCloud)...")

    # Timer para fallback de timeout (60 segundos)
    timeout_task: asyncio.Task | None = None
    resumen_called = asyncio.Event()

    async def timeout_fallback():
        """Fallback: ejecutar registrar_resumen_llamada si no se ejecutó en 60s."""
        if not resumen_called.is_set():
            print("\n[timeout fallback] 60s sin respuesta — invocando registrar_resumen_llamada")
            try:
                result = ejecutar_tool("registrar_resumen_llamada", {
                    "resumen": "Llamada finalizada por tiempo de espera.",
                    "intention": "calida",
                    "score_lead": 50,
                    "servicios_interes": [],
                    "recomendaciones": "Cliente no completó la conversación.",
                })
                print(f"[timeout fallback] Resultado: {result}")
            except Exception as ex:
                print(f"[timeout fallback] Error: {ex}")

    def reset_timeout_timer():
        """Reinicia el timer de 60 segundos."""
        nonlocal timeout_task
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        timeout_task = asyncio.create_task(timeout_fallback())
        # No reiniciamos resumen_called aquí — solo se marca cuando se ejecuta la tool

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("Conectada. Habla con el micrófono. Ctrl+C para salir.\n")

        # Iniciar timer al principio
        reset_timeout_timer()

        async def capture_and_send():
            try:
                while True:
                    try:
                        chunk = await asyncio.to_thread(
                            mic_stream.read, CHUNK, exception_on_overflow=False
                        )
                    except OSError:
                        # Error transitorio del dispositivo de audio — continuar
                        await asyncio.sleep(0.01)
                        continue
                    await session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"\n[capture error: {e}]")

        async def receive_loop():
            gemini_speaking = False
            try:
                while True:
                    async for response in session.receive():

                        # ── Tool call ─────────────────────────────────
                        if response.tool_call:
                            fn_responses = []
                            for fc in response.tool_call.function_calls:
                                print(f"\n[tool] {fc.name}({dict(fc.args or {})})")
                                result = ejecutar_tool(fc.name, dict(fc.args or {}))
                                # Marcar si se ejecutó registrar_resumen_llamada
                                if fc.name == "registrar_resumen_llamada":
                                    resumen_called.set()
                                fn_responses.append(
                                    types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                )
                            await session.send(
                                input=types.LiveClientToolResponse(
                                    function_responses=fn_responses
                                )
                            )
                            continue

                        sc = response.server_content
                        if not sc:
                            continue

                        # Audio de respuesta → cola de reproducción
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data:
                                    await playback_queue.put(part.inline_data.data)

                        # Usuario interrumpió → vaciar la cola
                        if sc.interrupted:
                            interrupted.set()
                            while not playback_queue.empty():
                                playback_queue.get_nowait()
                            if gemini_speaking:
                                print()
                                gemini_speaking = False
                            print("[interrumpido]")

                        if sc.input_transcription and sc.input_transcription.text:
                            print(f"\nTú:    {sc.input_transcription.text}", end="", flush=True)
                            # Resetear timer cuando hay nuevo input del usuario
                            reset_timeout_timer()

                        if sc.output_transcription and sc.output_transcription.text:
                            if not gemini_speaking:
                                print("\nCamila:", end="", flush=True)
                                gemini_speaking = True
                            print(sc.output_transcription.text, end="", flush=True)

                        if sc.turn_complete:
                            if gemini_speaking:
                                print()
                                gemini_speaking = False
                            interrupted.clear()
                            print()
                            # Reiniciar timer después de turn_complete
                            reset_timeout_timer()

            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"\n[receive error: {e}]")

        async def play_audio():
            try:
                while True:
                    chunk = await playback_queue.get()
                    if not interrupted.is_set():
                        await asyncio.to_thread(speaker_stream.write, chunk)
            except asyncio.CancelledError:
                pass

        tasks = [
            asyncio.create_task(capture_and_send(), name="capture"),
            asyncio.create_task(receive_loop(), name="receive"),
            asyncio.create_task(play_audio(), name="play"),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            # Cancelar el timer de fallback
            if timeout_task and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    mic_stream.close()
    speaker_stream.close()
    pa.terminate()
    print("\nSesión cerrada.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nAdios.")
