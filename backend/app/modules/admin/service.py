from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.admin.schemas import AdminStatus
from app.modules.integrations.repository import count_events
from app.modules.users.repository import count_users


async def get_status(session: AsyncSession) -> AdminStatus:
    settings = get_settings()

    try:
        users = await count_users(session)
        events = await count_events(session)
    except SQLAlchemyError:
        users = events = None

    return AdminStatus(
        app_name=settings.app_name,
        app_env=settings.app_env,
        database="unavailable" if users is None else "ok",
        users=users,
        integration_events=events,
    )
