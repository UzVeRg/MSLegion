import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_integration_postgres import isolated_schema, migrate_and_check

from app.core.config import get_settings
from app.modules.auth.models import UserSession
from app.modules.users.models import User
from app.telegram import worker


@pytest.mark.integration
@pytest.mark.skipif(
    not get_settings().run_integration_tests, reason="Интеграционные тесты отключены"
)
def test_worker_purges_inactive_sessions_in_batches(monkeypatch):
    async def run():
        async with isolated_schema() as engine:
            async with engine.begin() as connection:
                await connection.run_sync(migrate_and_check)
            factory = async_sessionmaker(engine)
            monkeypatch.setattr(worker, "SessionFactory", factory)
            monkeypatch.setattr(worker, "close_database", AsyncMock())
            monkeypatch.setattr(get_settings(), "telegram_bot_token", None)

            past = datetime.now(UTC) - timedelta(days=1)
            future = datetime.now(UTC) + timedelta(days=1)
            active_hash = bytes(32)
            locked_hash = (1).to_bytes(32)
            async with factory.begin() as session:
                user = User(display_name="Тест очистки")
                session.add(user)
                await session.flush()
                session.add(UserSession(token_hash=active_hash, user_id=user.id, expires_at=future))
                for index in range(1, 503):
                    session.add(
                        UserSession(
                            token_hash=index.to_bytes(32),
                            user_id=user.id,
                            expires_at=past if index % 2 else future,
                            revoked_at=None if index % 2 else past,
                        )
                    )

            async def remaining():
                async with factory() as session:
                    return set(await session.scalars(select(UserSession.token_hash)))

            async with factory.begin() as other:
                await other.get(UserSession, locked_hash, with_for_update=True)
                await asyncio.wait_for(worker.run(), timeout=10)
                assert len(await remaining()) == 3
                await asyncio.wait_for(worker.run(), timeout=10)
                assert await remaining() == {active_hash, locked_hash}

            monkeypatch.setattr(
                worker,
                "process_pending_events",
                AsyncMock(side_effect=RuntimeError("Сбой событий")),
            )
            with pytest.raises(RuntimeError, match="Сбой событий"):
                await worker.run()
            assert await remaining() == {active_hash}

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)
