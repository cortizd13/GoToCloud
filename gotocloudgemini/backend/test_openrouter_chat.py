"""
Test OpenRouter — Chat de texto
===============================
Usa el modelo gratuito baidu/cobuddy:free via OpenRouter API.
No requiere dependencias adicionales (usa requests de stdlib o http.client).

Uso:
    python backend/test_openrouter_chat.py
"""

import os
import sys
import json
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: install requests primero: pip install requests")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
MODEL = "baidu/cobuddy:free"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a helpful assistant. Respond in Spanish unless the user asks otherwise. "
    "Be concise and friendly."
)


def chat(user_message: str, history: list[dict] | None = None) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://gotocloud.chat",
        "X-OpenRouter-Title": "GoToCloud Test",
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    response = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    return data["choices"][0]["message"]["content"]


def main() -> None:
    print("=" * 60)  # no uft8 needed for ascii
    safe_print("  OpenRouter Chat — modelo: baidu/cobuddy:free")
    print("  Escribi tu mensaje o 'salir' para terminar.")
    print("=" * 60)
    print()

    history: list[dict] = []
    try:
        while True:
            user_input = input("  Tu: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"salir", "exit", "quit", "adios", "chao"}:
                print("\n  Chau!")
                break

            try:
                reply = chat(user_input, history)
                print()
                safe_print(f"  Asistente: {reply}")
                print()
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": reply})
            except Exception as e:
                print(f"\n  ERROR: {e}\n")
    except KeyboardInterrupt:
        print("\n\n  Sesion interrumpida.")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()