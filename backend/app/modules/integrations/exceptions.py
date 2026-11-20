from app.core.exceptions import AppError


class EventIdConflictError(AppError):
    status_code = 409
    code = "event_id_conflict"
    default_message = "event id already exists with different content"
