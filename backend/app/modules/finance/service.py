from datetime import UTC, date, datetime, time, timedelta, timezone
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.auth.service import get_own_profile
from app.modules.finance.ledger import lock_account, post_entry
from app.modules.finance.models import LCAccount
from app.modules.finance.schemas import DailyReward, WalletRead

MOSCOW_TIME = timezone(timedelta(hours=3))
INITIAL_REWARDS = (10, 20, 40, 10, 20, 30, 100, 20, 40, 25, 40, 60, 60, 120, 10, 20)


class CheckInDateChangedError(AppError):
    status_code = 409
    code = "lc_check_in_date_changed"
    default_message = "Дата отметки изменилась. Обновите баланс."


def utc_now() -> datetime:
    return datetime.now(UTC)


def reward_for(day: int) -> int:
    if day <= len(INITIAL_REWARDS):
        return INITIAL_REWARDS[day - 1]
    return 100 if day % 5 == 0 else 50


def wallet_view(account: LCAccount | None, now: datetime) -> WalletRead:
    local = now.astimezone(MOSCOW_TIME)
    today = local.date()
    last = account.last_check_in if account else None
    claimed = last is not None and last >= today
    consecutive = last == today - timedelta(days=1)
    streak = account.streak if account and (claimed or consecutive) else 0
    day = streak if claimed else streak + 1
    group_start = (day - 1) // 5 * 5 + 1
    midnight = datetime.combine(today + timedelta(days=1), time.min, MOSCOW_TIME)
    return WalletRead(
        balance=str(account.balance if account else 0),
        date=today,
        streak=streak,
        day=day,
        claimed_today=claimed,
        rewards=[
            DailyReward(day=number, amount=reward_for(number))
            for number in range(group_start, group_start + 5)
        ],
        seconds_until_reset=ceil((midnight - local).total_seconds()),
    )


async def read_wallet(session: AsyncSession, token_hash: bytes) -> WalletRead:
    user = await get_own_profile(session, token_hash)
    account = await session.get(LCAccount, user.id)
    return wallet_view(account, utc_now())


async def claim_check_in(
    session: AsyncSession, token_hash: bytes, requested_date: date
) -> WalletRead:
    async with session.begin():
        # После ожидания блокировки видим результат предыдущей попытки.
        await session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        user = await get_own_profile(session, token_hash)
        account = await lock_account(session, user.id)
        now = utc_now()
        current = wallet_view(account, now)
        if requested_date != current.date:
            raise CheckInDateChangedError
        if current.claimed_today:
            return current

        await post_entry(
            session,
            account,
            source="daily_check_in",
            operation_key=current.date.isoformat(),
            amount=reward_for(current.day),
        )
        account.last_check_in = current.date
        account.streak = current.day
        return wallet_view(account, now)
