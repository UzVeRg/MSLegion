import math
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from app.core.validation import DatabaseText


def validate_jsonb(value: JsonValue) -> None:
    if isinstance(value, str) and re.search(r"[\x00\ud800-\udfff]", value):
        raise ValueError("Строки JSON должны содержать допустимые символы Unicode без NUL")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Числа JSON должны быть конечными")
    if isinstance(value, dict):
        for key, item in value.items():
            validate_jsonb(key)
            validate_jsonb(item)
    elif isinstance(value, list):
        for item in value:
            validate_jsonb(item)


class CallbackEventCreate(BaseModel):
    source: DatabaseText = Field(min_length=1, max_length=64)
    event_id: DatabaseText = Field(min_length=1, max_length=128)
    event_type: DatabaseText = Field(min_length=1, max_length=128)
    payload: JsonValue

    @field_validator("payload")
    @classmethod
    def require_storable_payload(cls, value: JsonValue) -> JsonValue:
        validate_jsonb(value)
        return value

    @field_validator("source", "event_id", "event_type")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "Значение не должно быть пустым или состоять только из пробельных символов"
            )
        return normalized


class IntegrationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    event_id: str
    event_type: str
    payload: JsonValue
    received_at: datetime


class CallbackReceipt(BaseModel):
    accepted: Literal[True] = True
    duplicate: bool
    event: IntegrationEventRead
