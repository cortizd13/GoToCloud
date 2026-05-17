"""
Prueba conversacional multi-turno con Gemini Live.
Texto de entrada por teclado, audio de salida como archivos PCM.

Escuchar respuesta N:
  ffplay -f s16le -ar 24000 -ac 1 turn_1.pcm
"""
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from gemini_live_client import GeminiLiveClient

OUTPUT_DIR = Path(__file__).parent.parent


async def receive_and_save(client: GeminiLiveClient, turn: int) -> int:
    audio_data = b""
    chunk_count = 0
    async for chunk in client.receive_audio():
        chunk_count += 1
        audio_data += chunk
        print(f"  chunk #{chunk_count}: {len(chunk)} bytes", end="\r")

    print()
    if audio_data:
        out = OUTPUT_DIR / f"turn_{turn}.pcm"
        out.write_bytes(audio_data)
        print(f"  -> {len(audio_data)} bytes guardados en {out.name}")
        print(f"     ffplay -f s16le -ar 24000 -ac 1 {out.name}")
    else:
        print("  -> Sin audio en este turno.")
    return len(audio_data)


async def main():
    print("Conectando con Gemini Live...")
    client = GeminiLiveClient()
    await client.connect()
    print("Conectado. Escribe tu mensaje (o 'salir' para terminar).\n")

    turn = 0
    try:
        while True:
            text = input("Tú: ").strip()
            if not text or text.lower() in {"salir", "exit", "quit"}:
                break

            turn += 1
            print(f"[turno {turn}] Enviando...")
            await client.send_text(text)

            print(f"[turno {turn}] Recibiendo audio...")
            await receive_and_save(client, turn)
            print()

    finally:
        await client.close()
        print(f"Sesión cerrada. {turn} turno(s) completados.")


asyncio.run(main())
