from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.mafia import game
from app.modules.mafia.schemas import Player, RoomSettings, RoomState


def test_custom_mafia_tie_and_expired_turns() -> None:
    now = datetime(2026, 11, 23, tzinfo=UTC)
    players = {uuid4(): Player(name=f"Игрок {index}") for index in range(7)}
    state = RoomState(
        host_id=next(iter(players)),
        players=players,
        deadline=None,
        settings=RoomSettings(
            mode="custom", doctor=False, detective=False,
            night_seconds=20, day_seconds=25, vote_seconds=30,
        ),
    )
    game.start(state, now)
    mafia = game.active_voters(state)
    citizens = [
        player_id for player_id, player in state.players.items() if player.role == "citizen"
    ]
    assert len(mafia) == 2
    assert len(citizens) == 5
    assert state.deadline == now + timedelta(seconds=20)
    assert game.view("AB12CD34EF", state, mafia[0], now).allies == [mafia[1]]
    assert game.view("AB12CD34EF", state, citizens[0], now).allies == []

    state.targets = dict(zip(mafia, citizens[:2], strict=True))
    assert game.advance_expired(state, now + timedelta(seconds=47))
    assert state.phase == "vote"
    assert state.deadline == now + timedelta(seconds=75)
    assert state.history[0].player_id is None
    assert all(player.alive for player in state.players.values())

    assert game.advance_expired(state, now + timedelta(days=1))
    assert state.phase == "finished"
    assert state.winner == "draw"
    assert state.round == 12
