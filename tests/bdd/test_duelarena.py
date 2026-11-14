import inspect
import time

import pytest
from minqlx_plugin_test import assert_plugin_sent_to_console, setup_cvars
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from duelarena import duelarena

scenarios("features/duelarena.feature")


@pytest.fixture(autouse=True)
def _no_sleeping(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)


def _load_plugin():
    setup_cvars(
        {
            "qlx_commandPrefix": "!",
            "qlx_duelarenaDuelToNormalThreshold": "6",
            "qlx_duelarenaNormalToDuelThreshold": "11",
            "qlx_duelarenaDuelToNormalScoreReset": "continue",
        }
    )
    return duelarena()


def _try_to_join(player, team):
    return minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(player, "spectator", team)


@given(parsers.parse('{name:w} is on the "{team}" team'))
def _is_on_team(players, name, team):
    players[name].team = team


@given("the duelarena plugin is loaded", target_fixture="plugin")
def _plugin_loaded():
    return _load_plugin()


@given(
    "a duel arena match is running with Alice against Bob and Carol waiting",
    target_fixture="plugin",
)
def _match_is_running(players):
    plugin = _load_plugin()
    _try_to_join(players["Carol"], "red")
    game = minqlx.Game()
    game.red_score = 0
    game.blue_score = 0
    game.state = "countdown"
    inspect.unwrap(plugin.handle_game_countdown)(plugin)
    game.state = "in_progress"
    return plugin


@given(parsers.parse("the score is red {red:d}, blue {blue:d}"))
def _score_is(red, blue):
    game = minqlx.Game()
    game.red_score = red
    game.blue_score = blue


@when_step(
    parsers.parse('{name:w} tries to join the "{team}" team'),
    target_fixture="join_allowed",
)
def _tries_to_join(plugin, players, name, team):
    return _try_to_join(players[name], team)


@when_step(parsers.parse('the "{team}" team wins a round'))
def _team_wins_a_round(plugin, team):
    data = {"TEAM_WON": team.upper(), "ROUND": 1}
    inspect.unwrap(plugin.handle_round_end)(plugin, data)


@when_step("the next round is about to start")
def _next_round_is_about_to_start(plugin):
    minqlx.EVENT_DISPATCHERS["round_countdown"].dispatch(2)


@when_step(parsers.parse("{name:w} disconnects"), target_fixture="join_allowed")
def _disconnects(plugin, players, name):
    minqlx.EVENT_DISPATCHERS["player_disconnect"].dispatch(players[name], "disconnected")


@when_step(parsers.parse("the match ends with {red:d} to {blue:d}"))
def _match_ends(plugin, red, blue):
    minqlx.EVENT_DISPATCHERS["game_end"].dispatch({"ABORTED": False, "TSCORE0": red, "TSCORE1": blue})


@when_step("the match is aborted")
def _match_is_aborted(plugin):
    minqlx.EVENT_DISPATCHERS["game_end"].dispatch({"ABORTED": True, "TSCORE0": 0, "TSCORE1": 0})


@then(parsers.parse('{name:w} is put on the "{team}" team'))
def _is_put_on(players, name, team):
    players[name].assert_was_put_on(team)


@then(parsers.parse('{name:w} gets the message "{text}"'))
def _gets_the_message(players, name, text):
    players[name].assert_was_told(text)


@then(parsers.parse('everybody is not told "{text}"'))
def _everybody_is_not_told(text):
    assert_plugin_sent_to_console(text, times=0)
