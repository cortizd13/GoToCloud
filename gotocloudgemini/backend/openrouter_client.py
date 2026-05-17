"""
OpenRouter Client — Camila de GoToCloud
=======================================
Cliente de texto para OpenRouter con soporte de function calling.
Reemplaza al cliente de Gemini para el endpoint /chat/message.

Uso:
    python backend/test_openrouter_chat.py
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

sys.path.insert(0, str(Path(__file__).parent.parent))
from service.gotocloud_voicebot_tool import (
    GOTOCLOUD_TOOLS,
    SYSTEM_PROMPT,
    ejecutar_tool,
)

TEXT_SYSTEM_PROMPT = """\
Eres Camila, asistente de chat de GoToCloud, empresa colombiana lider en soluciones cloud y transformacion digital en Latinoamerica, partner certificado de Microsoft Azure.

## CANAL
Esta es una conversacion por CHAT ESCRITO en el sitio web. Escribe de forma natural y clara. Puedes usar listas o negitas cuando ayude a la claridad, pero no abuses del formato.

## TEMA UNICO
Solo puedes hablar de GoToCloud y sus servicios. Si preguntan por algo fuera de tu especialidad, redirigelos: "Eso esta fuera de mi especialidad, pero si puedo contarte como GoToCloud puede ayudarte con [tema relacionado]."

## SALUDO INICIAL
Saluda brevemente y pregunta en que puedes ayudar. No pidas datos personales de entrada.

## COMO USAR LAS TOOLS
- Usa SIEMPRE las tools para dar informacion. No inventes datos.
- Cuando alguien pregunte por servicios, productos, metricas o contacto, llama la tool correspondiente.
- Convierte el resultado en una respuesta clara y conversacional.

## RECONOCIMIENTO DE CLIENTES EXISTENTES
Cuando el visitante diga su nombre (o cedula), llama INMEDIATAMENTE `buscar_cliente` con ese dato.
- Si `encontrado=true`: saludalo como cliente conocido, usa los datos internamente y NO le pidas info que ya tienes.
- Si `encontrado=false`: es un visitante nuevo.

## SEGURIDAD — DATOS SENSIBLES (REGLA ABSOLUTA)
NUNCA repitas ni muestres en tu respuesta:
- Numeros de cedula o documento de identidad
- Numeros de telefono completos
- Cualquier otro identificador personal sensible

## FLUJO NATURAL
1. Saludo breve
2. Responder preguntas con tools
3. Si hay interes real, ofrecer WhatsApp al +57 317 427 0148
4. Al cerrar, llamar `registrar_resumen_llamada`

## TONO
Cercano, profesional, directo. Sin listas eternas. Respuestas concretas.
"""


def tools_to_openrouter(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convierte tools del formato Gemini al formato OpenAI/OpenRouter."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


class OpenRouterSession:
    """Sesion de chat con OpenRouter — mantiene historial y maneja function calls."""

    def __init__(self, model: str | None = None, system_prompt: str | None = None):
        self.api_key = API_KEY
        self.model = model or MODEL
        self.session_id = str(uuid.uuid4())
        self.ended = False
        self._history: list[dict[str, str]] = []

        system = system_prompt or TEXT_SYSTEM_PROMPT
        self._history.append({"role": "system", "content": system})

        self.db_session_id: str | None = None
        self.db_thread_id: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://gotocloud.chat",
            "X-OpenRouter-Title": "GoToCloud",
        }

    def _call_api(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = {"type": "auto"}

        resp = requests.post(BASE_URL, headers=self.headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def chat(self, user_message: str) -> dict[str, Any]:
        """Envía un mensaje y devuelve {reply, tool_calls, ended}."""
        if self.ended and len(user_message) < 10:
            return {
                "reply": "Gracias por contactar a GoToCloud! Que tengas un excelente dia.",
                "tool_calls": [],
                "ended": True,
            }
        if self.ended:
            self.ended = False

        self._history.append({"role": "user", "content": user_message})

        tools_format = tools_to_openrouter(GOTOCLOUD_TOOLS)

        response = self._call_api(self._history, tools_format)
        message = response["choices"][0]["message"]

        tool_calls: list[str] = []
        reply = ""

        if message.get("tool_calls"):
            self._history.append({"role": "assistant", "content": message.get("content") or ""})
            parts = [{"role": "assistant", "content": message.get("content") or ""}]

            for tc in message["tool_calls"]:
                func = tc["function"]
                name = func["name"]
                tool_calls.append(name)

                if name == "registrar_resumen_llamada":
                    self.ended = True

                try:
                    args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                except (json.JSONDecodeError, TypeError):
                    args = {}

                result = ejecutar_tool(name, args)
                parts.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

            response2 = self._call_api(self._history[:-1] + parts + [{"role": "user", "content": "Continua con la respuesta."}], tools_format)
            message2 = response2["choices"][0]["message"]
            reply = message2.get("content", "")

            self._history.append({"role": "assistant", "content": reply})
        else:
            reply = message.get("content", "")
            self._history.append({"role": "assistant", "content": reply})

        return {
            "reply": reply or "(procesando... preguntame de nuevo)",
            "tool_calls": tool_calls,
            "ended": self.ended,
        }

    async def send_message(self, message: str) -> dict[str, Any]:
        """Version async para usar con FastAPI."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.chat, message)


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))


def main() -> None:
    print("=" * 60)
    safe_print(f"  OpenRouter Chat — modelo: {MODEL}")
    print("  Escribi tu mensaje o 'salir' para terminar.")
    print("=" * 60)
    print()

    session = OpenRouterSession()
    try:
        while True:
            user_input = input("  Tu: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"salir", "exit", "quit", "adios", "chao"}:
                print("\n  Chau!")
                break

            try:
                result = session.chat(user_input)
                print()
                safe_print(f"  Camila: {result['reply']}")
                print()
                if result["ended"]:
                    break
            except Exception as e:
                print(f"\n  ERROR: {e}\n")
    except KeyboardInterrupt:
        print("\n\n  Sesion interrumpida.")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()