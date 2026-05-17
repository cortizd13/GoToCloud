"""
Text Agent Client — sesión de texto reutilizable para endpoints HTTP.
Envuelve la sesión de chat de Gemini con tools, gestión de sesión y
post-cierre (conversación terminada tras registrar_resumen_llamada).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

sys.path.insert(0, str(Path(__file__).parent.parent))
from service.gotocloud_voicebot_tool import (
    GOTOCLOUD_TOOLS,
    SYSTEM_PROMPT,
    ejecutar_tool,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

TEXT_ADAPTATION = (
    "[ADAPTACIÓN PARA TEXTO/CHAT]\n"
    "Esta conversación es por TEXTO ESCRITO, no por voz. "
    "Escribí respuestas completas e informativas — podés usar listas, "
    "negritas y formato cuando ayude a la claridad. "
    "El resto de las instrucciones (tools, flujo, conocimiento) sigue igual.\n\n"
)

SYSTEM_PROMPT_TEXT = TEXT_ADAPTATION + SYSTEM_PROMPT


class TextAgentSession:
    """Mantiene una sesión de chat de Gemini (texto) con estado conversacional."""

    def __init__(self, model: str | None = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en backend/.env")

        self.model = model or os.getenv("GEMINI_TEXT_MODEL", DEFAULT_MODEL)
        self.session_id = str(uuid.uuid4())
        self.ended = False

        self._client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )

        declarations = [
            types.FunctionDeclaration(**t) for t in GOTOCLOUD_TOOLS
        ]

        self._chat = self._client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_TEXT,
                tools=[types.Tool(function_declarations=declarations)],
                temperature=0.7,
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

    async def send_message(self, message: str) -> dict[str, Any]:
        """Envía un mensaje a la sesión y devuelve {reply, tool_calls, ended}."""
        loop = asyncio.get_running_loop()

        # Post-cierre: input trivial (< 10 chars) → despedida automática
        if self.ended:
            if not message or len(message) < 10:
                return {
                    "reply": (
                        "Gracias por contactar a GoToCloud! "
                        "Que tengas un excelente dia."
                    ),
                    "tool_calls": [],
                    "ended": True,
                }
            # Input sustancial → reactivar conversación
            self.ended = False

        response = await loop.run_in_executor(
            None, self._chat.send_message, message
        )

        tool_calls: list[str] = []

        while response.function_calls:
            parts = []
            for fc in response.function_calls:
                tool_calls.append(fc.name)
                if fc.name == "registrar_resumen_llamada":
                    self.ended = True
                args = dict(fc.args or {})
                try:
                    result = ejecutar_tool(fc.name, args)
                except Exception as exc:
                    logger.error(f"Tool {fc.name} error: {exc}")
                    result = {"error": str(exc)}
                parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            response = await loop.run_in_executor(
                None, self._chat.send_message, parts
            )

        reply = response.text or "(procesando... preguntame de nuevo)"

        return {
            "reply": reply,
            "tool_calls": tool_calls,
            "ended": self.ended,
        }
