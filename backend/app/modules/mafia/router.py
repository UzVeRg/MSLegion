from datetime import UTC, datetime, timedelta
from secrets import token_hex
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.exceptions import AppError, error_responses
from app.core.request_body import LimitedJSONRoute
from app.modules.auth.router import SessionDependency, TokenHash
from app.modules.auth.service import get_own_profile
from app.modules.mafia import game
from app.modules.mafia.models import MafiaRoom
from app.modules.mafia.schemas import (
    Player,
    RoomAction,
    RoomRead,
    RoomSettings,
    RoomState,
    RoomSummary,
)
from app.modules.users.models import User

RoomCode = Annotated[str, Path(pattern=r"^[0-9a-fA-F]{10}$")]
ROOMS_PER_DAY = 12
LOBBY_DURATION = timedelta(days=1)


class RoomNotFound(AppError):
    status_code = 404
    code = "mafia_room_not_found"
    default_message = "Комната не найдена или уже закрыта"


class InvalidAction(AppError):
    status_code = 409
    code = "mafia_invalid_action"
    default_message = "Это действие сейчас недоступно"


class ForbiddenAction(AppError):
    status_code = 403
    code = "mafia_forbidden_action"
    default_message = "Ваша роль не допускает это действие"


class TooManyActions(AppError):
    status_code = 429
    code = "mafia_rate_limit"
    default_message = "Превышена частота действий"


def prevent_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/mafia/rooms",
    tags=["mafia"],
    route_class=LimitedJSONRoute,
    dependencies=[Depends(prevent_caching)],
    responses=error_responses(401, 403, 404, 409, 429),
)


def save(room: MafiaRoom, state: RoomState, now: datetime) -> None:
    room.state = state.model_dump(mode="json")
    room.updated_at = now


def is_closed(state: RoomState, now: datetime) -> bool:
    return state.phase == "closed" or (
        state.phase == "lobby" and state.deadline is not None and state.deadline <= now
    )


@router.get("", summary="Получить комнаты игрока")
async def list_rooms(token_hash: TokenHash, session: SessionDependency) -> list[RoomSummary]:
    actor = await get_own_profile(session, token_hash)
    rooms = await session.scalars(
        select(MafiaRoom)
        .where(MafiaRoom.state.contains({"players": {str(actor.id): {}}}))
        .order_by(MafiaRoom.updated_at.desc(), MafiaRoom.code)
        .limit(20)
    )
    now = datetime.now(UTC)
    result = []
    for room in rooms:
        state = RoomState.model_validate(room.state)
        if not is_closed(state, now):
            game.advance_expired(state, now)
            result.append(game.summarize(room.code, state))
    return result


@router.post(
    "", status_code=status.HTTP_201_CREATED, summary="Создать комнату",
    responses=error_responses(413, 422),
)
async def create_room(
    settings: RoomSettings, token_hash: TokenHash, session: SessionDependency,
) -> RoomRead:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        await session.execute(select(User.id).where(User.id == actor.id).with_for_update())
        now = datetime.now(UTC)
        created = await session.scalar(select(func.count()).select_from(MafiaRoom).where(
            MafiaRoom.created_by == actor.id, MafiaRoom.created_at > now - LOBBY_DURATION,
        ))
        if created >= ROOMS_PER_DAY:
            raise TooManyActions("Можно создать до 12 комнат за 24 часа")
        state = RoomState(
            host_id=actor.id, settings=settings, deadline=now + LOBBY_DURATION,
            players={actor.id: Player(name=actor.display_name)},
        )
        for _ in range(3):
            code = await session.scalar(insert(MafiaRoom).values(
                code=token_hex(5).upper(), created_by=actor.id, created_at=now,
                updated_at=now, state=state.model_dump(mode="json"),
            ).on_conflict_do_nothing(index_elements=[MafiaRoom.code]).returning(MafiaRoom.code))
            if code is not None:
                return game.view(code, state, actor.id, now)
        raise InvalidAction("Не удалось выдать код комнаты. Попробуйте ещё раз")


@router.get("/{code}", summary="Получить своё состояние в комнате")
async def get_room(code: RoomCode, token_hash: TokenHash, session: SessionDependency) -> RoomRead:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        room = await session.get(MafiaRoom, code.upper())
        if room is None:
            raise RoomNotFound
        state = RoomState.model_validate(room.state)
        now = datetime.now(UTC)
        if actor.id not in state.players or is_closed(state, now):
            raise RoomNotFound
        if state.phase != "lobby" and state.deadline and state.deadline <= now:
            await session.refresh(room, with_for_update=True)
            state = RoomState.model_validate(room.state)
            now = datetime.now(UTC)
            if game.advance_expired(state, now):
                save(room, state, now)
        return game.view(room.code, state, actor.id, now)


def apply_action(state: RoomState, actor: User, action: RoomAction, now: datetime) -> None:
    player = state.players.get(actor.id)
    if action.type == "join":
        if player is None:
            if state.phase != "lobby" or len(state.players) >= game.MAX_PLAYERS:
                raise InvalidAction("Партия уже началась или комната заполнена")
            state.players[actor.id] = Player(name=actor.display_name)
        return
    if player is None:
        raise RoomNotFound

    if action.type in ("start", "leave"):
        if state.phase != "lobby":
            raise InvalidAction("Партия уже началась")
        if action.type == "start":
            if state.host_id != actor.id:
                raise ForbiddenAction("Начать партию может только ведущий")
            if len(state.players) < game.MIN_PLAYERS:
                raise InvalidAction("Для начала партии нужно минимум 5 игроков")
            game.start(state, now)
        else:
            del state.players[actor.id]
            if not state.players:
                state.phase = "closed"
                state.deadline = None
            elif state.host_id == actor.id:
                state.host_id = next(iter(state.players))
        return

    if action.turn != state.turn:
        raise InvalidAction("Фаза уже сменилась")
    match action.type:
        case "open_vote":
            if state.phase != "day":
                raise InvalidAction
            if state.host_id != actor.id:
                raise ForbiddenAction("Открыть голосование может только ведущий")
            game.advance(state, now)
        case "target":
            voters = game.active_voters(state)
            if actor.id not in voters:
                raise ForbiddenAction
            if actor.id in state.targets:
                if state.targets[actor.id] == action.target_id:
                    return
                raise InvalidAction("Выбор уже принят")
            if action.target_id is not None and action.target_id not in game.target_options(
                state, actor.id
            ):
                raise InvalidAction("Выберите доступного игрока")
            state.targets[actor.id] = action.target_id
            if all(voter in state.targets for voter in voters):
                game.advance(state, now)
        case "chat":
            if (
                not player.alive or state.phase == "finished"
                or not game.chat_channel(state, actor.id)
            ):
                raise ForbiddenAction("Сейчас вы не можете писать в чат")
            if not game.append_message(state, actor.id, action.text, now):
                raise TooManyActions("Отправляйте не чаще одного сообщения в секунду")


@router.post(
    "/{code}/actions", summary="Выполнить действие в комнате",
    responses=error_responses(413, 422),
)
async def room_action(
    code: RoomCode, action: RoomAction, token_hash: TokenHash, session: SessionDependency,
) -> RoomRead | None:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        room = await session.get(MafiaRoom, code.upper(), with_for_update=True)
        if room is None:
            raise RoomNotFound
        state = RoomState.model_validate(room.state)
        now = datetime.now(UTC)
        if is_closed(state, now):
            raise RoomNotFound
        game.advance_expired(state, now)
        apply_action(state, actor, action, now)
        if state.model_dump(mode="json") != room.state:
            save(room, state, now)
        return None if action.type == "leave" else game.view(room.code, state, actor.id, now)
