import pytest
from _pytest.fixtures import FixtureRequest
from mockito import when2, unstub, mock
from pytest_mock import MockerFixture

import minqlx
from minqlx import Game, NonexistentGameError


@pytest.fixture(name="no_minqlx_game")
def _no_game():
    when2(minqlx.Game).thenRaise(NonexistentGameError("Tried to instantiate a game while no game is active."))
    yield
    unstub()


@pytest.fixture(name="minqlx_game")
def game(request: FixtureRequest):
    mock_game = mock(spec=Game, strict=False)
    parse_game_fixture_params(request, mock_game)

    when2(minqlx.Game).thenReturn(mock_game)
    yield mock_game
    unstub()


def parse_game_fixture_params(request, minqlx_game):
    if hasattr(request, "param"):
        params = request.param.split(",")
        for parameter in params:
            key, value = parameter.split("=")
            if key == "game_type":
                minqlx_game.type_short = value
                continue
            if key in ["roundlimit", "red_score", "blue_score"]:
                setattr(minqlx_game, key, int(value))
                continue
            setattr(minqlx_game, key, value)


@pytest.fixture(name="game_in_warmup")
def _game_in_warmup(minqlx_game, request: FixtureRequest):
    minqlx_game.state = "warmup"
    minqlx_game.type_short = "ca"
    minqlx_game.map = "campgrounds"

    parse_game_fixture_params(request, minqlx_game)

    yield minqlx_game


@pytest.fixture(name="game_in_progress")
def _game_in_progress(minqlx_game, request: FixtureRequest):
    minqlx_game.state = "in_progress"
    minqlx_game.type_short = "ca"
    minqlx_game.map = "campgrounds"

    parse_game_fixture_params(request, minqlx_game)

    yield minqlx_game


@pytest.fixture(name="game_spy")
def _game_spy(mocker, minqlx_game):
    game_spy = mocker.spy(minqlx_game, "addteamscore")
    yield game_spy
