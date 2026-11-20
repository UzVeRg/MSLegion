import asyncio
import logging
import re
from typing import Literal

from httpx import AsyncClient, HTTPError

DeliveryOutcome = Literal["sent", "failed", "uncertain"]

# Журнал HTTPX включает полный URL, а Bot API передаёт токен в пути.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def send_message(
    client: AsyncClient, token: str, chat_id: int, message: str
) -> DeliveryOutcome:
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        return "failed"
    try:
        async with asyncio.timeout(12):
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
            )
        if response.status_code >= 500:
            return "uncertain"
        body = response.json()
    except (HTTPError, TimeoutError, ValueError):
        return "uncertain"
    if not isinstance(body, dict):
        return "uncertain"
    if response.is_success and body.get("ok") is True:
        return "sent"
    return "failed" if body.get("ok") is False else "uncertain"
