"""
Text Agent — Camila de GoToCloud
================================
Agente conversacional por TEXTO que usa las MISMAS tools y sistema
del voicebot (Gemini Live), pero con la API Generate estándar.

Uso:
    python backend/text_agent.py

Usa GEMINI_API_KEY del .env. Modelo configurable via GEMINI_TEXT_MODEL.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

# ── Importar las tools del voicebot ──────────────────────────────────
# Compatibilidad: voice_to_voice.py usa sys.path, main.py usa package-relative
sys.path.insert(0, str(Path(__file__).parent.parent))
from service.gotocloud_voicebot_tool import (
    GOTOCLOUD_TOOLS,
    SYSTEM_PROMPT,
    ejecutar_tool,
)

# ── Configuración ─────────────────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL = os.getenv("GEMINI_TEXT_MODEL", DEFAULT_MODEL)

# Adaptación mínima del system prompt para canal texto
TEXT_ADAPTATION = (
    "[ADAPTACIÓN PARA TEXTO/CHAT]\n"
    "Esta conversación es por TEXTO ESCRITO, no por voz. "
    "Escribí respuestas completas e informativas — podés usar listas, "
    "negritas y formato cuando ayude a la claridad. "
    "El resto de las instrucciones (tools, flujo, conocimiento) sigue igual.\n\n"
)

SYSTEM_PROMPT_TEXT = TEXT_ADAPTATION + SYSTEM_PROMPT


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no está configurada en backend/.env")
        sys.exit(1)

    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )

    # ── Preparar herramientas ────────────────────────────────────────
    declarations = [types.FunctionDeclaration(**t) for t in GOTOCLOUD_TOOLS]

    # ── Crear sesión de chat ─────────────────────────────────────────
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT_TEXT,
            tools=[types.Tool(function_declarations=declarations)],
            temperature=0.7,
            # Seguridad: prevenir jailbreak / salidas no deseadas
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ],
        ),
    )

    print("=" * 62)
    print("  Camila — Agente de GoToCloud (texto)")
    print(f"  Modelo: {MODEL}")
    print(f"  Tools:  {len(GOTOCLOUD_TOOLS)} cargadas")
    print("=" * 62)
    print("  Escribi tu mensaje o 'salir' para terminar.\n")

    try:
        call_ended = False  # True cuando se llamó registrar_resumen_llamada

        while True:
            user_input = input("  Tú: ").strip()

            # ── Post-cierre: input trivial → salir ─────────────────
            if call_ended:
                if not user_input or len(user_input) < 10:
                    print("\n  Camila: Gracias por contactar a GoToCloud! Que tengas un excelente dia.\n")
                    break
                # Escribió algo sustancial → reactivar
                call_ended = False

            if not user_input:
                continue
            if user_input.lower() in {"salir", "exit", "quit", "chao", "adiós"}:
                print("\n  Camila: Gracias por contactar a GoToCloud! Que tengas un excelente dia.")
                break

            # ── Enviar mensaje del usuario ───────────────────────────
            response = chat.send_message(user_input)

            # ── Loop de tool calls (Gemini pide ejecutar tools) ──────
            while response.function_calls:
                parts = []
                for fc in response.function_calls:
                    if fc.name == "registrar_resumen_llamada":
                        call_ended = True
                    args = dict(fc.args or {})
                    result = ejecutar_tool(fc.name, args)
                    parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                # Enviar TODOS los resultados juntos (como lista de Part, no Content)
                response = chat.send_message(parts)

            # ── Mostrar respuesta final ──────────────────────────────
            if response.text:
                print(f"\n  Camila: {response.text}\n")
            else:
                print("\n  Camila: (procesando... preguntame de nuevo)\n")

    except KeyboardInterrupt:
        print("\n\n  Sesión interrumpida. ¡Hasta luego!")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
