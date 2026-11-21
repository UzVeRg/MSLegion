import logging
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, JsonValue
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: JsonValue | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {code: {"model": ErrorEnvelope} for code in codes}


class AppError(Exception):
    status_code = 500
    code = "application_error"
    default_message = "Ошибка приложения"
    headers: ClassVar[dict[str, str] | None] = None

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "Недействительный ключ API"


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
    error = ErrorBody(
        code=code, message=message, request_id=request_id, details=jsonable_encoder(details)
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(error=error).model_dump(mode="json", exclude_none=True),
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
        headers=exc.headers,
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Не удалось выполнить запрос"
    details = None if isinstance(exc.detail, str) else exc.detail

    return build_error_response(
        status_code=exc.status_code,
        code="request_body_too_large" if exc.status_code == 413 else "http_error",
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
        message="Запрос не прошёл проверку",
        request_id=get_request_id(request),
        details=[
            {key: error[key] for key in ("type", "loc", "msg")}
            for error in exc.errors()
        ],
    )


async def unhandled_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "Необработанное исключение",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return build_error_response(
        status_code=500,
        code="internal_error",
        message="Внутренняя ошибка сервера",
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
