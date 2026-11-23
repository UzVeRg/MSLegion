import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from httpx import AsyncClient, HTTPError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import SessionFactory, close_database
from app.core.logging import application_logging
from app.modules.support.content import SUPPORT_BOT_USERNAME, get_content
from app.modules.support.models import SupportTicket
from app.modules.support.tickets import (
    PAGE_SIZE,
    answer_ticket,
    close_ticket,
    create_ticket,
    list_tickets,
    read_ticket,
)
from app.telegram.bot import DeliveryOutcome, send_message

logger = logging.getLogger(__name__)
Send = Callable[[int, str], Awaitable[DeliveryOutcome]]
MAX_TEXT = 900

USER_HELP = (
    "Поддержка MSLegion\n"
    "/faq — частые вопросы\n"
    "/contacts — контакты администрации\n"
    "/new описание — создать обращение\n"
    "/tickets — мои обращения\n"
    "/ticket номер — посмотреть обращение и ответ"
)
STAFF_HELP = (
    "\n\nКоманды администрации\n"
    "/queue — открытые обращения\n"
    "/ticket номер — открыть обращение\n"
    "/reply номер текст — сохранить и отправить ответ\n"
    "/close номер — закрыть обращение"
)


def number(value: str) -> int | None:
    if re.fullmatch(r"[1-9][0-9]{0,18}", value):
        parsed = int(value)
        if parsed < 2**63:
            return parsed
    return None


def status(ticket: SupportTicket) -> str:
    if ticket.closed_at:
        return "Закрыто"
    return "Есть ответ" if ticket.answer else "Ожидает ответа"


def ticket_text(ticket: SupportTicket) -> str:
    result = f"Обращение №{ticket.id} · {status(ticket)}\n\n{ticket.description}"
    if ticket.answer:
        result += f"\n\nОтвет администрации\n{ticket.answer}"
    return result


async def process_update(
    update: dict[str, Any], session: AsyncSession, settings: Settings, send: Send,
) -> None:
    message = update.get("message", {})
    chat = message.get("chat", {})
    sender = message.get("from", {})
    user_id = sender.get("id")
    if (
        chat.get("type") != "private" or not isinstance(user_id, int)
        or chat.get("id") != user_id or sender.get("is_bot")
    ):
        return

    parts = message.get("text", "").split(maxsplit=1)
    command, _, _ = parts[0].lower().partition("@") if parts else ("", "", "")
    argument = parts[1].strip() if len(parts) == 2 else ""
    staff = user_id in settings.support_admin_ids

    if command == "/faq":
        language = "en" if sender.get("language_code") == "en" else "ru"
        questions = get_content(language, settings.support_faq, settings.support_contacts).questions
        index = number(argument)
        if not questions:
            response = "Ответы пока не опубликованы."
        elif index is not None and index <= len(questions):
            item = questions[index - 1]
            response = f"{item.question}\n\n{item.answer}"
        else:
            lines = [f"{i}. {item.question[:65]}" for i, item in enumerate(questions, 1)]
            response = "Частые вопросы\n\n" + "\n".join(lines) + "\n\nОтвет на вопрос: /faq 1"
    elif command == "/contacts":
        contacts = get_content("ru", settings.support_faq, settings.support_contacts).contacts
        response = "\n".join(
            contact.label if contact.channel == "email" else contact.url for contact in contacts
        ) or "Контакты пока не опубликованы."
    elif command == "/new":
        if 0 < len(argument) <= MAX_TEXT and "\x00" not in argument:
            ticket_id = await create_ticket(session, user_id, message["message_id"], argument)
            response = f"Обращение №{ticket_id} принято. Проверить ответ: /ticket {ticket_id}"
        else:
            response = f"Команда: /new описание проблемы (до {MAX_TEXT} символов)."
    elif command == "/tickets" or (command == "/queue" and staff):
        cursor = number(argument)
        if argument and cursor is None:
            response = "Укажите номер из команды под предыдущим списком."
        else:
            author = user_id if command == "/tickets" else None
            rows = await list_tickets(session, author, cursor)
            lines = [
                f"/ticket {row.id} · {status(row)} · {' '.join(row.description.split())[:60]}"
                for row in rows[:PAGE_SIZE]
            ]
            if len(rows) > PAGE_SIZE:
                lines.append(f"Следующая страница: {command} {rows[PAGE_SIZE - 1].id}")
            response = "\n".join(lines) or "Обращений нет."
    elif command == "/ticket":
        ticket_id = number(argument)
        if ticket_id is None:
            response = "Команда: /ticket номер."
        else:
            ticket = await read_ticket(session, ticket_id, None if staff else user_id)
            response = ticket_text(ticket) if ticket else "Обращение не найдено."
    elif command == "/reply" and staff:
        response = await reply_to_ticket(session, user_id, argument, send)
    elif command == "/close" and staff:
        ticket_id = number(argument)
        if ticket_id is None:
            response = "Команда: /close номер."
        elif await close_ticket(session, ticket_id):
            response = f"Обращение №{ticket_id} закрыто."
        else:
            response = "Открытое обращение не найдено."
    else:
        response = USER_HELP + (STAFF_HELP if staff else "")

    await send(user_id, response)


async def reply_to_ticket(
    session: AsyncSession, admin_id: int, argument: str, send: Send,
) -> str:
    parts = argument.split(maxsplit=1)
    ticket_id = number(parts[0]) if parts else None
    answer = parts[1].strip() if len(parts) == 2 else ""
    if ticket_id is None or not 0 < len(answer) <= MAX_TEXT or "\x00" in answer:
        return f"Команда: /reply номер текст (до {MAX_TEXT} символов)."

    author = await answer_ticket(session, ticket_id, admin_id, answer)
    if author is None:
        return "Обращение закрыто, уже получило ответ или не существует."

    delivered = await send(author, f"Ответ на обращение №{ticket_id}\n\n{answer}")
    if delivered == "sent":
        return f"Ответ по обращению №{ticket_id} сохранён и отправлен."
    return f"Ответ сохранён. Доставка не подтверждена. Автор может открыть /ticket {ticket_id}."


class TelegramPollingError(Exception):
    pass


async def telegram_result(client: AsyncClient, token: str, method: str, **params: Any) -> Any:
    try:
        response = await client.post(f"https://api.telegram.org/bot{token}/{method}", json=params)
        body = response.json()
    except (HTTPError, ValueError):
        raise TelegramPollingError("Нет корректного ответа Telegram") from None
    if not isinstance(body, dict) or not response.is_success or body.get("ok") is not True:
        raise TelegramPollingError(f"Telegram вернул HTTP {response.status_code}")
    return body["result"]


async def poll(client: AsyncClient, token: str, settings: Settings) -> None:
    account = await telegram_result(client, token, "getMe")
    if account.get("username", "").lower() != SUPPORT_BOT_USERNAME.lower():
        raise TelegramPollingError(f"Токен должен принадлежать @{SUPPORT_BOT_USERNAME}")
    logger.info("Бот поддержки принимает обращения")

    offset = 0
    send = partial(send_message, client, token)
    while True:
        try:
            updates = await telegram_result(
                client, token, "getUpdates", offset=offset, timeout=25, limit=20,
                allowed_updates=["message"],
            )
            if not updates:
                offset = 0
            for update in updates:
                async with SessionFactory() as session:
                    await process_update(update, session, settings, send)
                offset = update["update_id"] + 1
        except (TelegramPollingError, SQLAlchemyError) as exc:
            logger.warning("Не удалось обработать очередь поддержки (%s)", type(exc).__name__)
            await asyncio.sleep(5)


async def run() -> None:
    settings = get_settings()
    token = settings.support_bot_token
    if token is None or not settings.support_admin_ids:
        raise SystemExit("Задайте SUPPORT_BOT_TOKEN и SUPPORT_ADMIN_IDS для бота поддержки.")
    value = token.get_secret_value()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", value):
        raise SystemExit("Недопустимый формат токена бота поддержки.")
    try:
        async with AsyncClient(timeout=35, trust_env=False) as client:
            await poll(client, value, settings)
    except TelegramPollingError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        await close_database()


if __name__ == "__main__":
    settings = get_settings()
    with application_logging():
        asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)
