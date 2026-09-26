# -*- coding: utf-8 -*-
"""
Обёртка над Gemini API (Google AI Studio) для ответов на вопросы
по заметкам с использованием найденного контекста.
"""

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)

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

_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    system_instruction=_SYSTEM_INSTRUCTION,
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

    response = _model.generate_content(prompt)
    return (response.text or "").strip() or "Не удалось получить ответ от модели."
