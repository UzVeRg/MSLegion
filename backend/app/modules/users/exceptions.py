from app.core.exceptions import AppError


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"
    default_message = "Пользователь не найден"


class UserTelegramIdConflictError(AppError):
    status_code = 409
    code = "telegram_id_conflict"
    default_message = "Пользователь с таким telegram_id уже существует"


class UserTelegramUnconfirmedError(AppError):
    status_code = 403
    code = "telegram_binding_unconfirmed"
    default_message = "Привязка к Telegram требует подтверждения администратором"


class UserTelegramIdMismatchError(AppError):
    status_code = 409
    code = "telegram_id_mismatch"
    default_message = "Идентификатор Telegram не соответствует записи пользователя"
