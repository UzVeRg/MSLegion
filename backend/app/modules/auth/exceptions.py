from typing import ClassVar

from app.core.exceptions import AppError


class TelegramLoginUnavailableError(AppError):
    status_code = 503
    code = "telegram_login_unavailable"
    default_message = "Вход через Telegram не настроен"


class UserAccessDisabledError(AppError):
    status_code = 403
    code = "user_access_disabled"
    default_message = "Доступ пользователя отключён"


class InvalidSessionError(AppError):
    status_code = 401
    code = "invalid_session"
    default_message = "Сессия недействительна"
    headers: ClassVar[dict[str, str] | None] = {"WWW-Authenticate": "Bearer"}
