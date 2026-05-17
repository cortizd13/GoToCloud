import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from gemini_live_client import GeminiLiveClient

OUTPUT_FILE = Path(__file__).parent.parent / "gemini_response.pcm"


async def main():
    print("Connecting to Gemini Live...")
    client = GeminiLiveClient()
    await client.connect()
    print("Connected.")

    text = "Say hello in one short sentence."
    print(f"Sending: {text!r}")
    await client.send_text(text)

    print("Receiving audio...")
    audio_data = b""
    chunk_count = 0

    async for chunk in client.receive_audio():
        chunk_count += 1
        audio_data += chunk
        print(f"  Chunk #{chunk_count}: {len(chunk)} bytes")

    print(f"\nTotal: {len(audio_data)} bytes across {chunk_count} chunks")

    if audio_data:
        OUTPUT_FILE.write_bytes(audio_data)
        print(f"Saved to {OUTPUT_FILE}")
        print("Listen with: ffplay -f s16le -ar 24000 -ac 1 gemini_response.pcm")
    else:
        print("WARNING: No audio received.")

    await client.close()
    print("Session closed.")


asyncio.run(main())
