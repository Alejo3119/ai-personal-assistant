"""
Capa de abstraccion sobre el proveedor de IA, con soporte de tools (function calling).
Permite cambiar entre Anthropic (API paga) y Ollama (modelo local, gratis)
sin tocar el resto del bot. Se elige con la variable de entorno LLM_PROVIDER.
"""

import json
import logging
import os

import requests

import tools

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()
MAX_TOOL_ITERATIONS = 5

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Sos un asistente personal util y directo. Respondes en espanol, "
    "de forma breve y clara, como si fueras un ayudante de confianza. "
    "Cuando sea util, usa las herramientas disponibles (por ejemplo para "
    "consultar el clima o programar un recordatorio) en vez de inventar la respuesta. "
    "Cuando una herramienta te devuelva un resultado, usa EXACTAMENTE esos datos y no "
    "agregues detalles que no esten ahi (por ejemplo, no inventes si esta soleado o "
    "nublado si la herramienta no lo dice). Nunca menciones tu fecha de corte de "
    "entrenamiento ni digas que tu informacion podria estar desactualizada cuando "
    "acabas de usar una herramienta con datos en vivo. Si el usuario pide una imagen, "
    "usa la herramienta generate_image: la imagen se le envia directamente al usuario, "
    "vos no la ves, asi que no intentes describirla, solo confirma que la enviaste. "
    "Si el usuario pregunta algo que podria estar en sus notas o documentos personales "
    "(cosas sobre si mismo, sus proyectos, datos que no sabrias de otra forma), usa la "
    "herramienta search_notes antes de responder que no sabes. Si search_notes devuelve "
    "texto con informacion (no el mensaje de 'no se encontraron notas'), ESE texto es la "
    "respuesta correcta: usalo directamente para responder, no digas que no tenes la "
    "informacion cuando la herramienta te la acaba de dar."
)


def _run_anthropic(history: list[dict], tool_ctx: dict | None) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = list(history)

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools.to_anthropic_format(),
            messages=messages,
        )

        logger.info("anthropic stop_reason=%s", response.stop_reason)
        if response.stop_reason != "tool_use":
            return "".join(block.text for block in response.content if block.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info("tool_call name=%s input=%s", block.name, block.input)
                result = tools.execute_tool(block.name, block.input, tool_ctx or {})
                logger.info("tool_result=%s", result)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        messages.append({"role": "user", "content": tool_results})

    return "No pude completar la accion, intenta de nuevo."


def _run_ollama(history: list[dict], tool_ctx: dict | None) -> str:
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "tools": tools.to_openai_format(), "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        message = resp.json()["message"]

        tool_calls = message.get("tool_calls")
        logger.info("ollama tool_calls=%s content=%r", tool_calls, message.get("content"))
        if not tool_calls:
            return message.get("content", "")

        messages.append(message)
        for call in tool_calls:
            fn = call["function"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            logger.info("tool_call name=%s args=%s", fn["name"], args)
            result = tools.execute_tool(fn["name"], args, tool_ctx or {})
            logger.info("tool_result=%s", result)
            messages.append({"role": "tool", "content": result})

    return "No pude completar la accion, intenta de nuevo."


def _run_openai(history: list[dict], tool_ctx: dict | None) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools.to_openai_format(),
        )
        message = response.choices[0].message
        logger.info("openai tool_calls=%s content=%r", message.tool_calls, message.content)

        if not message.tool_calls:
            return message.content or ""

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            }
        )
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            logger.info("tool_call name=%s args=%s", tc.function.name, args)
            result = tools.execute_tool(tc.function.name, args, tool_ctx or {})
            logger.info("tool_result=%s", result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "No pude completar la accion, intenta de nuevo."


def generate_response(history: list[dict], tool_ctx: dict | None = None) -> str:
    if LLM_PROVIDER == "ollama":
        return _run_ollama(history, tool_ctx)
    if LLM_PROVIDER == "openai":
        return _run_openai(history, tool_ctx)
    return _run_anthropic(history, tool_ctx)
