from fastapi import APIRouter, Response

from app.core.exceptions import error_responses
from app.core.request_body import LimitedJSONRoute
from app.modules.auth.router import SessionDependency, TokenHash
from app.modules.finance import service
from app.modules.finance.schemas import CheckInRequest, WalletRead

router = APIRouter(
    prefix="/finance/wallet",
    tags=["finance"],
    route_class=LimitedJSONRoute,
    responses=error_responses(401),
)


@router.get("", summary="Получить баланс LC и состояние отметки")
async def read_wallet(
    response: Response, session: SessionDependency, token_hash: TokenHash
) -> WalletRead:
    response.headers["Cache-Control"] = "no-store"
    return await service.read_wallet(session, token_hash)


@router.post(
    "/check-in",
    summary="Получить ежедневную награду LC",
    responses=error_responses(409, 413, 422),
)
async def claim_check_in(
    payload: CheckInRequest, response: Response, session: SessionDependency, token_hash: TokenHash
) -> WalletRead:
    response.headers["Cache-Control"] = "no-store"
    return await service.claim_check_in(session, token_hash, payload.date)
