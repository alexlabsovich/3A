# -*- coding: utf-8 -*-
"""
Обёртка над Gemini API (Google AI Studio) для ответов на вопросы
по заметкам с использованием найденного контекста.

Реализовано через обычный REST-запрос (requests), БЕЗ библиотеки
google-generativeai — та тянет за собой grpcio, который в Termux
собирается из исходников и может зависать на десятки минут или
падать по нехватке памяти. REST-запрос работает сразу и без сборки.
"""

import logging

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL

log = logging.getLogger("notes_bot.gemini")

_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

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
        "systemInstruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }

    try:
        resp = requests.post(
            _API_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        log.exception("Ошибка запроса к Gemini API")
        return "Не удалось связаться с Gemini API. Проверь интернет и GEMINI_API_KEY."
    except ValueError:
        log.exception("Gemini вернул не-JSON ответ")
        return "Gemini вернул некорректный ответ."

    try:
        candidates = data.get("candidates", [])
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason", "неизвестна")
            return f"Gemini не вернул ответ (причина: {reason})."
        parts = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or "Не удалось получить ответ от модели."
    except (KeyError, IndexError, TypeError):
        log.exception("Неожиданный формат ответа Gemini: %s", data)
        return "Не удалось разобрать ответ от Gemini."
