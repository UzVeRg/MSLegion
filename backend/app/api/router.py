from fastapi import APIRouter, HTTPException, status

from app.core.database import check_database

api_router = APIRouter()


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
