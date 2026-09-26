# -*- coding: utf-8 -*-
"""
Хранилище заметок на SQLite.

Каждая заметка: id, текст, дата создания.
Поиск релевантных заметок для контекста делается простым
подсчётом совпадения слов запроса с текстом заметки (без внешних
сервисов и эмбеддингов — быстро и не требует лишних API-вызовов).
"""

import sqlite3
import re
from datetime import datetime
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def add_note(text: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notes (text, created_at) VALUES (?, ?)",
            (text.strip(), datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def delete_note(note_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0


def get_note(note_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return dict(row) if row else None


def list_notes(limit: int = 20, offset: int = 0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def count_notes() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()
        return row["c"]


_WORD_RE = re.compile(r"[а-яa-zё0-9]+", re.IGNORECASE)


def _words(text: str):
    return set(_WORD_RE.findall(text.lower()))


def search_notes(query: str, limit: int = 6):
    """
    Простой поиск по совпадению слов. Возвращает список заметок,
    отсортированных по убыванию релевантности (без нулевых совпадений,
    если такие есть; если совпадений вообще нет — вернёт последние заметки).
    """
    q_words = _words(query)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()

    scored = []
    for r in rows:
        note_words = _words(r["text"])
        score = len(q_words & note_words)
        if score > 0:
            scored.append((score, dict(r)))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:limit]]

    # Если совпадений по словам нет — отдаём последние заметки,
    # чтобы Gemini всё равно имела хоть какой-то контекст и могла
    # честно сказать, что подходящих заметок не нашлось.
    return [dict(r) for r in rows[:limit]]
