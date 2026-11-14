import time

import pytest
from minqlx_plugin_test import setup_cvars
from mockito import any_, verify, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from minqlx import Plugin
from team_shots import team_shots

scenarios("features/team_shots.feature")

HIT_SOUND = "sound/feedback/hit_teammate.ogg"


class Clock:
    def __init__(self):
        self.seconds = 1_000_000.0

    def time(self):
        return self.seconds

    def advance(self, milliseconds):
        self.seconds += milliseconds / 1000


@pytest.fixture(name="clock")
def _clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(time, "time", clock.time)
    return clock


@given(
    parsers.parse(
        "the team_shots plugin is loaded with the punishment of {health:d} health for means of death {means:d}"
    ),
    target_fixture="plugin",
)
def _plugin_loaded(clock, health, means):
    setup_cvars(
        {
            "qlx_teamShots_minHealth": "1",
            "qlx_teamShots_punishments": f"{{{means}: {health}}}",
            "qlx_teamShots_min_damage": "15",
            "qlx_teamShots_warning_text": "^1watch your fire!",
            "qlx_teamShots_filtered_means_of_death": "18",
        }
    )
    when2(Plugin.play_sound, any_(str), player=any_).thenReturn(True)
    return team_shots()


@given(parsers.parse('{name:w} is on the "{team}" team with {health:d} health'))
def _is_on_team(players, name, team, health):
    players[name].team = team
    players[name].health = health


@given(parsers.parse("{name:w} has {health:d} health"))
def _has_health(players, name, health):
    players[name].health = health


@given("a new game is counting down")
def _new_game_counts_down(plugin):
    minqlx.EVENT_DISPATCHERS["game_countdown"].dispatch()


@given(parsers.parse("{attacker:w} damaged {target:w} with {damage:d} points by means of death {means:d}"))
def _damaged(plugin, players, attacker, target, damage, means):
    minqlx.EVENT_DISPATCHERS["damage"].dispatch(players[target], players[attacker], damage, 0, means)


@when_step(parsers.parse("{attacker:w} damages {target:w} with {damage:d} points by means of death {means:d}"))
def _damages(plugin, players, attacker, target, damage, means):
    minqlx.EVENT_DISPATCHERS["damage"].dispatch(players[target], players[attacker], damage, 0, means)


@when_step(
    parsers.parse(
        "{attacker:w} damages {target:w} with {damage:d} points and the flag {flags:d} by means of death {means:d}"
    )
)
def _damages_with_flags(plugin, players, attacker, target, damage, flags, means):
    minqlx.EVENT_DISPATCHERS["damage"].dispatch(players[target], players[attacker], damage, flags, means)


@when_step(parsers.parse("{milliseconds:d} milliseconds pass"))
def _time_passes(clock, milliseconds):
    clock.advance(milliseconds)


@then(parsers.parse("{name:w} has {health:d} health"))
def _health_is(players, name, health):
    assert players[name].health == health


@then("Alice hears the team hit sound")
def _hears_sound(players):
    verify(Plugin).play_sound(HIT_SOUND, player=players["Alice"])


@then("Alice hears no team hit sound")
def _hears_no_sound(players):
    verify(Plugin, times=0).play_sound(HIT_SOUND, player=any_)


@then(parsers.parse('{name:w} sees the warning "{text}"'))
def _sees_warning(players, name, text):
    players[name].assert_center_print(text)


@then(parsers.parse("{name:w} sees no warning"))
def _sees_no_warning(players, name):
    verify(players[name], times=0).center_print(any_)
