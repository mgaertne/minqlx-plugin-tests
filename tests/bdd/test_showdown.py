import datetime
import threading
from types import SimpleNamespace

import pytest
from minqlx_plugin_test import (
    assert_plugin_played_sound,
    connected_players,
    death_data,
    fake_player,
    fake_runtime,
    round_end_data,
    setup_cvars,
    setup_game_in_progress,
)
from mockito import any_, spy2, verify, when, when2
from mockito.matchers import matches
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
import showdown as showdown_module
from minqlx import Plugin
from showdown import ALL_WEAPONS, showdown

scenarios("features/showdown.feature", "features/showdown_votes.feature", "features/showdown_to_the_end.feature")

NAMES = "Alice|Bob|Carol|Dave|Eve"
TEAMS = "red|blue|spectator"
NOON = datetime.datetime(2025, 6, 15, 12, 0)
CVARS = {
    "qlx_commandPrefix": "!",
    "qlx_showdown_vote": "0",
    "qlx_showdown_vote_teamsize": "2",
    "qlx_showdown_min": "2",
    "qlx_showdown_max": "4",
    "qlx_showdown_random_weapons": "g,gl,pg,bfg,gh,ng",
    "qlx_showdown_overwrite_permission_level": "1",
}
NO_WEAPONS = dict.fromkeys(("g", "mg", "sg", "gl", "rl", "lg", "rg", "pg", "bfg", "gh", "ng", "pl", "cg", "hmg"), False)
ORIGINAL_WEAPONS = {**NO_WEAPONS, "mg": True, "gl": True}


class Dice:
    def __init__(self):
        self.roll = 1
        self.kamikaze = 0.9

    def randint(self, _low, _high):
        return self.roll

    def random(self):
        return self.kamikaze

    @staticmethod
    def choice(options):
        return options[0]

    @staticmethod
    def sample(population, count):
        return list(population)[:count]


class Clock:
    def __init__(self):
        self.now = NOON.timestamp()
        self.running = threading.Event()
        self.running.set()

    def time(self):
        return self.now

    def sleep(self, _seconds):
        self.running.wait(timeout=5)


@pytest.fixture(name="dice", autouse=True)
def _dice(monkeypatch):
    dice = Dice()
    monkeypatch.setattr(showdown_module, "random", dice)
    return dice


@pytest.fixture(name="clock", autouse=True)
def _clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(showdown_module, "time", clock)
    monkeypatch.setattr(
        showdown_module,
        "datetime",
        SimpleNamespace(now=lambda: datetime.datetime.fromtimestamp(clock.now)),
    )
    yield clock
    clock.running.set()


@pytest.fixture(autouse=True)
def _server():
    spy2(minqlx.console_command)
    when2(minqlx.console_command, any_).thenReturn(None)
    spy2(minqlx.remove_dropped_items)
    when2(minqlx.remove_dropped_items).thenReturn(None)
    spy2(minqlx.set_weapons)
    when2(minqlx.set_weapons, any_, any_).thenReturn(None)
    spy2(Plugin.stop_sound)
    when2(Plugin.stop_sound).thenReturn(None)


def load_plugin(db, **cvars):
    setup_cvars({**CVARS, **cvars})
    plugin = showdown()
    plugin._db_instance = db
    return plugin


def flush_game_frames(clock):
    clock.running.set()
    fake_runtime.join_minqlx_threads()
    fake_runtime.run_next_frame_tasks()


def stand_on(player, team, alive):
    player.team = team
    player.is_alive = alive
    player.health = 100 if alive else 0
    player.privileges = None
    player.holdable = None
    when(player).weapons().thenReturn(ORIGINAL_WEAPONS)


@given(parsers.parse('the showdown plugin is loaded with the random weapons "{weapons}"'), target_fixture="plugin")
def _plugin_loaded(db, weapons):
    return load_plugin(db, qlx_showdown_random_weapons=weapons)


@given(
    parsers.parse('the showdown plugin is loaded with the random weapons "{weapons}" and no early restoring'),
    target_fixture="plugin",
)
def _plugin_loaded_without_restoring(db, weapons):
    return load_plugin(db, qlx_showdown_random_weapons=weapons, qlx_showdown_min="0")


@given("the showdown plugin is loaded with showdown votes", target_fixture="plugin")
def _plugin_loaded_with_votes(db):
    return load_plugin(db, qlx_showdown_vote="1", qlx_showdown_random_weapons="gl")


@given(parsers.parse('a "{game_type}" game on "{mapname}" is in progress'))
def _game_of_type_in_progress(game_type, mapname):
    setup_game_in_progress(game_type=game_type, mapname=mapname)


@given(parsers.parse("round {number:d} has started"))
def _round_started(number):
    minqlx.EVENT_DISPATCHERS["round_start"].dispatch(number)


@given("the round ended")
@when_step("the round ends")
def _round_ends():
    minqlx.EVENT_DISPATCHERS["round_end"].dispatch(round_end_data(ROUND=1, TEAM_WON="RED"))
    fake_runtime.run_delayed_tasks()


@given(parsers.parse("the {team} team has {points:d} points"))
def _team_has_points(team, points):
    setattr(minqlx.Game(), f"{team}_score", points)


@given(parsers.re(rf'(?P<name>{NAMES}) is alive on the "(?P<team>{TEAMS})" team'))
def _is_alive_on_team(players, name, team):
    stand_on(players[name], team, alive=True)


@given(parsers.re(rf'(?P<name>{NAMES}) is dead on the "(?P<team>{TEAMS})" team'))
def _is_dead_on_team(players, name, team):
    stand_on(players[name], team, alive=False)


@given(parsers.re(rf"(?P<name>{NAMES}) is a spectator"))
def _is_spectator(players, name):
    stand_on(players[name], "spectator", alive=False)


@given(parsers.parse("{count:d} more living players are on the {team} team"))
def _more_living_players(players, count, team):
    for _ in range(count):
        name = f"Extra {len(players)}"
        players[name] = fake_player(1000 + len(players), name, _id=len(players))
        players[name].stats = None
        stand_on(players[name], team, alive=True)
    connected_players(*players.values())


@given(parsers.re(rf"(?P<name>{NAMES}) has (?P<health>\d+) health"))
def _has_health(players, name, health):
    players[name].health = int(health)


@given(parsers.re(rf"(?P<name>{NAMES}) is an admin"))
def _is_admin(players, name):
    players[name].privileges = "admin"


@given(parsers.re(rf"(?P<name>{NAMES}) has the permission level (?P<level>\d+)"))
def _has_permission_level(db, players, name, level):
    db[f"minqlx:players:{players[name].steam_id}:permission"] = level


@given("the dice favour a showdown")
def _dice_favour(dice):
    dice.roll = 1


@given("the dice skip the showdown")
def _dice_skip(dice):
    dice.roll = 100


@given(parsers.parse("the dice roll {roll:d}"))
def _dice_roll(dice, roll):
    dice.roll = roll


@given("the kamikaze roll succeeds")
def _kamikaze_roll(dice):
    dice.kamikaze = 0.1


@given("the clock shows noon on the 15th of June 2025")
def _clock_shows_noon(clock):
    clock.now = NOON.timestamp()


@given(parsers.parse("{seconds:d} seconds passed"))
def _seconds_passed(clock, seconds):
    clock.now += seconds


@given(parsers.parse("the Redis driver has the version {version}"))
def _redis_version(monkeypatch, version):
    monkeypatch.setattr("showdown.redis.VERSION", tuple(int(part) for part in version.split(".")))


@when_step("one of the extra players dies")
def _extra_player_dies(plugin, players):
    extra = next(player for name, player in players.items() if name.startswith("Extra") and player.is_alive)
    extra.is_alive = False
    extra.health = 0
    minqlx.EVENT_DISPATCHERS["death"].dispatch(extra, None, death_data())


@given(parsers.re(rf"(?P<name>{NAMES}) died"))
@when_step(parsers.re(rf"(?P<name>{NAMES}) dies"))
def _dies(plugin, players, name):
    players[name].is_alive = False
    players[name].health = 0
    minqlx.EVENT_DISPATCHERS["death"].dispatch(players[name], None, death_data())


@when_step(parsers.re(rf'(?P<name>{NAMES}) switches to the "(?P<team>{TEAMS})" team'))
def _switches_team(plugin, players, name, team):
    old_team = players[name].team
    players[name].team = team
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], old_team, team)


@when_step(parsers.re(rf'(?P<name>{NAMES}) joins the "(?P<team>{TEAMS})" team'))
def _joins_team(plugin, players, name, team):
    players[name].team = team
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], "spectator", team)


@given("the countdown is held up")
def _countdown_is_held_up(clock):
    clock.running.clear()


@given("the countdown is over")
@when_step("the countdown is over")
def _countdown_is_over(clock):
    flush_game_frames(clock)


@then("a showdown is announced")
def _showdown_is_announced():
    verify(Plugin).msg(matches(r".*showdown! Weapons will be restored"))


@then("no showdown is announced")
def _no_showdown_is_announced():
    verify(Plugin, times=0).msg(matches(r".*showdown!"))


@then(parsers.parse('everybody is not told "{text}"'))
def _everybody_is_not_told(text):
    verify(Plugin, times=0).msg(text)


@then("no vote is counted")
def _no_vote_is_counted():
    verify(Plugin, times=0).msg(matches(r".*voted for"))


@then(parsers.re(rf"(?P<name>{NAMES}) is told \"(?P<text>.*)\""))
def _is_told(players, name, text):
    players[name].assert_was_told(text)


@then(parsers.re(rf"(?P<name>{NAMES}) is not told anything"))
def _is_not_told(players, name):
    verify(players[name], times=0).tell(any_)


@then(parsers.re(rf"(?P<name>{NAMES}) is asked to vote on the fate of (?P<target>{NAMES})"))
def _is_asked_to_vote(players, name, target):
    players[name].assert_was_told(
        "Have a say in your team mate's fate:\n"
        "  ^5!showdown^7 for a random weapon showdown^7\n"
        f"  ^5!hurry^7 to punish ^7{players[target].name}"
    )


@then(parsers.re(rf"(?P<name>{NAMES}) is stripped of all weapons"))
def _is_stripped(players, name):
    verify(players[name], atleast=1).weapons(**dict.fromkeys(NO_WEAPONS, False), hands=False)
    verify(players[name], atleast=1).weapon(15)


@then(parsers.re(rf"(?P<name>{NAMES}) is left untouched"))
def _is_left_untouched(players, name):
    verify(players[name], times=0).weapon(any_)


@then(parsers.re(rf'(?P<name>{NAMES}) wields the "(?P<shortname>\w+)" with haste'))
def _wields(players, name, shortname):
    weapon = next(weapon for weapon in ALL_WEAPONS if weapon.shortname == shortname)
    verify(players[name]).weapons(**{**NO_WEAPONS, "hands": True, shortname: True})
    verify(players[name]).weapon(weapon.ql_id)
    verify(players[name]).ammo(**{shortname: -1})
    verify(players[name]).powerups(haste=30)


@then(parsers.re(rf"(?P<name>{NAMES}) holds a kamikaze"))
def _holds_kamikaze(players, name):
    assert players[name].holdable == "kamikaze"


@then(parsers.re(rf"(?P<name>{NAMES}) holds no kamikaze"))
def _holds_no_kamikaze(players, name):
    assert players[name].holdable is None


@then(parsers.re(rf"(?P<name>{NAMES}) gets her weapons back"))
def _gets_weapons_back(clock, players, name):
    flush_game_frames(clock)
    verify(minqlx).set_weapons(players[name].id, ORIGINAL_WEAPONS)


@then(parsers.re(rf"(?P<name>{NAMES}) is slapped for (?P<damage>\d+) damage"))
def _is_slapped(players, name, damage):
    verify(players[name]).slap(damage=int(damage))


@then(parsers.re(rf'(?P<name>{NAMES}) sees "(?P<text>.*)" in the middle of the screen'))
def _sees_in_the_middle(players, name, text):
    verify(players[name]).center_print(text)


@then(parsers.parse('the server console runs "{command}"'))
def _console_runs(command):
    verify(minqlx).console_command(command)


@then("the weapons are not restored")
def _weapons_are_not_restored():
    verify(minqlx, times=0).console_command("g_guidedRocket 0")
    verify(Plugin, times=0).stop_sound()


@then("the dropped items are removed")
def _dropped_items_are_removed():
    verify(minqlx).remove_dropped_items()


@then(parsers.parse('the sound "{sound}" is played'))
def _sound_is_played(sound):
    assert_plugin_played_sound(sound)


@then(parsers.parse('the sound "{sound}" is not played'))
def _sound_is_not_played(sound):
    verify(Plugin, times=0).play_sound(sound)


@then(parsers.re(rf'the sound "(?P<sound>.*)" is played to (?P<name>{NAMES})'))
def _sound_is_played_to(players, sound, name):
    verify(Plugin).play_sound(sound, players[name])


@then("the sounds are stopped")
def _sounds_are_stopped():
    verify(Plugin).stop_sound()


@then("the sounds are not stopped")
def _sounds_are_not_stopped():
    verify(Plugin, times=0).stop_sound()


@then(parsers.parse('the countdown announces "{text}"'))
def _countdown_announces(clock, text):
    flush_game_frames(clock)
    verify(Plugin, atleast=1).center_print(f"^3{text}")


@then(
    parsers.re(
        rf"the database records that (?P<name>{NAMES}) stood alone for (?P<seconds>\d+) seconds "
        r"when the round ended at 12:00:(?P<second>\d+)"
    )
)
def _database_records_standing_time(db, players, name, seconds, second):
    ended_at = NOON.replace(second=int(second)).timestamp()
    record = db.sorted_sets[f"minqlx:players:{players[name].steam_id}:last_standings"]
    assert record == {ended_at: int(seconds)}
