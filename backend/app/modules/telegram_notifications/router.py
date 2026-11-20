from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import Settings, get_settings
from app.core.exceptions import error_responses
from app.core.security import require_admin_key
from app.modules.auth.exceptions import TelegramLoginUnavailableError
from app.modules.auth.router import SessionDependency
from app.modules.telegram_notifications.service import DeliverySummary, deliver_notifications

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
    responses=error_responses(401, 422, 503),
)


@router.post("/admin/telegram-notifications/send", summary="Отправить уведомления Telegram")
async def send_notifications(
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DeliverySummary:
    if settings.telegram_bot_token is None:
        raise TelegramLoginUnavailableError("Отправка уведомлений Telegram не настроена")
    return await deliver_notifications(
        session, settings.telegram_bot_token.get_secret_value(), limit
    )
