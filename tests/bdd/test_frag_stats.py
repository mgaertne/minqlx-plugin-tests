import pytest
import redis
from minqlx_plugin_test import setup_cvars
from mockito import mock, verify, when
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from frag_stats import COLLECTED_SOULZ_KEY, REAPERZ_KEY, frag_stats

scenarios("features/frag_stats.feature")


@pytest.fixture(name="pipeline")
def _pipeline():
    return mock(strict=False)


@pytest.fixture(name="db")
def _db(pipeline):
    db = mock(spec=redis.StrictRedis)
    when(db).pipeline(transaction=False).thenReturn(pipeline)
    return db


@given("the frag_stats plugin is loaded", target_fixture="plugin")
def _plugin_loaded(db):
    setup_cvars({"qlx_commandPrefix": "!"})
    plugin = frag_stats()
    plugin._db_instance = db
    return plugin


def _death(victim, killer, means_of_death):
    minqlx.EVENT_DISPATCHERS["death"].dispatch(victim, killer, {"MOD": means_of_death})


@given(parsers.parse("{killer:w} fragged {victim:w}"))
@when_step(parsers.parse("{killer:w} fragged {victim:w}"))
def _fragged(plugin, players, killer, victim):
    _death(players[victim], players[killer], "ROCKET")


@given("Alice killed herself")
def _alice_killed_herself(plugin, players):
    _death(players["Alice"], players["Alice"], "ROCKET")


@given("Bob fell into the void")
def _bob_fell_into_the_void(plugin, players):
    _death(players["Bob"], None, "HURT")


@given("Bob switched teams")
def _bob_switched_teams(plugin, players):
    _death(players["Bob"], None, "SWITCHTEAM")


@when_step("a new game is counting down")
def _new_game_counts_down(plugin):
    minqlx.EVENT_DISPATCHERS["game_countdown"].dispatch()


@given(
    parsers.parse("the database says Alice fragged Bob {alice_frags:d} times and Bob fragged Alice {bob_frags:d} times")
)
def _database_scores(db, players, alice_frags, bob_frags):
    alice, bob = players["Alice"].steam_id, players["Bob"].steam_id
    when(db).zscore(COLLECTED_SOULZ_KEY.format(alice), bob).thenReturn(float(alice_frags))
    when(db).zscore(REAPERZ_KEY.format(alice), bob).thenReturn(float(bob_frags))


@then("the database counted Alice's soul of Bob once")
def _database_counted(pipeline, players):
    alice, bob = players["Alice"].steam_id, players["Bob"].steam_id
    verify(pipeline).zincrby(COLLECTED_SOULZ_KEY.format(alice), value=str(bob), amount=1)
    verify(pipeline).zincrby(REAPERZ_KEY.format(bob), value=str(alice), amount=1)
