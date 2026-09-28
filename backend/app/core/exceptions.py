import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 500
    code = "application_error"
    default_message = "application error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"
    default_message = "user not found"


class UserTelegramIdConflictError(AppError):
    status_code = 409
    code = "telegram_id_conflict"
    default_message = "user with this telegram_id already exists"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "invalid api key"


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={"error": jsonable_encoder(error)},
        headers=headers,
    )


async def app_error_handler(
    request: Request,
    exc: AppError,
) -> JSONResponse:
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=get_request_id(request),
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "request failed"
    details = None if isinstance(exc.detail, str) else exc.detail

    return build_error_response(
        status_code=exc.status_code,
        code="http_error",
        message=message,
        request_id=get_request_id(request),
        details=details,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return build_error_response(
        status_code=422,
        code="validation_error",
        message="request validation failed",
        request_id=get_request_id(request),
        details=exc.errors(),
    )


async def unhandled_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return build_error_response(
        status_code=500,
        code="internal_error",
        message="internal server error",
        request_id=get_request_id(request),
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(
        StarletteHTTPException,
        http_error_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_error_handler,
    )
