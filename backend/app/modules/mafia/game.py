from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timedelta
from random import SystemRandom
from uuid import UUID, uuid4

from app.modules.mafia.schemas import (
    ChatChannel,
    ChatMessage,
    Investigation,
    Outcome,
    PlayerRead,
    Role,
    RoomRead,
    RoomState,
    RoomSummary,
)

MIN_PLAYERS = 5
MAX_PLAYERS = 12
MAX_ROUNDS = 12
CHAT_LIMIT = 80


def start(state: RoomState, now: datetime) -> None:
    count = len(state.players)
    mafia_count = 1 + (count >= 7) + (count >= 10)
    roles: list[Role] = ["mafia"] * mafia_count
    if state.settings.doctor:
        roles.append("doctor")
    if state.settings.detective:
        roles.append("detective")
    roles.extend(["citizen"] * (count - len(roles)))
    SystemRandom().shuffle(roles)
    for player, role in zip(state.players.values(), roles, strict=True):
        player.role = role
    state.round = 1
    state.turn += 1
    state.phase = "night"
    state.deadline = now + timedelta(seconds=state.settings.night_seconds)


def active_voters(state: RoomState) -> list[UUID]:
    return [
        player_id for player_id, player in state.players.items()
        if player.alive and (state.phase == "vote" or (
            state.phase == "night" and player.role in ("mafia", "doctor", "detective")
        ))
    ]


def target_options(state: RoomState, actor: UUID) -> list[UUID]:
    role = state.players[actor].role
    return [
        player_id for player_id, player in state.players.items() if player.alive and (
            player_id != actor if state.phase == "vote" or role == "detective"
            else role != "mafia" or player.role != "mafia"
        )
    ]


def unique_choice(votes: Iterable[UUID | None]) -> UUID | None:
    leaders = Counter(vote for vote in votes if vote is not None).most_common(2)
    if leaders and (len(leaders) == 1 or leaders[0][1] > leaders[1][1]):
        return leaders[0][0]
    return None


def night_victim(state: RoomState) -> UUID | None:
    mafia_votes = []
    protected = None
    for player_id, target in state.targets.items():
        match state.players[player_id].role:
            case "mafia":
                mafia_votes.append(target)
            case "doctor":
                protected = target
            case "detective" if target is not None:
                state.investigations.append(Investigation(
                    round=state.round, player_id=target,
                    mafia=state.players[target].role == "mafia",
                ))
    victim = unique_choice(mafia_votes)
    return victim if victim != protected else None


def advance(state: RoomState, now: datetime) -> None:
    state.turn += 1
    if state.phase == "day":
        state.phase = "vote"
        state.deadline = now + timedelta(seconds=state.settings.vote_seconds)
        return

    phase = state.phase
    assert phase in ("night", "vote")
    victim = night_victim(state) if phase == "night" else unique_choice(state.targets.values())
    state.history.append(Outcome(round=state.round, phase=phase, player_id=victim))
    if victim is not None:
        state.players[victim].alive = False
    state.targets.clear()
    state.mafia_messages.clear()

    alive = [player for player in state.players.values() if player.alive]
    mafia_count = sum(player.role == "mafia" for player in alive)
    if mafia_count == 0:
        state.winner = "town"
    elif mafia_count * 2 >= len(alive):
        state.winner = "mafia"
    elif phase == "vote" and state.round >= MAX_ROUNDS:
        state.winner = "draw"

    if state.winner:
        state.phase = "finished"
        state.deadline = None
    elif phase == "night":
        state.phase = "day"
        state.deadline = now + timedelta(seconds=state.settings.day_seconds)
    else:
        state.round += 1
        state.phase = "night"
        state.deadline = now + timedelta(seconds=state.settings.night_seconds)


def advance_expired(state: RoomState, now: datetime) -> bool:
    turn = state.turn
    while state.phase in ("night", "day", "vote") and state.deadline and state.deadline <= now:
        advance(state, state.deadline)
    return state.turn != turn


def chat_channel(state: RoomState, actor: UUID) -> ChatChannel | None:
    if state.phase in ("lobby", "day", "vote", "finished"):
        return "public"
    player = state.players[actor]
    if state.phase == "night" and player.role == "mafia" and player.alive:
        return "mafia"
    return None


def append_message(state: RoomState, actor: UUID, text: str, now: datetime) -> bool:
    messages = state.mafia_messages if chat_channel(state, actor) == "mafia" else state.messages
    last = next((message for message in reversed(messages) if message.player_id == actor), None)
    if last and now - last.sent_at < timedelta(seconds=1):
        return False
    messages.append(ChatMessage(
        id=uuid4(), player_id=actor, name=state.players[actor].name, text=text, sent_at=now,
    ))
    del messages[:-CHAT_LIMIT]
    return True


def summarize(code: str, state: RoomState) -> RoomSummary:
    return RoomSummary(
        code=code, phase=state.phase, mode=state.settings.mode, player_count=len(state.players),
    )


def view(code: str, state: RoomState, actor: UUID, now: datetime) -> RoomRead:
    own = state.players[actor]
    can_target = actor in active_voters(state)
    chat = chat_channel(state, actor)
    return RoomRead(
        code=code, settings=state.settings, host_id=state.host_id, phase=state.phase,
        round=state.round, turn=state.turn, deadline=state.deadline, server_time=now,
        winner=state.winner,
        players=[
            PlayerRead(id=player_id, name=player.name, alive=player.alive,
                       role=player.role if state.phase == "finished" else None)
            for player_id, player in state.players.items()
        ],
        role=own.role,
        allies=[
            player_id for player_id, player in state.players.items()
            if own.role == player.role == "mafia" and player_id != actor
        ],
        eligible_targets=target_options(state, actor) if can_target else [],
        can_target=can_target,
        target_locked=actor in state.targets,
        target_id=state.targets.get(actor),
        vote_count=len(state.targets) if state.phase == "vote" else None,
        history=state.history,
        investigations=state.investigations if own.role == "detective" else [],
        messages=state.mafia_messages if chat == "mafia" else state.messages if chat else [],
        chat=chat,
        can_chat=chat is not None and own.alive and state.phase != "finished",
    )
