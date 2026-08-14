"""Herramientas (tools) que el asistente puede invocar por su cuenta."""

import urllib.parse

import requests

import rag

TOOLS = [
    {
        "name": "get_weather",
        "description": "Obtiene el clima actual de una ciudad.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Nombre de la ciudad"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Programa un recordatorio para dentro de N minutos. El asistente le va a escribir al usuario cuando llegue el momento.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Que hay que recordar"},
                "minutes": {"type": "number", "description": "En cuantos minutos avisar"},
            },
            "required": ["text", "minutes"],
        },
    },
    {
        "name": "search_notes",
        "description": "Busca en las notas/documentos personales del usuario informacion relevante a una consulta.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Que buscar en las notas del usuario"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_image",
        "description": "Genera y envia una imagen a partir de una descripcion en texto.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Descripcion de la imagen a generar, preferiblemente en ingles para mejor calidad",
                },
            },
            "required": ["prompt"],
        },
    },
]


def to_anthropic_format():
    return [
        {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
        for t in TOOLS
    ]


def to_openai_format():
    """Formato estandar de function calling que usan tanto OpenAI como Ollama."""
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in TOOLS
    ]


def get_weather(city: str) -> str:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "es"},
        timeout=15,
    ).json()
    results = geo.get("results")
    if not results:
        return f"No encontre la ciudad '{city}'."

    place = results[0]
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": place["latitude"], "longitude": place["longitude"], "current_weather": "true"},
        timeout=15,
    ).json()
    current = weather["current_weather"]
    return f"En {place['name']} hace {current['temperature']} grados C, viento {current['windspeed']} km/h."


def set_reminder(text: str, minutes: float, ctx: dict) -> str:
    ctx["schedule_reminder"](text, minutes)
    return f"Recordatorio programado para dentro de {minutes} minutos: {text}"


def search_notes(query: str) -> str:
    results = rag.search(query)
    if not results:
        return "No se encontraron notas relevantes (o todavia no hay documentos indexados)."
    return "\n\n".join(f"[{source}]: {text}" for source, text in results)


def generate_image(prompt: str, ctx: dict) -> str:
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    ctx["send_image"](resp.content, prompt)
    return f"Imagen generada y enviada al usuario: {prompt}"


def execute_tool(name: str, args: dict, ctx: dict) -> str:
    if name == "get_weather":
        return get_weather(args["city"])
    if name == "set_reminder":
        return set_reminder(args["text"], args["minutes"], ctx)
    if name == "search_notes":
        return search_notes(args["query"])
    if name == "generate_image":
        return generate_image(args["prompt"], ctx)
    return f"Herramienta desconocida: {name}"
