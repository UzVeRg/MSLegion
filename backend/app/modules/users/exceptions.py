from app.core.exceptions import AppError


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"
    default_message = "Пользователь не найден"


class UserTelegramIdConflictError(AppError):
    status_code = 409
    code = "telegram_id_conflict"
    default_message = "Пользователь с таким telegram_id уже существует"
