import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


class CallbackEventCreate(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    payload: JsonValue

    @field_validator("source", "event_id", "event_type")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
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
