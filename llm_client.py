"""
Capa de abstraccion sobre el proveedor de IA.
Permite cambiar entre Anthropic (API paga) y Ollama (modelo local, gratis)
sin tocar el resto del bot. Se elige con la variable de entorno LLM_PROVIDER.
"""

import os

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()
SYSTEM_PROMPT = (
    "Sos un asistente personal util y directo. Respondes en espanol, "
    "de forma breve y clara, como si fueras un ayudante de confianza."
)


def _generate_anthropic(history: list[dict]) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    return response.content[0].text


def _generate_ollama(history: list[dict]) -> str:
    import requests

    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def generate_response(history: list[dict]) -> str:
    if LLM_PROVIDER == "ollama":
        return _generate_ollama(history)
    return _generate_anthropic(history)
