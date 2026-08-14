"""Herramientas (tools) que el asistente puede invocar por su cuenta."""

import requests

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
]


def to_anthropic_format():
    return [
        {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
        for t in TOOLS
    ]


def to_ollama_format():
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


def execute_tool(name: str, args: dict, ctx: dict) -> str:
    if name == "get_weather":
        return get_weather(args["city"])
    if name == "set_reminder":
        return set_reminder(args["text"], args["minutes"], ctx)
    return f"Herramienta desconocida: {name}"
