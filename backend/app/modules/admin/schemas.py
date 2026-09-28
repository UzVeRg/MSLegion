from pydantic import BaseModel


class AdminStatus(BaseModel):
    app_name: str
    app_env: str
    database: str
    users: int | None
    integration_events: int | None
