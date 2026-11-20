from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import error_responses
from app.modules.admin.router import router as admin_router
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.router import router as integrations_router
from app.modules.users.models import User
from app.modules.users.router import router as users_router

api_router = APIRouter(responses=error_responses(500))
api_router.include_router(users_router, prefix="/api/v1")
api_router.include_router(admin_router, prefix="/api/v1")
api_router.include_router(integrations_router, prefix="/api/v1")


@api_router.get(
    "/health",
    tags=["system"],
    summary="Process health check",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get(
    "/ready",
    tags=["system"],
    summary="Application readiness check",
    responses=error_responses(503),
)
async def readiness(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    try:
        for model in (User, IntegrationEvent):
            await session.execute(select(model).limit(0))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
    }
