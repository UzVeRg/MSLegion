from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_admin_key
from app.modules.admin.schemas import AdminStatus
from app.modules.admin.service import get_status

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/status",
    response_model=AdminStatus,
)
async def admin_status(session: SessionDependency) -> AdminStatus:
    return await get_status(session)
