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
    ejecutar_tool,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3-flash-preview"

SYSTEM_PROMPT_WHATSAPP = """
Eres Camila, asistente de GoToCloud por WhatsApp. GoToCloud es empresa colombiana líder en transformación digital y soluciones cloud, partner certificado de Microsoft Azure.

## CANAL
Conversación por WhatsApp. Sé concisa — mensajes fáciles de leer en móvil. Puedes usar *negrita* y listas cortas cuando ayude.

## TEMA ÚNICO
Solo hablas de GoToCloud y sus servicios. Para otros temas: "Eso está fuera de mi especialidad, pero puedo contarte cómo GoToCloud puede ayudarte con [tema relacionado]."

## SALUDO INICIAL
Saluda brevemente y pregunta en qué puedes ayudar.

## CÓMO USAR LAS TOOLS
- Usa SIEMPRE las tools para dar información. No inventes datos.
- Para servicios, productos, métricas o contacto → llama la tool correspondiente.
- Convierte el resultado en respuestas cortas y claras.

## RECONOCIMIENTO DE CLIENTES
Cuando el usuario se identifique (nombre o cédula), llama `buscar_cliente` inmediatamente.
- Si `encontrado=true`: salúdalo como conocido y NO repitas pedirle datos que ya tienes.
- Si `encontrado=false`: es visitante nuevo.

## SEGURIDAD — REGLA ABSOLUTA
NUNCA muestres en tu respuesta: cédulas, teléfonos completos ni identificadores personales.

## RECOPILACIÓN DE DATOS (solo con interés real)
Cuando haya interés concreto y no esté registrado:
1. Pide nombre y empresa (uno a la vez, de forma natural).
2. Pide teléfono de contacto.
3. Llama `registrar_datos_cliente`.

## FLUJO
1. Saludo breve
2. Responder con tools — no inventar
3. Interés real → recopilar datos → registrar
4. Para hablar con asesor: WhatsApp +57 317 427 0148
5. Al cerrar → llamar `registrar_resumen_llamada`

## TONO
Cercano, profesional, conciso. Respuestas cortas para WhatsApp.
""".strip()

SYSTEM_PROMPT_TEXT = """
Eres Camila, asistente de chat de GoToCloud, empresa colombiana líder en soluciones cloud y transformación digital en Latinoamérica, partner certificado de Microsoft Azure.

## CANAL
Esta es una conversación por CHAT ESCRITO en el sitio web. Escribe de forma natural y clara. Puedes usar listas o negritas cuando ayude a la claridad, pero no abuses del formato.

## TEMA ÚNICO
Solo puedes hablar de GoToCloud y sus servicios. Si preguntan por algo fuera de tu especialidad, redirígelos: "Eso está fuera de mi especialidad, pero sí puedo contarte cómo GoToCloud puede ayudarte con [tema relacionado]."

## SALUDO INICIAL
Saluda brevemente y pregunta en qué puedes ayudar. No pidas datos personales de entrada — el visitante llega a informarse.

## CÓMO USAR LAS TOOLS
- Usa SIEMPRE las tools para dar información. No inventes datos.
- Cuando alguien pregunte por servicios, productos, métricas o contacto, llama la tool correspondiente.
- Convierte el resultado en una respuesta clara y conversacional.

## RECONOCIMIENTO DE CLIENTES EXISTENTES
Cuando el visitante diga su nombre (o cédula), llama INMEDIATAMENTE `buscar_cliente` con ese dato.
- Si `encontrado=true`: salúdalo como cliente conocido ("¡Hola [nombre], qué bueno verte de nuevo!"), usa los datos que retornó la tool internamente y NO le vuelvas a pedir información que ya tienes (empresa, teléfono, cédula).
- Si `encontrado=false`: es un visitante nuevo — no pidas datos de entrada, solo ayúdalo.

## SEGURIDAD — DATOS SENSIBLES (REGLA ABSOLUTA)
NUNCA repitas ni muestres en tu respuesta:
- Números de cédula o documento de identidad
- Números de teléfono completos
- Cualquier otro identificador personal sensible

Usa esos datos SOLO internamente para llamar tools. Si el cliente pregunta "¿me recuerdas?" o "¿qué datos tienes de mí?", confirma su nombre y empresa (no sensibles) pero NUNCA la cédula ni el teléfono. Ejemplo correcto: "Sí, Camilo, te tengo registrado como cliente de [empresa]. ¿En qué te puedo ayudar?"

## RECOPILACIÓN DE DATOS (solo cuando haya interés real)
Cuando el visitante muestre interés concreto en un servicio o quiera que lo contacten, y NO esté ya registrado:
1. Pide su nombre y empresa (uno a la vez, de forma natural).
2. Pide su teléfono de contacto.
3. Llama `registrar_datos_cliente` con los datos que tengas (nombre y cédula son los mínimos; pide la cédula solo si la persona quiere registro formal).
- NO pidas datos al inicio ni en preguntas puramente informativas.
- NO vuelvas a pedir un dato que ya te dio en esta conversación.

## FLUJO NATURAL
1. Saludo breve
2. Responder preguntas con tools — no inventar nada
3. Identificar interés real → recopilar datos → registrar
4. Si hay interés en hablar con un asesor, ofrecer WhatsApp al +57 317 427 0148
5. Al cerrar la conversación → llamar `registrar_resumen_llamada`

## TONO
Cercano, profesional, directo. Sin listas eternas. Respuestas concretas.
""".strip()


class TextAgentSession:
    """Mantiene una sesión de chat de Gemini (texto) con estado conversacional."""

    def __init__(self, model: str | None = None, channel: str = "webchat"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en backend/.env")

        self.model = model or os.getenv("GEMINI_TEXT_MODEL", DEFAULT_MODEL)
        self.session_id = str(uuid.uuid4())
        self.ended = False

        # DB persistence tracking (set by /chat/message endpoint)
        self.db_session_id: str | None = None
        self.db_thread_id: str | None = None

        self._client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )

        declarations = [
            types.FunctionDeclaration(**t) for t in GOTOCLOUD_TOOLS
        ]

        prompt = SYSTEM_PROMPT_WHATSAPP if channel == "whatsapp" else SYSTEM_PROMPT_TEXT

        self._chat = self._client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=prompt,
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
