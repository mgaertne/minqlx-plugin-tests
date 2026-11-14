import threading
import time

import pytest
from minqlx_plugin_test import setup_cvars, setup_game_in_progress
from mockito import any_, verify, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from minqlx import Plugin
from thirtysecwarn import thirtysecwarn

scenarios("features/thirtysecwarn.feature")

ROUND_STARTED_AT = 1000


class VirtualClock:
    """Holds sleeping threads until the test says the time has come."""

    def __init__(self):
        self.sleeps = []
        self.entered = threading.Semaphore(0)
        self.released = threading.Event()

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.entered.release()
        self.released.wait(timeout=5)


@pytest.fixture(name="clock")
def _clock(monkeypatch):
    clock = VirtualClock()
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock


@pytest.fixture(name="settings")
def _settings():
    return {"qlx_thirtySecondWarnAnnouncer": "standard", "roundtimelimit": "150"}


def _apply(settings):
    setup_cvars(settings)
    when2(minqlx.get_configstring, 662).thenReturn(str(ROUND_STARTED_AT))
    when2(minqlx.get_configstring, 669).thenReturn("")
    when2(minqlx.get_configstring, 670).thenReturn("")


@given(
    parsers.parse("the thirtysecwarn plugin is loaded with a round time limit of {seconds:d} seconds"),
    target_fixture="plugin",
)
def _plugin_loaded(clock, settings, seconds):
    settings["roundtimelimit"] = str(seconds)
    _apply(settings)
    when2(Plugin.play_sound, any_(str)).thenReturn(None)
    return thirtysecwarn()


@given(parsers.parse("the round time limit is {seconds:d} seconds"))
def _round_time_limit(settings, seconds):
    settings["roundtimelimit"] = str(seconds)
    _apply(settings)


@given(parsers.parse('the announcer "{announcer}" is chosen'))
def _announcer_chosen(settings, announcer):
    settings["qlx_thirtySecondWarnAnnouncer"] = announcer
    _apply(settings)


@given("a timeout was called during the round")
def _timeout_called():
    when2(minqlx.get_configstring, 669).thenReturn("1")


@given("a timeout ended before the round started")
def _timeout_ended_before():
    when2(minqlx.get_configstring, 670).thenReturn(str(ROUND_STARTED_AT - 10))


@given("a timeout ended after the round started")
def _timeout_ended_after():
    when2(minqlx.get_configstring, 670).thenReturn(str(ROUND_STARTED_AT + 10))


@given(parsers.parse('a game of type "{game_type}" on "{mapname}" is in progress'))
def _game_of_type(game_type, mapname):
    setup_game_in_progress(game_type=game_type, mapname=mapname)


@when_step("a round starts")
def _round_starts(plugin, clock):
    minqlx.EVENT_DISPATCHERS["round_start"].dispatch(1)
    assert clock.entered.acquire(timeout=2)


@when_step("the round ends")
def _round_ends(plugin):
    minqlx.EVENT_DISPATCHERS["round_end"].dispatch({"TEAM_WON": "RED", "ROUND": 1})


@when_step("the match starts")
def _match_starts(plugin):
    minqlx.EVENT_DISPATCHERS["game_start"].dispatch({})


@when_step("30 seconds are left in the round")
def _thirty_seconds_left(plugin, clock):
    clock.released.set()
    for thread in threading.enumerate():
        if thread.name.endswith("minqlxthread"):
            thread.join(timeout=2)
    minqlx.handle_frame()
    minqlx.handle_frame()


@then(parsers.parse('the announcer plays "{sound}"'))
def _announcer_plays(sound):
    verify(Plugin).play_sound(sound)


@then(parsers.parse('the announcer plays "{sound}" once'))
def _announcer_plays_once(sound):
    verify(Plugin, times=1).play_sound(sound)


@then("nothing is announced")
def _nothing_is_announced():
    verify(Plugin, times=0).play_sound(any_(str))


@then(parsers.parse("the warning waited {seconds:d} seconds"))
def _warning_waited(clock, seconds):
    assert clock.sleeps == [seconds]
