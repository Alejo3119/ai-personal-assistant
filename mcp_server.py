"""
V7: servidor MCP (Model Context Protocol) que expone las tools del asistente
para que cualquier cliente MCP (Claude Desktop, Claude Code, etc.) las use
directamente, sin pasar por Telegram.

set_reminder no se expone aca: depende del job_queue del chat de Telegram,
que no existe en un cliente MCP generico. generate_image devuelve la URL de
la imagen en vez de enviarla (aca no hay un chat al que mandarsela).
"""

import urllib.parse

from mcp.server.mcpserver import MCPServer

import tools as bot_tools

mcp = MCPServer("asistente-personal")


@mcp.tool()
def get_weather(city: str) -> str:
    """Obtiene el clima actual de una ciudad."""
    return bot_tools.get_weather(city)


@mcp.tool()
def search_notes(query: str) -> str:
    """Busca en las notas/documentos personales del usuario (carpeta documents/)."""
    return bot_tools.search_notes(query)


@mcp.tool()
def generate_image(prompt: str) -> str:
    """Genera una imagen a partir de una descripcion y devuelve la URL de la imagen."""
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"


if __name__ == "__main__":
    mcp.run()
