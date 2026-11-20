from app.core.exceptions import AppError


class CommunityNotFoundError(AppError):
    status_code = 404
    code = "community_not_found"
    default_message = "Сообщество не найдено"


class CommunityOwnerRequiredError(AppError):
    status_code = 403
    code = "community_owner_required"
    default_message = "Операция доступна владельцу сообщества"


class CommunityOwnerRemovalError(AppError):
    status_code = 409
    code = "community_owner_removal"
    default_message = "Владельца сообщества нельзя исключить"


class CommunityServerConflictError(AppError):
    status_code = 409
    code = "community_server_conflict"
    default_message = "Сервер с таким адресом уже зарегистрирован в сообществе"


class CommunityServerNotFoundError(AppError):
    status_code = 404
    code = "community_server_not_found"
    default_message = "Сервер в этом сообществе не найден"
