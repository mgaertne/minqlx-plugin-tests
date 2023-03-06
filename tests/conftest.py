import functools
import sys
from typing import Union, Any

import pytest
from _pytest.fixtures import FixtureRequest

# noinspection PyProtectedMember
from mockito import any_, patch, mock, spy2, unstub, when, when2, verify

# noinspection PyProtectedMember
from mockito.matchers import Matcher

import minqlx
from minqlx import Game, NonexistentGameError, Plugin

if sys.version_info < (3, 8):
    collect_ignore = ["test_mydiscordbot.py"]
    collect_ignore_glob = ["discord_extensions"]


@pytest.fixture(name="minqlx_plugin", autouse=True)
def _plugin():
    spy2(Plugin.msg)
    when2(Plugin.msg, any_(str)).thenReturn(None)
    spy2(Plugin.center_print)
    when2(Plugin.center_print, any_(str)).thenReturn(None)
    spy2(Plugin.play_sound)
    when2(Plugin.play_sound, any_(str)).thenReturn(None)
    spy2(Plugin.players)
    when2(Plugin.players).thenReturn(None)
    spy2(Plugin.player)
    when2(Plugin.player, any_()).thenReturn(None)
    spy2(Plugin.switch)
    when2(Plugin.switch, any_, any_).thenReturn(None)
    spy2(minqlx.set_cvar)
    when2(minqlx.set_cvar, any_, any_).thenReturn(None)
    spy2(Plugin.kick)
    when2(Plugin.kick, any_, any_(str)).thenReturn(None)
    spy2(minqlx.get_cvar)
    when2(minqlx.get_cvar, "zmq_stats_enable").thenReturn("1")
    patch(minqlx.next_frame, lambda func: func)
    patch(minqlx.thread, lambda func: func)

    yield

    unstub()


@pytest.fixture(name="cvars")
def _cvars(request):
    if hasattr(request, "param"):
        params = request.param.split(",")
        for parameter in params:
            cvar, value = parameter.split("=")
            when2(minqlx.get_cvar, cvar.strip()).thenReturn(value.strip())
    yield
    unstub()


@pytest.fixture(name="no_minqlx_game")
def _no_game():
    when2(minqlx.Game).thenRaise(
        NonexistentGameError("Tried to instantiate a game while no game is active.")
    )
    yield
    unstub()


def assert_game_addteamscore(*, team: str, score: int, _times: int = 1) -> None:
    """Verify that the score of the team was manipulated by the given amount.

    :param: team: the team for which the team score should have been manipualted
    :param: score: the amount that should have been added to the team's score. This may be negative or a matcher.
    :param: times: the amount of times the function addteamscore should have been called. (default: 1)
    """
    verify(minqlx.Game(), times=_times).addteamscore(team, score)


@pytest.fixture(name="minqlx_game")
def game(request: FixtureRequest):
    mock_game = mock(spec=Game, strict=False)
    mock_game.type_short = "ca"
    mock_game.map = "campgrounds"
    mock_game.red_score = 0
    mock_game.blue_score = 0
    mock_game.roundlimit = 8
    mock_game.assert_addteamscore = assert_game_addteamscore
    parse_game_fixture_params(request, mock_game)

    when2(minqlx.Game).thenReturn(mock_game)
    yield mock_game
    unstub(mock_game)


def parse_game_fixture_params(request, minqlx_game):
    if hasattr(request, "param"):
        params = request.param.split(",")
        for parameter in params:
            key, value = parameter.split("=")
            if key.strip() == "game_type":
                minqlx_game.type_short = value.strip()
                continue
            if key.strip() in ["roundlimit", "red_score", "blue_score"]:
                setattr(minqlx_game, key.strip(), int(value.strip()))
                continue
            setattr(minqlx_game, key.strip(), value.strip())


@pytest.fixture(name="game_in_warmup")
def _game_in_warmup(minqlx_game, request: FixtureRequest):
    minqlx_game.state = "warmup"
    minqlx_game.type_short = "ca"
    minqlx_game.map = "campgrounds"

    parse_game_fixture_params(request, minqlx_game)

    yield minqlx_game


@pytest.fixture(name="game_in_countdown")
def _game_in_countdown(minqlx_game, request: FixtureRequest):
    minqlx_game.state = "countdown"
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


def assert_channel_was_replied(
    channel: minqlx.AbstractChannel,
    matcher: Union[str, Matcher, Any],
    *,
    times: int = 1,
) -> None:
    """Verify that a mocked channel was replied to with the given matcher.

    :param: channel: The mocked channel that was replied to.
    :param: matcher: a matcher for the amount reply sent to the channel.
    :param: times: The amount of times the plugin should have replied to the channel. (default: 1).
    """
    verify(channel, times=times).reply(matcher)


@pytest.fixture(name="mock_channel")
def _mocked_channel():
    channel = mock(spec=minqlx.AbstractChannel, strict=False)
    when(channel).reply(any_).thenReturn(None)
    channel.assert_was_replied = functools.partial(assert_channel_was_replied, channel)
    yield channel
    unstub(channel)
