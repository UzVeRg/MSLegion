from app.core.exceptions import AppError


class EventIdConflictError(AppError):
    status_code = 409
    code = "event_id_conflict"
    default_message = "Событие с этим идентификатором уже существует и имеет другое содержимое"
