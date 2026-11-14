from fnmatch import fnmatch

import pytest
from minqlx_plugin_test import (
    assert_plugin_sent_to_console,
    connected_players,
    fake_player,
    setup_cvar,
    setup_game_in_progress,
    setup_game_in_warmup,
)
from mockito import any_, mock, verify, when, when2
from mockito.matchers import matches
from pytest_bdd import given, parsers, then
from pytest_bdd import when as when_step

import minqlx
from minqlx.database import Redis

STEAM_IDS = {"Alice": 123, "Bob": 456, "Carol": 789, "Dave": 321, "Eve": 654}


class FakeRedis:
    """A dict-backed stand-in for the Redis driver, for plugins that read back what they wrote."""

    def __init__(self):
        self.data = {}
        self.hashes = {}

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = str(value)

    def exists(self, key):
        return key in self.data

    def get(self, key):
        return self.data.get(key)

    def incr(self, key):
        self.data[key] = str(int(self.data.get(key, 0)) + 1)

    def scan_iter(self, match):
        return [key for key in self.data if fnmatch(key, match)]

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def get_permission(self, _player):
        return 0


@pytest.fixture(name="db")
def _db():
    return FakeRedis()


@pytest.fixture(autouse=True)
def _forget_plugin_registrations():
    yield
    minqlx.reset_registrations()


@pytest.fixture(name="players")
def _players():
    return {}


@given(parsers.parse('player "{name}" is connected'))
def _player_connected(players, name):
    players[name] = fake_player(STEAM_IDS[name], name, _id=len(players))
    players[name].stats = None
    connected_players(*players.values())


@given(parsers.parse("{name} is the server owner"))
def _server_owner(name):
    setup_cvar("qlx_owner", str(STEAM_IDS[name]))


@given("nobody but the owner has admin rights", target_fixture="plugin")
def _nobody_is_admin(plugin):
    db = mock(strict=False)
    when(db).get_permission(any_).thenReturn(0)
    plugin.database = Redis
    plugin._db_instance = db
    return plugin


@given(parsers.parse('a game on "{mapname}" is in progress'))
def _game_in_progress(mapname):
    setup_game_in_progress(mapname=mapname)


@given(parsers.parse('a game on "{mapname}" is in warmup'))
def _game_in_warmup(mapname):
    setup_game_in_warmup(mapname=mapname)


@given("no game is running")
def _no_game_is_running():
    when2(minqlx.Game).thenRaise(minqlx.NonexistentGameError("no game"))


@given(parsers.parse('{name} typed "{message}"'))
@when_step(parsers.parse('{name} types "{message}"'))
def _types(players, mock_channel, name, message):
    minqlx.COMMANDS.handle_input(players[name], message, mock_channel)
    minqlx.join_minqlx_threads()


@then(parsers.parse('the channel is told "{text}"'))
def _channel_is_told(mock_channel, text):
    verify(mock_channel).reply(text)


@then(parsers.parse('everybody is told "{text}"'))
def _everybody_is_told(text):
    assert_plugin_sent_to_console(text)


@then("the join is allowed")
def _join_is_allowed(join_allowed):
    assert join_allowed is not False


@then("the join is stopped")
def _join_is_stopped(join_allowed):
    assert join_allowed is False


@then("the channel is told the usage of the command")
def _channel_is_told_usage(mock_channel):
    verify(mock_channel).reply(matches(r"^\^7Usage: \^6!"))


@then("the channel is not told anything")
def _channel_is_not_told(mock_channel):
    verify(mock_channel, times=0).reply(any_)
