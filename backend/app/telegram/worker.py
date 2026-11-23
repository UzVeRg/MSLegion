import asyncio

from app.core.config import get_settings
from app.core.database import SessionFactory, close_database
from app.modules.auth.maintenance import purge_inactive_sessions
from app.modules.integrations.processing import process_pending_events
from app.modules.telegram_notifications.service import deliver_notifications


async def run() -> None:
    try:
        async with SessionFactory() as session:
            removed = await purge_inactive_sessions(session)
            if removed:
                print(f"Удалено завершённых сессий: {removed}.")
            processed = await process_pending_events(session, limit=100)
            token = get_settings().telegram_bot_token
            if token is None:
                return
            sent = await deliver_notifications(session, token.get_secret_value(), limit=20)
            if any(processed.model_dump().values()) or any(sent.model_dump().values()):
                print(
                    f"Наблюдения: применено {processed.applied}, "
                    f"пропущено {processed.ignored}, отклонено {processed.rejected}. "
                    f"Уведомления: отправлено {sent.sent}, ошибок {sent.failed}, "
                    f"неизвестный результат {sent.uncertain}, отменено {sent.canceled}."
                )
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)
