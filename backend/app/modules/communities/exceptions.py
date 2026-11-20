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


class CommunityPostNotFoundError(AppError):
    status_code = 404
    code = "community_post_not_found"
    default_message = "Публикация в этом сообществе не найдена"


class CommunityPostImageNotFoundError(AppError):
    status_code = 404
    code = "community_post_image_not_found"
    default_message = "Изображение публикации не найдено"


class CommunityPostTooLargeError(AppError):
    status_code = 413
    code = "community_post_too_large"
    default_message = "Размер запроса публикации превышает 128 КиБ"


class CommunityPostImageTooLargeError(AppError):
    status_code = 413
    code = "community_post_image_too_large"
    default_message = "Размер изображения превышает 2 МиБ"


class CommunityPostImageTypeError(AppError):
    status_code = 415
    code = "community_post_image_type"
    default_message = "Поддерживаются изображения PNG, JPEG и WebP"
