from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.validation import DatabaseText

CommunityName = Annotated[
    DatabaseText, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]


class CommunityCreate(BaseModel):
    name: CommunityName


class CommunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
