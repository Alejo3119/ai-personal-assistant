"""
Cliente MCP minimo para validar mcp_server.py de punta a punta: lo lanza como
subproceso (stdio, el transporte estandar de MCP) y llama a sus tools por el
protocolo real, no importando las funciones directo en Python.

Uso: python test_mcp_client.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools expuestas por el servidor:", [t.name for t in tools.tools])

            result = await session.call_tool("get_weather", {"city": "Marinilla"})
            print("get_weather(Marinilla) ->", result.content[0].text)

            result = await session.call_tool("search_notes", {"query": "materia favorita"})
            print("search_notes(materia favorita) ->", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
