"""
Test de produccion — verifica que el servidor en la nube responde correctamente.
Uso: venv\Scripts\python.exe test_production.py [URL]
Si no se pasa URL, lee PUBLIC_URL de backend/.env
"""
import sys
import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "backend" / ".env")

try:
    import requests
except ImportError:
    print("Falta requests: venv\\Scripts\\pip install requests")
    sys.exit(1)

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False
    print("[WARN] websockets no instalado — test de WebSocket omitido")
    print("       instala con: venv\\Scripts\\pip install websockets\n")

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PUBLIC_URL", "").strip().rstrip("/")

if not BASE_URL:
    print("ERROR: pasa la URL como argumento o configura PUBLIC_URL en backend/.env")
    sys.exit(1)

WS_URL = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/twilio-stream"

print(f"Base URL : {BASE_URL}")
print(f"WS  URL  : {WS_URL}")
print("=" * 60)

PASS = "[PASS]"
FAIL = "[FAIL]"


def test_health():
    print("\n1. GET /health")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        if r.status_code == 200:
            print(f"   {PASS} {r.status_code} — {r.json()}")
        else:
            print(f"   {FAIL} Status {r.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"   {FAIL} Error de conexion: {e}")


def test_twiml():
    print("\n2. POST /twiml (simulando llamada Twilio)")
    payload = {
        "CallSid":    "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "AccountSid": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "From":       "+573001234567",
        "To":         "+12345678901",
        "CallStatus": "ringing",
        "Direction":  "inbound",
        "ApiVersion": "2010-04-01",
    }
    try:
        r = requests.post(f"{BASE_URL}/twiml", data=payload, timeout=10)
        if r.status_code == 200 and "twilio-stream" in r.text:
            print(f"   {PASS} {r.status_code} — XML recibido con WebSocket URL")
            stream_url = [l.strip() for l in r.text.splitlines() if "Stream" in l]
            print(f"   Stream: {stream_url[0] if stream_url else 'no encontrado'}")
        else:
            print(f"   {FAIL} Status {r.status_code}")
            print(f"   Body: {r.text[:300]}")
    except Exception as e:
        print(f"   {FAIL} Error de conexion: {e}")


async def test_websocket():
    print("\n3. WebSocket /twilio-stream (handshake Twilio)")
    import json, base64
    try:
        async with websockets.connect(
            WS_URL,
            additional_headers={"Origin": BASE_URL},
            open_timeout=10,
        ) as ws:
            print(f"   {PASS} WebSocket conectado")

            # Simular evento "connected" de Twilio
            await ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
            print("   Enviado: connected")

            # Simular evento "start"
            await ws.send(json.dumps({
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "streamSid": "MZ1234567890abcdef",
                    "accountSid": "AC1234567890abcdef",
                    "callSid":    "CA1234567890abcdef",
                    "tracks": ["inbound"],
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                },
                "streamSid": "MZ1234567890abcdef",
            }))
            print("   Enviado: start")

            # Esperar respuesta de Gemini (audio de vuelta) por 8 segundos
            print("   Esperando audio de Gemini (8s)...")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=8)
                data = json.loads(msg)
                if data.get("event") == "media":
                    payload = data.get("media", {}).get("payload", "")
                    print(f"   {PASS} Audio recibido de Gemini — {len(base64.b64decode(payload))} bytes mulaw")
                else:
                    print(f"   INFO evento recibido: {data.get('event')}")
            except asyncio.TimeoutError:
                print(f"   [WARN] No llegó audio en 8s — Gemini puede estar procesando o no hay mic input")

            await ws.send(json.dumps({"event": "stop", "streamSid": "MZ1234567890abcdef"}))
            print("   Enviado: stop — test completo")

    except Exception as e:
        print(f"   {FAIL} Error WebSocket: {e}")


if __name__ == "__main__":
    test_health()
    test_twiml()
    if HAS_WS:
        asyncio.run(test_websocket())
    print("\n" + "=" * 60)
    print("Tests completados.")
