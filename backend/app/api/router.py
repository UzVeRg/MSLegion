from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import error_responses
from app.modules.admin.router import router as admin_router
from app.modules.auth.models import UserSession
from app.modules.auth.router import router as auth_router
from app.modules.communities.content_router import router as content_router
from app.modules.communities.models import (
    Community,
    CommunityMembership,
    CommunityPost,
    CommunityServer,
)
from app.modules.communities.router import router as communities_router
from app.modules.domain_events.models import DomainEvent
from app.modules.domain_events.router import router as domain_events_router
from app.modules.finance.models import LCAccount, LCEntry
from app.modules.finance.router import router as finance_router
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.router import router as integrations_router
from app.modules.mafia.models import MafiaRoom
from app.modules.mafia.router import router as mafia_router
from app.modules.support.models import SupportTicket
from app.modules.support.router import router as support_router
from app.modules.telegram_notifications.models import TelegramNotification
from app.modules.telegram_notifications.router import router as telegram_notifications_router
from app.modules.users.models import User
from app.modules.users.router import router as users_router

api_router = APIRouter(responses=error_responses(500))
api_router.include_router(users_router, prefix="/api/v1")
api_router.include_router(admin_router, prefix="/api/v1")
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(communities_router, prefix="/api/v1")
api_router.include_router(content_router, prefix="/api/v1")
api_router.include_router(domain_events_router, prefix="/api/v1")
api_router.include_router(telegram_notifications_router, prefix="/api/v1")
api_router.include_router(integrations_router, prefix="/api/v1")
api_router.include_router(mafia_router, prefix="/api/v1")
api_router.include_router(finance_router, prefix="/api/v1")
api_router.include_router(support_router, prefix="/api/v1")


@api_router.get(
    "/health",
    tags=["system"],
    summary="Проверка состояния процесса",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get(
    "/ready",
    tags=["system"],
    summary="Проверка готовности приложения",
    responses=error_responses(503),
)
async def readiness(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    try:
        for model in (
            User,
            IntegrationEvent,
            UserSession,
            Community,
            CommunityMembership,
            CommunityServer,
            CommunityPost,
            DomainEvent,
            TelegramNotification,
            MafiaRoom,
            LCAccount,
            LCEntry,
            SupportTicket,
        ):
            await session.execute(select(model).limit(0))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="База данных недоступна",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
    }
