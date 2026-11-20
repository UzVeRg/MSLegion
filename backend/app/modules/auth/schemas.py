from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.auth.telegram import INIT_DATA_MAX_LENGTH


class TelegramLogin(BaseModel):
    init_data: str = Field(min_length=1, max_length=INIT_DATA_MAX_LENGTH, repr=False)


class SessionToken(BaseModel):
    access_token: str = Field(repr=False)
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
