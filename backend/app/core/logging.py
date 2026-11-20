import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(
            record,
            "request_id",
            request_id_context.get(),
        )
        if request_id != "-":
            payload["request_id"] = request_id

        for field in (
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )


@contextmanager
def application_logging() -> Iterator[None]:
    logger = logging.getLogger("app")
    level, propagate = logger.level, logger.propagate
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.setLevel(get_settings().log_level.upper())
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(level)
        logger.propagate = propagate
