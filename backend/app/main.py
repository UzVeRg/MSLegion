from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import close_database
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import request_context_middleware

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

install_exception_handlers(app)
app.middleware("http")(request_context_middleware)
app.include_router(api_router)
