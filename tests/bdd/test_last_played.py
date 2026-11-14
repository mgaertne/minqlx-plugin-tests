from datetime import datetime, timedelta, timezone

import pytest
import redis
from minqlx_plugin_test import connected_players, fake_player, setup_cvars, setup_game_in_progress
from mockito import any_, mock, verify, when, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from last_played import TIMESTAMP_FORMAT, last_played

scenarios("features/last_played.feature")

ALICE_STEAM_ID = 123


def _ago(amount, unit):
    return (datetime.now(timezone.utc) - timedelta(**{unit: amount})).strftime(TIMESTAMP_FORMAT)


@pytest.fixture(name="db")
def _db():
    db = mock(spec=redis.StrictRedis)
    when(db).exists(any_).thenReturn(False)
    return db


@given("the last_played plugin is loaded", target_fixture="plugin")
def _plugin_loaded(db):
    setup_cvars({"qlx_commandPrefix": "!"})
    plugin = last_played()
    plugin._db_instance = db
    return plugin


@given(parsers.parse('player "{name}" is connected'), target_fixture="player")
def _player_connected(name):
    player = fake_player(ALICE_STEAM_ID, name)
    connected_players(player)
    return player


@given(parsers.parse('a game on "{mapname}" is in progress'))
def _game_in_progress(mapname):
    setup_game_in_progress(mapname=mapname)


@given("no game is running")
def _no_game_is_running():
    when2(minqlx.Game).thenRaise(minqlx.NonexistentGameError("no game"))


@given(parsers.parse('the map "{mapname}" was last played {amount:d} {unit} ago'))
def _map_was_played(db, mapname, amount, unit):
    key = f"minqlx:maps:{mapname}:last_played"
    when(db).exists(key).thenReturn(True)
    when(db).get(key).thenReturn(_ago(amount, unit))


@given(parsers.parse('Alice played "{mapname}" {amount:d} {unit} ago'))
def _alice_played(db, mapname, amount, unit):
    key = f"minqlx:players:{ALICE_STEAM_ID}:last_played"
    when(db).exists(key).thenReturn(True)
    when(db).hget(key, mapname).thenReturn(_ago(amount, unit))


@when_step(parsers.parse('Alice types "{message}"'))
def _alice_types(player, mock_channel, message):
    minqlx.COMMANDS.handle_input(player, message, mock_channel)


@then(parsers.parse('the channel is told "{text}"'))
def _channel_is_told(mock_channel, text):
    verify(mock_channel).reply(text)


@then("the channel is not told anything")
def _channel_is_not_told(mock_channel):
    verify(mock_channel, times=0).reply(any_)
