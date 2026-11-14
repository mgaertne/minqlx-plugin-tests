import threading
import time

import pytest
from minqlx_plugin_test import connected_players, game_start_data, setup_cvars
from mockito import mock
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import autoready as autoready_module
import minqlx
from autoready import autoready

scenarios("features/autoready.feature")


class RecordedCountdown:
    def __init__(self, duration, *, timed_actions):
        self.duration = duration
        self.seconds_left = duration
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def is_alive(self):
        return self.started and not self.stopped


@pytest.fixture(name="countdowns")
def _countdowns(monkeypatch):
    countdowns = []

    def record(duration, *, timed_actions):
        countdown = RecordedCountdown(duration, timed_actions=timed_actions)
        countdowns.append(countdown)
        return countdown

    monkeypatch.setattr(autoready_module, "CountdownThread", record)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    return countdowns


@pytest.fixture(name="cvars_in_use")
def _cvars_in_use():
    return {}


@given(
    parsers.parse(
        "the autoready plugin is loaded with a minimum of {min_players:d} players, "
        "a delay of {delay:d} seconds and {min_seconds:d} seconds at least"
    ),
    target_fixture="plugin",
)
def _plugin_loaded(countdowns, cvars_in_use, min_players, delay, min_seconds):
    cvars_in_use.update(
        {
            "qlx_autoready_min_players": str(min_players),
            "qlx_autoready_autostart_delay": str(delay),
            "qlx_autoready_min_seconds": str(min_seconds),
            "qlx_autoready_timer_visible": "60",
            "qlx_autoready_disable_manual_readyup": "0",
        }
    )
    setup_cvars(cvars_in_use)
    return autoready()


@given("readying up by hand is forbidden")
def _readyup_forbidden(plugin):
    plugin.disable_player_ready = True


@given(parsers.parse("{name:w} disconnected"))
def _disconnected(players, name):
    players.pop(name)
    connected_players(*players.values())


@given(parsers.parse('{name:w} joined the "{team}" team'))
def _joined(plugin, players, name, team):
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], "spectator", team)


@given(parsers.parse("the countdown has {seconds:d} seconds left"))
def _countdown_has_seconds_left(countdowns, seconds):
    countdowns[-1].seconds_left = seconds


@given("the map changes")
@when_step("the map changes")
def _map_changes(plugin):
    minqlx.EVENT_DISPATCHERS["map"].dispatch("thunderstruck", "ca")


@when_step(parsers.parse('{name:w} joins the "{team}" team'))
def _joins(plugin, players, name, team):
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], "spectator", team)


@when_step(parsers.parse("{name:w} disconnects"))
def _disconnects(plugin, players, name):
    leaving = players.pop(name)
    connected_players(*players.values())
    minqlx.EVENT_DISPATCHERS["player_disconnect"].dispatch(leaving, "disconnected")


@when_step("the match starts")
def _match_starts(plugin):
    minqlx.EVENT_DISPATCHERS["game_start"].dispatch(game_start_data())


@given(parsers.parse('{name:w} is still loading on the "{team}" team'))
def _still_loading(players, name, team):
    players[name].team = team
    players[name].stats = mock({"ping": -1})


@when_step("the game is about to start")
def _game_is_about_to_start(plugin):
    minqlx.EVENT_DISPATCHERS["game_countdown"].dispatch()
    for thread in threading.enumerate():
        if thread.name.endswith("minqlxthread"):
            thread.join(timeout=2)


@when_step(parsers.parse('{name:w} sends the client command "{command}"'), target_fixture="command_result")
def _sends_client_command(plugin, players, name, command):
    return minqlx.EVENT_DISPATCHERS["client_command"].dispatch(players[name], command)


@then(parsers.parse("a countdown of {seconds:d} seconds is running"))
def _countdown_is_running(countdowns, seconds):
    running = [countdown for countdown in countdowns if countdown.is_alive()]
    assert [countdown.duration for countdown in running] == [seconds]


@then(parsers.parse('{name:w} is put on the "{team}" team'))
def _is_put_on(players, name, team):
    players[name].assert_was_put_on(team)


@then("no countdown is running")
def _no_countdown_is_running(countdowns):
    assert not [countdown for countdown in countdowns if countdown.is_alive()]


@then(parsers.parse("exactly {count:d} countdown was started"))
def _countdowns_were_started(countdowns, count):
    assert len(countdowns) == count


@then("the command is passed on")
def _command_is_passed_on(command_result):
    assert command_result is not False


@then("the command is blocked")
def _command_is_blocked(command_result):
    assert command_result is False
