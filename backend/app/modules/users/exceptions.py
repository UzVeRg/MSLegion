from app.core.exceptions import AppError


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"
    default_message = "user not found"


class UserTelegramIdConflictError(AppError):
    status_code = 409
    code = "telegram_id_conflict"
    default_message = "user with this telegram_id already exists"
