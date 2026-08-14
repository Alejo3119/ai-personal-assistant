# Asistente Personal con IA

Un asistente conversacional personal, accesible por Telegram, con memoria persistente entre sesiones. Pensado como proyecto de aprendizaje incremental: cada etapa agrega una capacidad real (proveedores de IA, herramientas/acciones, multi-agente, RAG, MCP) sobre una base que ya funciona de punta a punta.

## Estado actual: V1 — Asistente base

- Bot de Telegram como interfaz (sin frontend propio).
- Memoria persistente por chat en SQLite (recuerda la conversación entre mensajes y reinicios del bot).
- Capa de abstracción de proveedor de IA (`llm_client.py`): el mismo bot puede correr contra **Claude (Anthropic API)** o contra un **modelo Llama local vía Ollama**, sin costo, eligiendo con una variable de entorno.

## Arquitectura

```
Telegram (usuario) ──▶ main.py (bot handler)
                              │
                              ├─▶ memory.py ──▶ SQLite (historial por chat_id)
                              │
                              └─▶ llm_client.py ──▶ Anthropic API  (LLM_PROVIDER=anthropic)
                                                └──▶ Ollama local  (LLM_PROVIDER=ollama)
```

## Cómo correrlo

1. Crear un bot con [@BotFather](https://t.me/BotFather) en Telegram y copiar el token.
2. Conseguir una API key en [console.anthropic.com](https://console.anthropic.com) (requiere créditos de API — **distinto** de una suscripción a Claude Pro/claude.ai) **o** instalar [Ollama](https://ollama.com) y descargar un modelo local (`ollama pull llama3.2`) para no depender de ninguna API paga.
3. Copiar `.env.example` a `.env` y completar `TELEGRAM_BOT_TOKEN`, `LLM_PROVIDER` (`anthropic` u `ollama`) y la key/modelo correspondiente.
4. ```bash
   python -m venv .venv
   .venv/Scripts/activate   # en Windows
   pip install -r requirements.txt
   python main.py
   ```
5. Escribirle al bot por Telegram.

## Hoja de ruta / próximas etapas

Este proyecto está pensado para crecer por versiones, cada una funcional antes de pasar a la siguiente:

- **V2 — Tools**: function calling real (recordatorios, clima, y posiblemente control de PC reutilizando ideas de [wol-remote-pc-control](https://github.com/Alejo3119/wol-remote-pc-control)).
- **V3 — Multi-proveedor ampliado**: sumar OpenAI además de Anthropic/Ollama, seleccionable en runtime.
- **V4 — Generación de imágenes**: como una tool más que el agente puede invocar.
- **V5 — RAG**: consultar documentos/notas propias como fuente de contexto.
- **V6 — Multi-agente**: separar responsabilidades (recordatorios, clima, imágenes) en agentes especializados coordinados por un orquestador.
- **V7 — MCP**: exponer las tools como servidor MCP (Model Context Protocol) para que otros clientes MCP puedan usarlas.

## Stack

- Python 3.11
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) / [Ollama](https://ollama.com) (modelo local)
- SQLite (memoria persistente)

## Licencia

MIT
