import math
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
)

from app.core.validation import DatabaseText

SERVER_STATUS_SOURCE = "server-status"
SERVER_STATUS_EVENT_TYPE = "server.status"
ProcessingOutcome = Literal["applied", "ignored", "rejected"]


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
    processing_state: Literal["pending", "applied", "ignored", "rejected"] | None = None


class CallbackReceipt(BaseModel):
    accepted: Literal[True] = True
    duplicate: bool
    event: IntegrationEventRead


class ServerStatusPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server_id: uuid.UUID
    online: bool = Field(strict=True)
    observed_at: AwareDatetime


class ServerStatusEventCreate(ServerStatusPayload):
    event_id: Annotated[
        DatabaseText, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
    ]

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value > datetime.now(UTC) + timedelta(minutes=1):
            raise ValueError("Время наблюдения не может опережать сервер более чем на минуту")
        return value.astimezone(UTC)


class ProcessingSummary(BaseModel):
    applied: int = 0
    ignored: int = 0
    rejected: int = 0


class ProcessingMetrics(ProcessingSummary):
    pending: int
    oldest_pending_at: datetime | None
