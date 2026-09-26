# -*- coding: utf-8 -*-
"""
Обёртка над Groq API для ответов на вопросы по заметкам
с использованием найденного контекста.

Groq предоставляет OpenAI-совместимый REST API — обычный HTTP-запрос
через requests, никаких тяжёлых SDK и зависимостей не требуется.
Получить ключ: https://console.groq.com/keys
"""

import logging

import requests

from config import GROQ_API_KEY, GROQ_MODEL

log = logging.getLogger("notes_bot.groq")

_API_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_INSTRUCTION = (
    "Ты — ассистент по личным заметкам пользователя в Telegram. "
    "Тебе передаются несколько заметок (с id и датой) в качестве контекста "
    "и вопрос/запрос пользователя. "
    "Отвечай кратко и по делу на русском языке, опираясь только на "
    "предоставленные заметки. "
    "Если среди заметок нет ничего релевантного запросу — прямо скажи об этом, "
    "не выдумывай факты. "
    "Если уместно, укажи в скобках id заметок, на которые опираешься, "
    "например: (заметка #3)."
)


def answer_with_context(query: str, notes: list) -> str:
    """
    notes: список словарей {id, text, created_at}
    """
    if notes:
        context_lines = []
        for n in notes:
            context_lines.append(f"[Заметка #{n['id']} от {n['created_at']}]\n{n['text']}")
        context_block = "\n\n".join(context_lines)
    else:
        context_block = "(заметок пока нет)"

    prompt = (
        f"Контекст (заметки пользователя):\n{context_block}\n\n"
        f"Запрос пользователя: {query}"
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        log.exception("Ошибка запроса к Groq API")
        return "Не удалось связаться с Groq API. Проверь интернет и GROQ_API_KEY."
    except ValueError:
        log.exception("Groq вернул не-JSON ответ")
        return "Groq вернул некорректный ответ."

    try:
        choices = data.get("choices", [])
        if not choices:
            return "Groq не вернул ответ."
        text = choices[0]["message"]["content"].strip()
        return text or "Не удалось получить ответ от модели."
    except (KeyError, IndexError, TypeError):
        log.exception("Неожиданный формат ответа Groq: %s", data)
        return "Не удалось разобрать ответ от Groq."
