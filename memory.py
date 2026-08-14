"""Memoria persistente del asistente: guarda el historial de conversacion por chat en SQLite."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "assistant.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.commit()
    con.close()


def save_message(chat_id: int, role: str, content: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content),
    )
    con.commit()
    con.close()


def get_history(chat_id: int, limit: int = 20):
    """Devuelve los ultimos `limit` mensajes del chat, en orden cronologico,
    listos para pasarle a la API de Anthropic como lista de {role, content}."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (chat_id, limit),
    ).fetchall()
    con.close()
    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]
