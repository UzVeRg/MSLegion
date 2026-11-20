import logging
from unittest.mock import AsyncMock

import pytest

import app.main as main


async def test_lifespan_preserves_host_logging_and_closes_database_on_error(monkeypatch):
    close = AsyncMock()
    monkeypatch.setattr(main, "close_database", close)
    root = logging.getLogger()
    original_handlers = root.handlers.copy()
    original_level = root.level
    with pytest.raises(RuntimeError, match="shutdown"):
        async with main.app.router.lifespan_context(main.app):
            assert root.handlers == original_handlers
            assert root.level == original_level
            raise RuntimeError("shutdown")
    close.assert_awaited_once()
