"""
RAG (Retrieval-Augmented Generation): indexa archivos de texto propios (carpeta documents/)
y permite buscar los fragmentos mas relevantes para una consulta por similitud semantica.
Usa embeddings locales de Ollama, sin costo y sin depender de una base de datos vectorial externa.
"""

import sqlite3
from pathlib import Path

import numpy as np
import requests

DB_PATH = Path(__file__).parent / "assistant.db"
DOCS_DIR = Path(__file__).parent / "documents"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _embed(text: str) -> np.ndarray:
    resp = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    return np.array(resp.json()["embeddings"][0], dtype=np.float32)


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def _init_table(con: sqlite3.Connection):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
        """
    )


def build_index() -> int:
    """Reconstruye el indice desde cero con los archivos .txt/.md de documents/. Devuelve cuantos fragmentos indexo."""
    DOCS_DIR.mkdir(exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    _init_table(con)
    con.execute("DELETE FROM rag_chunks")

    indexed = 0
    for path in DOCS_DIR.glob("**/*"):
        if not path.is_file() or path.suffix.lower() not in (".txt", ".md"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for chunk in _chunk_text(text):
            embedding = _embed(chunk)
            con.execute(
                "INSERT INTO rag_chunks (source, text, embedding) VALUES (?, ?, ?)",
                (path.name, chunk, embedding.tobytes()),
            )
            indexed += 1

    con.commit()
    con.close()
    return indexed


def search(query: str, k: int = 3) -> list[tuple[str, str]]:
    con = sqlite3.connect(DB_PATH)
    _init_table(con)
    rows = con.execute("SELECT source, text, embedding FROM rag_chunks").fetchall()
    con.close()

    if not rows:
        return []

    query_vec = _embed(query)
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)

    scored = []
    for source, text, emb_bytes in rows:
        vec = np.frombuffer(emb_bytes, dtype=np.float32)
        vec_norm = vec / (np.linalg.norm(vec) + 1e-8)
        similarity = float(np.dot(query_norm, vec_norm))
        scored.append((similarity, source, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(source, text) for _, source, text in scored[:k]]
