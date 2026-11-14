from types import SimpleNamespace

from minqlx_plugin_test import editable_game, fake_runtime, game_start_data, round_end_data, setup_cvars
from mockito import any_, mock, verify
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from minqlx import Plugin
from spec_rotation import spec_rotation

scenarios("features/spec_rotation.feature")

NAMES = "Alice|Bob|Carol|Dave|Eve"
TEAMS = "red|blue|spectator|any"


@given("the spec_rotation plugin is loaded", target_fixture="plugin")
def _plugin_loaded(db):
    setup_cvars({"qlx_commandPrefix": "!"})
    plugin = spec_rotation()
    plugin._db_instance = db
    return plugin


@given(parsers.re(rf'(?P<name>{NAMES}) is on the "(?P<team>{TEAMS})" team'))
def _is_on_team(players, name, team):
    players[name].team = team


@given(parsers.re(rf"(?P<name>{NAMES}) waits in the spec rotation"))
def _waits_in_rotation(plugin, players, name):
    plugin.spec_rotation.append(players[name].steam_id)


@given(parsers.parse('the plugin "{name}" ignores the situation'))
def _balance_plugin_ignores(monkeypatch, name):
    monkeypatch.setitem(Plugin._loaded_plugins, name, mock({"last_action": "ignore"}, strict=False))


@given(parsers.parse('a game on "{mapname}" is counting down'))
def _game_is_counting_down(mapname):
    editable_game().state = "countdown"


@given(parsers.parse("the {team} team has {points:d} points"))
def _team_has_points(team, points):
    setattr(minqlx.Game(), f"{team}_score", points)


@given(parsers.re(rf"(?P<name>{NAMES}) has (?P<games>\d+) games completed"))
def _has_games(db, players, name, games):
    db[f"minqlx:players:{players[name].steam_id}:games_completed"] = games


@given(parsers.parse("everybody has dealt {damage:d} damage"))
def _everybody_dealt(players, damage):
    for player in players.values():
        player.stats = SimpleNamespace(damage_dealt=damage)


@given(parsers.re(rf"(?P<name>{NAMES}) has dealt (?P<damage>\d+) damage"))
def _has_dealt(players, name, damage):
    players[name].stats = SimpleNamespace(damage_dealt=int(damage))


@given(parsers.parse("round {number:d} started"))
def _round_started(plugin, number):
    minqlx.EVENT_DISPATCHERS["round_start"].dispatch(number)


@given(parsers.parse("the Steam ID {steam_id:d} waits in the spec rotation"))
def _steam_id_waits_in_rotation(plugin, steam_id):
    plugin.spec_rotation.append(steam_id)


@given(parsers.re(rf"(?P<name>{NAMES}) has a score of (?P<score>\d+)"))
def _has_score(players, name, score):
    players[name].score = int(score)


@given("the countdown ran")
@when_step("the countdown runs")
def _countdown_runs(plugin):
    minqlx.EVENT_DISPATCHERS["game_countdown"].dispatch()
    fake_runtime.run_delayed_tasks()


@given(parsers.re(rf'(?P<name>{NAMES}) tried to join the "(?P<team>{TEAMS})" team'))
@when_step(
    parsers.re(rf'(?P<name>{NAMES}) tries to join the "(?P<team>{TEAMS})" team'),
    target_fixture="attempt_allowed",
)
def _tries_to_join(plugin, players, name, team):
    return minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(players[name], players[name].team, team)


@given(parsers.re(rf'(?P<name>{NAMES}) switched to the "(?P<new>{TEAMS})" team from the "(?P<old>{TEAMS})" team'))
@when_step(parsers.re(rf'(?P<name>{NAMES}) switches to the "(?P<new>{TEAMS})" team from the "(?P<old>{TEAMS})" team'))
def _switches_team(plugin, players, name, new, old):
    players[name].team = new
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], old, new)


@when_step(parsers.re(rf'(?P<name>{NAMES}) sends the client command "(?P<command>.*)"'))
def _sends_client_command(plugin, players, name, command):
    minqlx.EVENT_DISPATCHERS["client_command"].dispatch(players[name], command)
    fake_runtime.join_minqlx_threads()


@when_step(parsers.re(rf"(?P<name>{NAMES}) disconnects"))
def _disconnects(plugin, players, name):
    minqlx.EVENT_DISPATCHERS["player_disconnect"].dispatch(players[name], "disconnected")


@when_step(parsers.re(rf"(?P<name>{NAMES}) has loaded"))
def _has_loaded(plugin, players, name):
    minqlx.EVENT_DISPATCHERS["player_loaded"].dispatch(players[name])
    fake_runtime.run_delayed_tasks()


@when_step("the game starts")
def _game_starts(plugin):
    minqlx.EVENT_DISPATCHERS["game_start"].dispatch(game_start_data())


@when_step(parsers.parse("round {number:d} counts down"))
def _round_counts_down(plugin, number):
    minqlx.EVENT_DISPATCHERS["round_countdown"].dispatch(number)


@when_step(parsers.parse("round {number:d} ends with a win for {winner}"))
def _round_ends_with_win(plugin, number, winner):
    minqlx.EVENT_DISPATCHERS["round_end"].dispatch(round_end_data(ROUND=number, TEAM_WON=winner.upper()))


@given(parsers.parse("round {number:d} ended in a draw"))
@when_step(parsers.parse("round {number:d} ends in a draw"))
def _round_ends_in_draw(plugin, number):
    minqlx.EVENT_DISPATCHERS["round_end"].dispatch(round_end_data(ROUND=number, TEAM_WON="DRAW"))


@when_step("the map changes")
def _map_changes(plugin):
    minqlx.EVENT_DISPATCHERS["map"].dispatch("aerowalk", "ca")


@then(parsers.re(rf'(?P<name>{NAMES}) is told "(?P<text>.*)"'))
def _is_told(players, name, text):
    players[name].assert_was_told(text)


@then(parsers.re(rf"(?P<name>{NAMES}) is not told anything"))
def _is_not_told(players, name):
    verify(players[name], times=0).tell(any_)


@then(parsers.re(rf'(?P<name>{NAMES}) is put on the "(?P<team>{TEAMS})" team'))
def _is_put_on_team(players, name, team):
    players[name].assert_was_put_on(team)


@then(parsers.re(rf"(?P<name>{NAMES}) is not put on any team"))
def _is_not_put_on_team(players, name):
    verify(players[name], times=0).put(any_)


@then("the team switch is stopped")
def _switch_is_stopped(attempt_allowed):
    assert attempt_allowed is False


@then("the team switch is allowed")
def _switch_is_allowed(attempt_allowed):
    assert attempt_allowed is not False


@then("the spec rotation is empty")
def _rotation_is_empty(plugin):
    assert plugin.spec_rotation == []


@then(parsers.re(rf"the spec rotation holds (?P<names>({NAMES})(, ({NAMES}))*( and ({NAMES}))?)"))
def _rotation_holds(plugin, players, names):
    expected = [players[name].steam_id for name in names.replace(" and ", ", ").split(", ")]
    assert plugin.spec_rotation == expected


@then(parsers.re(rf"(?P<name>{NAMES}) has a score of (?P<score>\d+)"))
def _score_is(players, name, score):
    assert players[name].score == int(score)


@then(parsers.parse("the {team} team gained {points:d} points"))
def _team_gained_points(team, points):
    verify(minqlx.Game()).addteamscore(team, points)


@then(parsers.parse("the {team} team lost {points:d} points"))
def _team_lost_points(team, points):
    verify(minqlx.Game()).addteamscore(team, -points)
