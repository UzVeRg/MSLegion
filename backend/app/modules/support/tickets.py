from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.support.models import SupportTicket

PAGE_SIZE = 10


async def create_ticket(
    session: AsyncSession, author_id: int, message_id: int, description: str,
) -> int:
    async with session.begin():
        result = await session.execute(
            insert(SupportTicket)
            .values(author_id=author_id, message_id=message_id, description=description)
            .on_conflict_do_nothing(constraint="uq_support_tickets_message")
            .returning(SupportTicket.id)
        )
        ticket_id = result.scalar_one_or_none()
        if ticket_id is not None:
            return ticket_id
        result = await session.execute(select(SupportTicket.id).where(
            SupportTicket.author_id == author_id, SupportTicket.message_id == message_id,
        ))
        return result.scalar_one()


async def read_ticket(
    session: AsyncSession, ticket_id: int, author_id: int | None,
) -> SupportTicket | None:
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if author_id is not None:
        query = query.where(SupportTicket.author_id == author_id)
    return await session.scalar(query)


async def list_tickets(
    session: AsyncSession, author_id: int | None, cursor: int | None,
) -> Sequence[SupportTicket]:
    query = select(SupportTicket).limit(PAGE_SIZE + 1)
    if author_id is None:
        query = query.where(SupportTicket.closed_at.is_(None)).order_by(SupportTicket.id)
        if cursor is not None:
            query = query.where(SupportTicket.id > cursor)
    else:
        query = query.where(SupportTicket.author_id == author_id).order_by(SupportTicket.id.desc())
        if cursor is not None:
            query = query.where(SupportTicket.id < cursor)
    return (await session.scalars(query)).all()


async def answer_ticket(
    session: AsyncSession, ticket_id: int, admin_id: int, answer: str,
) -> int | None:
    async with session.begin():
        return await session.scalar(
            update(SupportTicket)
            .where(
                SupportTicket.id == ticket_id,
                SupportTicket.closed_at.is_(None),
                SupportTicket.answer.is_(None),
            )
            .values(answer=answer, answered_by=admin_id)
            .returning(SupportTicket.author_id)
        )


async def close_ticket(session: AsyncSession, ticket_id: int) -> bool:
    async with session.begin():
        result = await session.scalar(
            update(SupportTicket)
            .where(SupportTicket.id == ticket_id, SupportTicket.closed_at.is_(None))
            .values(closed_at=func.now())
            .returning(SupportTicket.id)
        )
        return result is not None
