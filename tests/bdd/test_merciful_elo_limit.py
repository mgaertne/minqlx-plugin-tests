import time
from typing import Dict

import pytest
from minqlx_plugin_test import setup_cvars
from mockito import any_, mock, verify, when
from mockito.matchers import matches
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from merciful_elo_limit import APPLICATION_GAMES_KEY, merciful_elo_limit

scenarios("features/merciful_elo_limit.feature")


@pytest.fixture(name="db")
def _db():
    db = mock(strict=False)
    when(db).get_permission(any_).thenReturn(0)
    when(db).exists(any_).thenReturn(False)
    when(db).zrangebyscore(any_, any_, "+INF").thenReturn([])
    return db


@pytest.fixture(name="ratings")
def _ratings():
    ratings: Dict[int, Dict[str, Dict[str, int]]] = {}
    minqlx.Plugin._loaded_plugins["balance"] = mock({"ratings": ratings})
    yield ratings
    minqlx.Plugin._loaded_plugins.pop("balance", None)


@given(
    parsers.parse(
        "the merciful_elo_limit plugin is loaded with a minimum rating of {min_elo:d} and {games:d} application games"
    ),
    target_fixture="plugin",
)
def _plugin_loaded(db, ratings, min_elo, games, monkeypatch):
    setup_cvars(
        {
            "qlx_commandPrefix": "!",
            "qlx_mercifulelo_minelo": str(min_elo),
            "qlx_mercifulelo_applicationgames": str(games),
        }
    )
    plugin = merciful_elo_limit()
    plugin._db_instance = db
    monkeypatch.setattr(plugin, "blink2", lambda *_args, **_kwargs: None)
    return plugin


@given(parsers.parse("{name} has permission {level:d}"))
def _has_permission(db, players, name, level):
    when(db).get_permission(players[name]).thenReturn(level)


@given(parsers.parse("the balance plugin rates Alice with {elo:d}"))
def _alice_is_rated(ratings, players, elo):
    ratings[players["Alice"].steam_id] = {"ca": {"elo": elo}}


@given(parsers.parse("Alice used {games:d} application games"))
def _alice_used_games(db, players, games):
    key = APPLICATION_GAMES_KEY.format(players["Alice"].steam_id)
    timestamps = [time.time() - day * 86400 for day in range(games)]
    when(db).exists(key).thenReturn(True)
    when(db).zrangebyscore(key, any_, "+INF").thenReturn(timestamps)


@given("Alice is fully connected")
def _alice_is_fully_connected(players):
    players["Alice"].connection_state = "active"


@given(parsers.parse('Alice plays for the "{team}" team'))
def _alice_plays_for(players, team):
    players["Alice"].team = team


@when_step("Alice has loaded")
def _alice_has_loaded(plugin, players):
    minqlx.EVENT_DISPATCHERS["player_loaded"].dispatch(players["Alice"])


@when_step("a round starts")
def _round_starts(plugin):
    minqlx.EVENT_DISPATCHERS["round_start"].dispatch(1)


@then(parsers.parse("Alice is warned that {left:d} of {games:d} application games are left"))
def _alice_is_warned(players, left, games):
    players["Alice"].assert_was_told(
        matches(rf"^Alice, this is a \^1Skill Warning! .*\^3{left} \^7of {games} application matches left")
    )


@then("Alice is not told anything")
def _alice_is_not_told(players):
    verify(players["Alice"], times=0).tell(any_)


@then(parsers.parse('Bob is told "{text}"'))
def _bob_is_told(players, text):
    players["Bob"].assert_was_told(text)


@then(parsers.parse("Alice is kicked for using up the {games:d} application games"))
def _alice_is_kicked(players, games):
    verify(players["Alice"]).kick(matches(rf"^You used up your {games} application games"))


@then("an application game is recorded for Alice")
def _game_is_recorded(db, players):
    verify(db).zadd(APPLICATION_GAMES_KEY.format(players["Alice"].steam_id), any_, any_)


@then("no application game is recorded for Alice")
def _no_game_is_recorded(db):
    verify(db, times=0).zadd(any_, any_, any_)


@then("the last application game of Alice is removed")
def _last_game_is_removed(db, players):
    key = APPLICATION_GAMES_KEY.format(players["Alice"].steam_id)
    last_game = db.zrangebyscore(key, 0, "+INF")[-1]
    verify(db).zrem(key, last_game)
