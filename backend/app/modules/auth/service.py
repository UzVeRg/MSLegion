from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.telegram import verify_telegram_init_data
from app.modules.users import repository
from app.modules.users.exceptions import UserTelegramUnconfirmedError
from app.modules.users.schemas import UserCreate


async def resolve_telegram_user_id(
    session: AsyncSession,
    init_data: str,
    *,
    bot_token: str,
    now: int,
) -> UUID:
    identity = verify_telegram_init_data(init_data, bot_token=bot_token, now=now)
    payload = UserCreate(telegram_id=identity.telegram_id, display_name=identity.display_name)
    async with session.begin():
        user = await repository.insert_user(session, payload, telegram_verified=True)
        if user is None:
            # Отдельный запрос видит запись после завершения конкурирующей вставки.
            user = await repository.get_user_by_telegram_id(session, identity.telegram_id)
            if user is None or not user.telegram_verified:
                raise UserTelegramUnconfirmedError
        user_id = user.id
    return user_id
