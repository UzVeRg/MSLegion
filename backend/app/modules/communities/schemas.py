import re
from datetime import datetime
from ipaddress import ip_address
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.validation import DatabaseText

DisplayName = Annotated[
    DatabaseText, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


class CommunityCreate(BaseModel):
    name: DisplayName


class CommunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID


class CommunityServerCreate(BaseModel):
    name: DisplayName
    host: str = Field(min_length=1, max_length=254)
    port: int = Field(strict=True, ge=1, le=65535)

    @field_validator("host")
    @classmethod
    def normalize_host(cls, value: str) -> str:
        host = value.strip().lower().removesuffix(".")
        if "%" not in host:
            try:
                return str(ip_address(host))
            except ValueError:
                pass
        if len(host) <= 253 and all(DNS_LABEL.fullmatch(label) for label in host.split(".")):
            return host
        raise ValueError("Укажите DNS-имя или IP-адрес без схемы, порта и пути")


class CommunityServerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    community_id: UUID
    name: str
    host: str
    port: int
    online: bool | None
    status_observed_at: datetime | None


class CommunityStatistics(BaseModel):
    members: int
    servers: int
    online: int
    offline: int
    unobserved: int
