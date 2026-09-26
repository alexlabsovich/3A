# -*- coding: utf-8 -*-
"""
Конфигурация бота.

Заполни своими значениями:
- BOT_TOKEN       — токен телеграм-бота от @BotFather
- GEMINI_API_KEY  — ключ API из Google AI Studio (https://aistudio.google.com/apikey)
- ALLOWED_USER_ID — телеграм ID, с которого бот будет принимать команды
"""

import os

# Можно вписать значения прямо сюда, ИЛИ задать их как переменные окружения
# (например через `export BOT_TOKEN=...` в Termux) — тогда менять этот файл не нужно.

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_БОТА")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ВСТАВЬ_СЮДА_КЛЮЧ_GEMINI")

# Единственный разрешённый пользователь
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "8373993954"))

# Модель Gemini. Если эта модель станет недоступна/устареет,
# посмотри актуальный список моделей в Google AI Studio и поменяй строку ниже.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Путь к файлу базы данных с заметками
DB_PATH = os.environ.get("NOTES_DB_PATH", "notes.db")

# Сколько заметок максимум подмешивать в контекст одного запроса к Gemini
MAX_CONTEXT_NOTES = 6
