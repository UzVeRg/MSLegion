from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.communities.models import Community, CommunityServer
from app.modules.telegram_notifications.models import TelegramNotification
from app.modules.users.models import User
from app.telegram import bot


class DeliverySummary(BaseModel):
    sent: int = 0
    failed: int = 0
    uncertain: int = 0
    canceled: int = 0


async def enqueue_status_change(
    session: AsyncSession,
    server: CommunityServer,
    event_id: UUID,
    online: bool,
    observed_at: datetime,
) -> None:
    owner_id = await session.scalar(
        select(User.id)
        .join(Community, Community.owner_id == User.id)
        .where(
            Community.id == server.community_id,
            User.status == "active",
            User.telegram_verified,
            User.telegram_notifications_since <= observed_at,
        )
    )
    if owner_id is not None:
        message = (
            f"Сервер «{server.name}» снова доступен."
            if online
            else f"Сервер «{server.name}» недоступен."
        )
        session.add(
            TelegramNotification(
                event_id=event_id,
                user_id=owner_id,
                state="queued",
                message=message,
            )
        )


async def deliver_notifications(session: AsyncSession, token: str, limit: int) -> DeliverySummary:
    counts = {"sent": 0, "failed": 0, "uncertain": 0, "canceled": 0}
    notification = TelegramNotification
    async with session.begin():
        abandoned = (
            update(notification)
            .where(
                notification.state == "sending",
                notification.attempted_at < datetime.now(UTC) - timedelta(minutes=5),
            )
            .values(state="uncertain")
            .returning(notification.event_id)
        )
        counts["uncertain"] = len((await session.scalars(abandoned)).all())

    async with AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
        for _ in range(limit):
            async with session.begin():
                record = await session.scalar(
                    select(notification)
                    .where(notification.state == "queued")
                    .order_by(notification.created_at, notification.event_id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if record is None:
                    break
                record.state = "sending"
                record.attempted_at = datetime.now(UTC)
                event_id, user_id = record.event_id, record.user_id

            # Согласие проверяется под той же блокировкой, которую берёт его изменение.
            async with session.begin():
                user = await session.get(
                    User, user_id, with_for_update=True, populate_existing=True
                )
                record = await session.get(
                    notification, event_id, with_for_update=True, populate_existing=True
                )
                if record is None or record.state != "sending":
                    continue
                if (
                    user is None
                    or user.status != "active"
                    or not user.telegram_verified
                    or user.telegram_id is None
                    or user.telegram_notifications_since is None
                    or user.telegram_notifications_since > record.created_at
                ):
                    outcome = "canceled"
                else:
                    outcome = await bot.send_message(
                        client, token, user.telegram_id, record.message
                    )
                record.state = outcome
            counts[outcome] += 1
    return DeliverySummary(**counts)
