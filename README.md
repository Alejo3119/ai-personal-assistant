# Asistente Personal con IA

Un asistente conversacional personal, accesible por Telegram, con memoria persistente entre sesiones. Pensado como proyecto de aprendizaje incremental: cada etapa agrega una capacidad real (proveedores de IA, herramientas/acciones, multi-agente, RAG, MCP) sobre una base que ya funciona de punta a punta.

> **Nota:** proyecto desarrollado con asistencia de IA (Claude, de Anthropic).

## Estado actual: V7 — Servidor MCP

- Bot de Telegram como interfaz (sin frontend propio).
- Memoria persistente por chat en SQLite (recuerda la conversación entre mensajes y reinicios del bot).
- Capa de abstracción de proveedor de IA (`llm_client.py`): el mismo bot puede correr contra **Claude (Anthropic)**, **OpenAI (GPT)** o un **modelo Llama local vía Ollama**, sin costo, eligiendo con una variable de entorno. Los tres soportan el mismo loop de tools.
- **Tool calling real** (`tools.py`):
  - `get_weather` — clima actual vía Open-Meteo (sin API key).
  - `set_reminder` — recordatorio con entrega asíncrona real vía `job_queue` de Telegram, sin que el usuario vuelva a escribir.
  - `generate_image` — genera y envía una imagen (Pollinations.ai, sin API key) a partir de una descripción.
  - `search_notes` — RAG sobre archivos propios (`documents/*.md`, `*.txt`): busca por similitud semántica usando embeddings locales de Ollama (`nomic-embed-text`) guardados en SQLite, sin base de datos vectorial externa.
- **Arquitectura multi-agente** (`agents.py`): un orquestador recibe cada mensaje y decide si lo responde directamente (charla general) o lo delega a un agente especializado (clima, recordatorios, imágenes, notas), cada uno con su propio system prompt enfocado y acceso *solo* a su propia tool. Reusa el mismo loop de tool-calling de `llm_client.py`, generalizado para aceptar system prompt / tools / executor por agente.
- **Servidor MCP** (`mcp_server.py`): expone `get_weather`, `search_notes` y `generate_image` como un servidor [MCP](https://modelcontextprotocol.io) real (protocolo estándar, transporte stdio), para que cualquier cliente MCP (Claude Desktop, Claude Code, etc.) las use directamente — no solo el bot de Telegram. `set_reminder` no se expone acá porque depende del `job_queue` de un chat de Telegram especifico, que no existe fuera de ese contexto; `generate_image` devuelve la URL de la imagen en vez de enviarla, porque acá no hay chat al que mandarla.

Nota sobre offline: el modelo local (Ollama) corre sin internet, pero Telegram es un servicio en la nube — la interfaz del bot y las tools de clima/imágenes sí necesitan conexión. `search_notes` sí funciona 100% offline si `LLM_PROVIDER=ollama` (embeddings y modelo, ambos locales).

## Arquitectura

```
Telegram (usuario) ──▶ main.py (bot handler)
                              │
                              ├─▶ memory.py ──▶ SQLite (historial por chat_id)
                              │
                              └─▶ agents.py (orquestador)
                                        │
                                        ├─▶ responde directo (charla general)
                                        │
                                        └─▶ delegate ──▶ agente especialista (clima/recordatorios/imagenes/notas)
                                                              │        (system prompt + tools propias)
                                                              ▼
                                        llm_client.py ──▶ Anthropic API  (LLM_PROVIDER=anthropic)
                                                       ├──▶ OpenAI API    (LLM_PROVIDER=openai)
                                                       └──▶ Ollama local  (LLM_PROVIDER=ollama)
                                                              │
                                                              ▼ (si el agente pide su tool)
                                        tools.py ──▶ Open-Meteo / job_queue / Pollinations.ai / rag.py
```

### Hallazgo de V6: confiabilidad de las cadenas multi-agente con modelos locales chicos

Probando V6 en vivo con `llama3.1:8b` (local, vía Ollama) apareció algo interesante: la arquitectura funciona (el orquestador delega bien, el agente especialista llama a su tool correctamente, el dato real llega), pero el **relevo final** — el paso donde un agente tiene que tomar el resultado de una tool y convertirlo en una respuesta en lenguaje natural — falla de forma intermitente, y el fallo se puede mover a *cualquier* eslabón de la cadena (a veces el especialista, a veces el propio orquestador), incluso reforzando el prompt con reglas explícitas y ejemplos concretos.

La causa más probable: modelos chicos como este tienen un sesgo de entrenamiento muy fuerte hacia responder "no tengo acceso a datos en tiempo real" ante preguntas de clima/hora/etc., y ese reflejo a veces gana incluso con el dato correcto ya en el contexto. Cada salto adicional en una cadena multi-agente es una nueva oportunidad para que ese reflejo se dispare — a diferencia del flujo de un solo agente (V1-V5), donde el mismo modelo respondió bien de forma consistente.

Conclusión práctica: la arquitectura multi-agente (orquestador + especialistas) está bien diseñada y funciona; la confiabilidad del paso final depende del modelo usado. Queda pendiente confirmar si un modelo más grande (Claude, GPT-4o) elimina este problema — es la hipótesis más probable dado que ninguno de estos fallos apareció durante las pruebas de V1-V5 con el mismo modelo en un solo salto.

### Notas personales (RAG)

Poné tus propios archivos `.md` o `.txt` en la carpeta `documents/` (se crea sola, y está en `.gitignore` — tus notas nunca se suben al repo). Se indexan automáticamente cada vez que arranca el bot.

## Servidor MCP

Probarlo standalone (lanza el servidor como subproceso y llama a sus tools por el protocolo real):

```bash
python test_mcp_client.py
```

Para usarlo desde Claude Desktop, agregar en su config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "asistente-personal": {
      "command": "C:\\ruta\\a\\este\\repo\\.venv\\Scripts\\python.exe",
      "args": ["C:\\ruta\\a\\este\\repo\\mcp_server.py"]
    }
  }
}
```

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

## Stack

- Python 3.11
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) / [OpenAI SDK](https://github.com/openai/openai-python) / [Ollama](https://ollama.com) (modelo local)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- SQLite (memoria persistente + índice RAG)

## Licencia

MIT
