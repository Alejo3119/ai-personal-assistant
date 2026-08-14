# Asistente Personal con IA

Un asistente conversacional personal, accesible por Telegram, con memoria persistente entre sesiones. Pensado como proyecto de aprendizaje incremental: cada etapa agrega una capacidad real (proveedores de IA, herramientas/acciones, multi-agente, RAG, MCP) sobre una base que ya funciona de punta a punta.

> **Nota:** proyecto desarrollado con asistencia de IA (Claude, de Anthropic).

## Estado actual: V5 — Tools + imágenes + RAG

- Bot de Telegram como interfaz (sin frontend propio).
- Memoria persistente por chat en SQLite (recuerda la conversación entre mensajes y reinicios del bot).
- Capa de abstracción de proveedor de IA (`llm_client.py`): el mismo bot puede correr contra **Claude (Anthropic)**, **OpenAI (GPT)** o un **modelo Llama local vía Ollama**, sin costo, eligiendo con una variable de entorno. Los tres soportan el mismo loop de tools.
- **Tool calling real** (`tools.py`):
  - `get_weather` — clima actual vía Open-Meteo (sin API key).
  - `set_reminder` — recordatorio con entrega asíncrona real vía `job_queue` de Telegram, sin que el usuario vuelva a escribir.
  - `generate_image` — genera y envía una imagen (Pollinations.ai, sin API key) a partir de una descripción.
  - `search_notes` — RAG sobre archivos propios (`documents/*.md`, `*.txt`): busca por similitud semántica usando embeddings locales de Ollama (`nomic-embed-text`) guardados en SQLite, sin base de datos vectorial externa.

Nota sobre offline: el modelo local (Ollama) corre sin internet, pero Telegram es un servicio en la nube — la interfaz del bot y las tools de clima/imágenes sí necesitan conexión. `search_notes` sí funciona 100% offline si `LLM_PROVIDER=ollama` (embeddings y modelo, ambos locales).

## Arquitectura

```
Telegram (usuario) ──▶ main.py (bot handler)
                              │
                              ├─▶ memory.py ──▶ SQLite (historial por chat_id)
                              │
                              ├─▶ llm_client.py ──▶ Anthropic API  (LLM_PROVIDER=anthropic)
                              │                 ├──▶ OpenAI API    (LLM_PROVIDER=openai)
                              │                 └──▶ Ollama local  (LLM_PROVIDER=ollama)
                              │                         │
                              │                         ▼ (si el modelo pide una tool)
                              └─▶ tools.py ──▶ Open-Meteo (clima) / job_queue (recordatorios) / Pollinations.ai (imagenes)
                                            └──▶ rag.py ──▶ documents/*.md,*.txt + embeddings Ollama ──▶ SQLite
```

### Notas personales (RAG)

Poné tus propios archivos `.md` o `.txt` en la carpeta `documents/` (se crea sola, y está en `.gitignore` — tus notas nunca se suben al repo). Se indexan automáticamente cada vez que arranca el bot.

## Cómo correrlo

1. Crear un bot con [@BotFather](https://t.me/BotFather) en Telegram y copiar el token.
2. Elegir proveedor: API key de [console.anthropic.com](https://console.anthropic.com) o de [platform.openai.com](https://platform.openai.com) (ambas requieren créditos de API, pago único — **distinto** de una suscripción a Claude Pro/ChatGPT Plus) **o** instalar [Ollama](https://ollama.com) y descargar un modelo local (`ollama pull llama3.2`) para no depender de ninguna API paga.
3. Copiar `.env.example` a `.env` y completar `TELEGRAM_BOT_TOKEN`, `LLM_PROVIDER` (`anthropic`, `openai` u `ollama`) y la key/modelo correspondiente.
4. ```bash
   python -m venv .venv
   .venv/Scripts/activate   # en Windows
   pip install -r requirements.txt
   python main.py
   ```
5. Escribirle al bot por Telegram.

## Hoja de ruta / próximas etapas

Este proyecto está pensado para crecer por versiones, cada una funcional antes de pasar a la siguiente:

- **V6 — Multi-agente**: separar responsabilidades (recordatorios, clima, imágenes) en agentes especializados coordinados por un orquestador.
- **V7 — MCP**: exponer las tools como servidor MCP (Model Context Protocol) para que otros clientes MCP puedan usarlas.

## Stack

- Python 3.11
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) / [Ollama](https://ollama.com) (modelo local)
- SQLite (memoria persistente)

## Licencia

MIT
