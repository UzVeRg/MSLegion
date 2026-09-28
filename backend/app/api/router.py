from fastapi import APIRouter, HTTPException, status

from app.core.database import check_database
from app.modules.admin.router import router as admin_router
from app.modules.integrations.router import router as integrations_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
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
)
async def readiness() -> dict[str, str]:
    if not await check_database():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        )

    return {
        "status": "ok",
        "database": "ok",
    }
