from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import LCAccount, LCEntry

MAX_BALANCE = (1 << 63) - 1


async def lock_account(session: AsyncSession, user_id: UUID) -> LCAccount:
    """Открывает счёт по требованию и блокирует его до конца транзакции."""
    await session.execute(
        insert(LCAccount).values(user_id=user_id).on_conflict_do_nothing(index_elements=["user_id"])
    )
    result = await session.scalars(
        select(LCAccount)
        .where(LCAccount.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.one()


async def post_entry(
    session: AsyncSession,
    account: LCAccount,
    *,
    source: str,
    operation_key: str,
    amount: int,
) -> bool:
    """Записывает операцию к заблокированному счёту. Повтор возвращает False."""
    if type(amount) is not int or amount == 0:
        raise ValueError("Операция LC требует ненулевого целого числа")
    previous = await session.get(LCEntry, (account.user_id, source, operation_key))
    if previous is not None:
        if previous.amount != amount:
            raise ValueError("Ключ операции LC уже использован с другой суммой")
        return False

    balance = account.balance + amount
    if not 0 <= balance <= MAX_BALANCE:
        raise ValueError("Баланс LC вышел за допустимые пределы")
    account.balance = balance
    session.add(LCEntry(
        user_id=account.user_id, source=source, operation_key=operation_key, amount=amount,
    ))
    return True
