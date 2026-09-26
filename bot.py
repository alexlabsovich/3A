# -*- coding: utf-8 -*-
"""
Телеграм-бот для заметок с ответами через Gemini API.

Команды:
  /start              — приветствие и краткая справка
  /help               — справка
  /add <текст>        — сохранить новую заметку
  /list [страница]    — список последних заметок
  /show <id>          — показать заметку целиком
  /del <id>           — удалить заметку
  /ask <вопрос>       — найти релевантные заметки и получить ответ от Gemini

Любое обычное текстовое сообщение (не команда) тоже воспринимается
как запрос /ask — бот ищет подходящие заметки и отвечает с их учётом.

Бот реагирует ТОЛЬКО на сообщения от пользователя с ALLOWED_USER_ID.
"""

import logging

import telebot
from telebot.types import Message

from config import BOT_TOKEN, ALLOWED_USER_ID, MAX_CONTEXT_NOTES
import storage
import groq_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("notes_bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

NOTES_PER_PAGE = 10


def is_allowed(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id == ALLOWED_USER_ID


def guard(handler):
    """Декоратор: пропускает только разрешённого пользователя, остальных игнорирует."""

    def wrapper(message: Message):
        if not is_allowed(message):
            log.info(
                "Игнорирую сообщение от постороннего пользователя id=%s username=%s",
                getattr(message.from_user, "id", None),
                getattr(message.from_user, "username", None),
            )
            return
        try:
            handler(message)
        except Exception:
            log.exception("Ошибка при обработке сообщения")
            bot.reply_to(message, "Произошла ошибка при обработке запроса. Подробности в логах.")

    return wrapper


@bot.message_handler(commands=["start"])
@guard
def cmd_start(message: Message):
    bot.reply_to(
        message,
        "Привет! Я бот-заметочник.\n\n"
        "• /add <текст> — сохранить заметку\n"
        "• /list — показать список заметок\n"
        "• /show <id> — показать заметку целиком\n"
        "• /del <id> — удалить заметку\n"
        "• /ask <вопрос> — спросить что-то по заметкам\n\n"
        "Можно просто написать вопрос текстом без команды — "
        "я поищу подходящие заметки и отвечу.",
    )


@bot.message_handler(commands=["help"])
@guard
def cmd_help(message: Message):
    cmd_start(message)


@bot.message_handler(commands=["add"])
@guard
def cmd_add(message: Message):
    text = message.text.split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        bot.reply_to(message, "Использование: /add текст заметки")
        return
    note_id = storage.add_note(text[1])
    bot.reply_to(message, f"Заметка сохранена (#{note_id}).")


@bot.message_handler(commands=["list"])
@guard
def cmd_list(message: Message):
    parts = message.text.split(maxsplit=1)
    page = 1
    if len(parts) > 1 and parts[1].strip().isdigit():
        page = max(1, int(parts[1].strip()))

    total = storage.count_notes()
    if total == 0:
        bot.reply_to(message, "Заметок пока нет. Добавь первую через /add <текст>.")
        return

    offset = (page - 1) * NOTES_PER_PAGE
    notes = storage.list_notes(limit=NOTES_PER_PAGE, offset=offset)
    if not notes:
        bot.reply_to(message, f"Страница {page} пустая. Всего заметок: {total}.")
        return

    lines = [f"Заметки (страница {page}, всего {total}):"]
    for n in notes:
        snippet = n["text"].replace("\n", " ")
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        lines.append(f"#{n['id']} [{n['created_at']}] {snippet}")

    max_page = (total - 1) // NOTES_PER_PAGE + 1
    if max_page > 1:
        lines.append(f"\nВсего страниц: {max_page}. Следующая: /list {page + 1}")

    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["show"])
@guard
def cmd_show(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        bot.reply_to(message, "Использование: /show <id заметки>")
        return
    note = storage.get_note(int(parts[1].strip()))
    if not note:
        bot.reply_to(message, "Заметка с таким id не найдена.")
        return
    bot.reply_to(message, f"Заметка #{note['id']} от {note['created_at']}:\n\n{note['text']}")


@bot.message_handler(commands=["del"])
@guard
def cmd_del(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        bot.reply_to(message, "Использование: /del <id заметки>")
        return
    ok = storage.delete_note(int(parts[1].strip()))
    bot.reply_to(message, "Заметка удалена." if ok else "Заметка с таким id не найдена.")


def _ask_and_reply(message: Message, query: str):
    if not query.strip():
        bot.reply_to(message, "Напиши вопрос после команды, например: /ask что я писал про отпуск?")
        return
    bot.send_chat_action(message.chat.id, "typing")
    notes = storage.search_notes(query, limit=MAX_CONTEXT_NOTES)
    answer = groq_client.answer_with_context(query, notes)

    if notes:
        used_ids = ", ".join(f"#{n['id']}" for n in notes)
        answer = f"{answer}\n\n— Использованы заметки: {used_ids}"

    bot.reply_to(message, answer)


@bot.message_handler(commands=["ask"])
@guard
def cmd_ask(message: Message):
    parts = message.text.split(maxsplit=1)
    query = parts[1] if len(parts) > 1 else ""
    _ask_and_reply(message, query)


@bot.message_handler(func=lambda m: True, content_types=["text"])
@guard
def handle_plain_text(message: Message):
    # Любой обычный текст без команды трактуем как запрос к заметкам.
    _ask_and_reply(message, message.text)


def main():
    storage.init_db()
    log.info("Бот запущен. Разрешённый пользователь: %s", ALLOWED_USER_ID)
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
