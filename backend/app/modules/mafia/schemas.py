from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Mode = Literal["classic", "custom"]
Phase = Literal["lobby", "night", "day", "vote", "finished", "closed"]
Role = Literal["mafia", "doctor", "detective", "citizen"]
Winner = Literal["mafia", "town", "draw"]
ChatChannel = Literal["public", "mafia"]


class RoomSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Mode = "classic"
    doctor: bool = True
    detective: bool = True
    night_seconds: int = Field(default=45, ge=15, le=180)
    day_seconds: int = Field(default=90, ge=15, le=300)
    vote_seconds: int = Field(default=35, ge=15, le=180)

    @model_validator(mode="after")
    def classic_requires_default_rules(self) -> "RoomSettings":
        if self.mode == "classic" and self.model_dump(exclude={"mode"}) != {
            name: field.default for name, field in type(self).model_fields.items() if name != "mode"
        }:
            raise ValueError("Для изменения правил выберите настраиваемую партию")
        return self


class Player(BaseModel):
    name: str
    alive: bool = True
    role: Role | None = None


class PlayerRead(Player):
    id: UUID


class Outcome(BaseModel):
    round: int
    phase: Literal["night", "vote"]
    player_id: UUID | None


class Investigation(BaseModel):
    round: int
    player_id: UUID
    mafia: bool


class ChatMessage(BaseModel):
    id: UUID
    player_id: UUID
    name: str
    text: str
    sent_at: datetime


class RoomState(BaseModel):
    host_id: UUID
    settings: RoomSettings
    deadline: datetime | None
    phase: Phase = "lobby"
    round: int = 0
    turn: int = 0
    winner: Winner | None = None
    players: dict[UUID, Player]
    targets: dict[UUID, UUID | None] = Field(default_factory=dict)
    history: list[Outcome] = Field(default_factory=list)
    investigations: list[Investigation] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    mafia_messages: list[ChatMessage] = Field(default_factory=list)


class RoomSummary(BaseModel):
    code: str
    mode: Mode
    phase: Phase
    player_count: int


class RoomRead(BaseModel):
    code: str
    settings: RoomSettings
    host_id: UUID
    phase: Phase
    round: int
    turn: int
    deadline: datetime | None
    server_time: datetime
    winner: Winner | None
    players: list[PlayerRead]
    role: Role | None
    allies: list[UUID]
    eligible_targets: list[UUID]
    can_target: bool
    target_locked: bool
    target_id: UUID | None
    vote_count: int | None
    history: list[Outcome]
    investigations: list[Investigation]
    messages: list[ChatMessage]
    chat: ChatChannel | None
    can_chat: bool


class LobbyAction(BaseModel):
    type: Literal["join", "start", "leave"]


class PhaseAction(BaseModel):
    turn: int = Field(ge=0)


class TargetAction(PhaseAction):
    type: Literal["target"]
    target_id: UUID | None


class ChatAction(PhaseAction):
    type: Literal["chat"]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class OpenVoteAction(PhaseAction):
    type: Literal["open_vote"]


RoomAction = Annotated[
    LobbyAction | TargetAction | ChatAction | OpenVoteAction,
    Field(discriminator="type"),
]
