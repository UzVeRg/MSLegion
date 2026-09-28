import logging
import re
import time
import uuid

from fastapi import Request, Response

from app.core.exceptions import build_error_response
from app.core.logging import request_id_context

logger = logging.getLogger("app.request")

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def resolve_request_id(value: str | None) -> str:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid.uuid4().hex


async def request_context_middleware(
    request: Request,
    call_next,
) -> Response:
    request_id = resolve_request_id(
        request.headers.get("X-Request-ID"),
    )
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    started = time.perf_counter()

    try:
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            response = build_error_response(
                status_code=500,
                code="internal_error",
                message="internal server error",
                request_id=request_id,
            )

        duration_ms = round(
            (time.perf_counter() - started) * 1000,
            3,
        )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        request_id_context.reset(token)
