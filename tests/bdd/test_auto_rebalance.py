import inspect
from typing import Dict

import pytest
from minqlx_plugin_test import editable_game, setup_cvars
from mockito import any_, mock, verify
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from auto_rebalance import auto_rebalance

scenarios("features/auto_rebalance.feature")


@pytest.fixture(name="ratings")
def _ratings():
    ratings: Dict[int, Dict[str, Dict[str, int]]] = {}
    balance = mock(strict=False)
    balance.ratings = ratings
    minqlx.Plugin._loaded_plugins["balance"] = balance
    yield ratings
    minqlx.Plugin._loaded_plugins.pop("balance", None)


@given("the auto_rebalance plugin is loaded", target_fixture="plugin")
def _plugin_loaded(ratings):
    setup_cvars(
        {
            "qlx_rebalanceScoreDiffThreshold": "3",
            "qlx_rebalanceWinningStreakThreshold": "3",
            "qlx_rebalanceNumAnnouncements": "2",
        }
    )
    return auto_rebalance()


@given("the balance plugin is not loaded")
def _balance_is_not_loaded(ratings):
    minqlx.Plugin._loaded_plugins.pop("balance")


@given(parsers.parse('{name:w} is on the "{team}" team with a rating of {elo:d}'))
def _is_on_team(players, ratings, name, team, elo):
    players[name].team = team
    ratings[players[name].steam_id] = {"ca": {"elo": elo}}


@given(parsers.parse("{name:w} is a spectator with a rating of {elo:d}"))
def _is_spectator(players, ratings, name, elo):
    players[name].team = "spectator"
    ratings[players[name].steam_id] = {"ca": {"elo": elo}}


@given(parsers.parse('{name:w} joined the "{team}" team'))
def _joined_team(players, name, team):
    minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(players[name], "spectator", team)
    players[name].team = team


@given("a new round starts")
def _new_round_starts(plugin):
    minqlx.EVENT_DISPATCHERS["round_start"].dispatch(1)


@given(parsers.parse("the score is red {red:d}, blue {blue:d}"))
def _score_is(red, blue):
    game = editable_game()
    game.red_score = red
    game.blue_score = blue


@given(parsers.parse('the "{team}" team won {rounds:d} rounds'))
def _team_won_rounds(plugin, team, rounds):
    for _ in range(rounds):
        _round_ends(plugin, team)


def _round_ends(plugin, team):
    inspect.unwrap(plugin.handle_round_end)(plugin, {"TEAM_WON": team.upper(), "ROUND": 1})


@when_step(
    parsers.parse('{name:w} tries to join the "{team}" team'),
    target_fixture="join_allowed",
)
def _tries_to_join(players, name, team):
    return minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(players[name], "spectator", team)


@when_step(parsers.parse('the "{team}" team wins a round'))
def _team_wins_a_round(plugin, team):
    _round_ends(plugin, team)


@then(parsers.parse('{name:w} gets the message "{text}"'))
def _is_told(players, name, text):
    players[name].assert_was_told(text)


@then(parsers.parse('{name:w} is put on the "{team}" team'))
def _is_put_on(players, name, team):
    players[name].assert_was_put_on(team)


@then("the balance plugin is asked to suggest a rebalance")
def _balance_is_asked(players):
    playing = {player.steam_id: "ca" for player in players.values() if player.team in ["red", "blue"]}
    verify(minqlx.Plugin._loaded_plugins["balance"]).add_request(playing, any_, any_)


@then("the balance plugin is not asked")
def _balance_is_not_asked():
    verify(minqlx.Plugin._loaded_plugins["balance"], times=0).add_request(any_, any_, any_)
