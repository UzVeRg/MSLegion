from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import check_database
from app.modules.admin.schemas import AdminStatus
from app.modules.integrations.repository import count_events
from app.modules.users.repository import count_users


async def get_status(session: AsyncSession) -> AdminStatus:
    settings = get_settings()

    if not await check_database():
        return AdminStatus(
            app_name=settings.app_name,
            app_env=settings.app_env,
            database="unavailable",
            users=None,
            integration_events=None,
        )

    return AdminStatus(
        app_name=settings.app_name,
        app_env=settings.app_env,
        database="ok",
        users=await count_users(session),
        integration_events=await count_events(session),
    )
