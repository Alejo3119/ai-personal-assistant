"""
V6: arquitectura multi-agente.

Un orquestador recibe el mensaje del usuario y decide si lo puede responder el
mismo (charla general) o si conviene delegarlo a un agente especializado, cada
uno con su propio system prompt enfocado y acceso SOLO a su propia herramienta.
Reusa el mismo loop de tool-calling de llm_client.py, generalizado para aceptar
un system prompt / lista de tools / executor distintos por agente.
"""

import llm_client
import tools

FINAL_ANSWER_RULE = (
    "Tu respuesta final tiene que decir el resultado real en lenguaje natural (ej. "
    "'Hace 14 grados en...' o 'Listo, te lo recuerdo en 10 minutos'), como si se lo "
    "dijeras directo a la persona. Nunca describas que hiciste, ni digas cosas como "
    "'la herramienta me devuelve...' o 'no tengo mas informacion' — el dato que te "
    "dio la herramienta ES la informacion completa que necesitas para responder."
)

AGENTS = {
    "clima": {
        "description": "Consulta el clima actual de una ciudad.",
        "system_prompt": (
            "Llama a get_weather con la ciudad pedida. Cuando te devuelva el resultado, "
            "respondelo tal cual, en una frase. Ejemplo: si get_weather devuelve 'En "
            "Bogota hace 15 grados C, viento 5 km/h.', tu respuesta final es exactamente "
            "esa frase (podes agregar una palabra amable antes o despues, nada mas). Vos "
            "SI tenes acceso a datos en vivo porque get_weather te los acaba de dar: "
            "nunca digas que no tenes acceso a informacion en vivo."
        ),
        "tool_names": ["get_weather"],
    },
    "recordatorios": {
        "description": "Programa recordatorios para el usuario.",
        "system_prompt": (
            "Sos un agente especializado UNICAMENTE en programar recordatorios. Usa "
            "la herramienta set_reminder. " + llm_client.TOOL_RESULT_RULES + " " + FINAL_ANSWER_RULE
        ),
        "tool_names": ["set_reminder"],
    },
    "imagenes": {
        "description": "Genera y envia una imagen a partir de una descripcion.",
        "system_prompt": (
            "Sos un agente especializado UNICAMENTE en generar imagenes. Usa la "
            "herramienta generate_image. La imagen se envia directo al usuario, vos "
            "no la ves, no intentes describirla, solo confirma que la enviaste."
        ),
        "tool_names": ["generate_image"],
    },
    "notas": {
        "description": "Busca informacion en las notas/documentos personales del usuario.",
        "system_prompt": (
            "Sos un agente especializado UNICAMENTE en buscar en las notas del "
            "usuario. Usa la herramienta search_notes. " + llm_client.TOOL_RESULT_RULES + " " + FINAL_ANSWER_RULE
        ),
        "tool_names": ["search_notes"],
    },
}

ORCHESTRATOR_SYSTEM_PROMPT = (
    "Sos el orquestador de un equipo de agentes especializados. Cuando el pedido del "
    "usuario sea sobre clima, recordatorios, imagenes o sus notas personales, NO lo "
    "respondas vos: delega con la herramienta 'delegate', indicando el agente correcto "
    "y el pedido tal cual lo escribio el usuario. Si es charla general que no encaja "
    "en ningun agente especializado, respondele vos directamente, breve y en espanol.\n\n"
    "Agentes disponibles:\n"
    + "\n".join(f"- {name}: {info['description']}" for name, info in AGENTS.items())
    + "\n\nEl resultado que te devuelve 'delegate' es la respuesta YA elaborada por el "
    "agente especialista: repetisela al usuario tal cual (podes acomodar el tono), no "
    "inventes otros datos ni la reemplaces por tu propio conocimiento. " + llm_client.TOOL_RESULT_RULES
)

DELEGATE_TOOL = [
    {
        "name": "delegate",
        "description": "Delega el pedido del usuario a un agente especializado.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": list(AGENTS.keys()),
                    "description": "Agente especializado al que delegar",
                },
                "request": {
                    "type": "string",
                    "description": "El pedido del usuario, tal cual, para que el agente lo resuelva",
                },
            },
            "required": ["agent", "request"],
        },
    }
]


def run_agent(agent_key: str, request: str, tool_ctx: dict) -> str:
    agent = AGENTS[agent_key]
    agent_tool_defs = [t for t in tools.TOOLS if t["name"] in agent["tool_names"]]
    return llm_client.generate_response(
        [{"role": "user", "content": request}],
        tool_ctx=tool_ctx,
        system_prompt=agent["system_prompt"],
        tool_defs=agent_tool_defs,
    )


def _orchestrator_executor(name: str, args: dict, tool_ctx: dict) -> str:
    if name == "delegate":
        return run_agent(args["agent"], args["request"], tool_ctx)
    return tools.execute_tool(name, args, tool_ctx)


def handle(history: list[dict], tool_ctx: dict) -> str:
    return llm_client.generate_response(
        history,
        tool_ctx=tool_ctx,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tool_defs=DELEGATE_TOOL,
        executor=_orchestrator_executor,
    )
