"""
Asistente personal con IA — V1
Bot de Telegram conectado a Claude (Anthropic), con memoria persistente en SQLite.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()  # debe correr antes de importar llm_client, que lee env vars al importarse

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

import memory
from llm_client import generate_response, LLM_PROVIDER

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    logger.info("chat=%s mensaje recibido: %s", chat_id, user_text)

    memory.save_message(chat_id, "user", user_text)
    history = memory.get_history(chat_id)

    try:
        reply_text = generate_response(history)
    except Exception:
        logger.exception("Fallo llamando al proveedor de IA (%s)", LLM_PROVIDER)
        reply_text = "Tuve un problema para pensar la respuesta. Intenta de nuevo."

    memory.save_message(chat_id, "assistant", reply_text)
    await update.message.reply_text(reply_text)


def main():
    memory.init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot iniciado, esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()
