import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validation import MAX_BIGINT, DatabaseText


class UserCreate(BaseModel):
    telegram_id: int | None = Field(default=None, gt=0, le=MAX_BIGINT)
    display_name: DatabaseText = Field(min_length=1, max_length=128)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        return normalized


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int | None
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime
