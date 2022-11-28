import pytest
from pytest_mock import MockerFixture

from minqlx import Game, NonexistentGameError


@pytest.fixture(name="no_minqlx_game")
def no_game(mocker: MockerFixture):
    mocker.patch("minqlx.Game",
                 side_effect=NonexistentGameError("Tried to instantiate a game while no game is active."))
    yield


@pytest.fixture(name="minqlx_game")
def game(mocker: MockerFixture):
    mock_game = mocker.MagicMock(spec=Game)
    mocker.patch("minqlx.Game", return_value=mock_game)
    yield mock_game


@pytest.fixture
def game_in_warmup(minqlx_game):
    minqlx_game.state = "warmup"
    minqlx_game.type_short = "ca"
    minqlx_game.map = "campgrounds"
    yield minqlx_game


@pytest.fixture
def game_in_progress(minqlx_game):
    minqlx_game.state = "in_progress"
    minqlx_game.type_short = "ca"
    minqlx_game.map = "campgrounds"
    yield minqlx_game
