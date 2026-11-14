from datetime import datetime

from minqlx_plugin_test import fake_runtime, game_end_data, setup_cvars
from mockito import any_, mock, verify, when, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import bday as bday_module
import minqlx
from bday import BDAY_KEY, LONG_MAP_NAMES_KEY, bday
from minqlx import Plugin

scenarios("features/bday.feature")

NOW = datetime(2025, 6, 15, 12, 0)
NAME_KEY = "minqlx:players:{}:last_used_name"
BIRTHDAY_SONG = "sound/karaoke4/happybirthday.ogg"
STEAM_IDS = {"Alice": 123, "Bob": 456, "Carol": 789}
NAMES = "Alice|Bob|Carol"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW

    @classmethod
    def today(cls):
        return NOW


def birthday_picks_key(name):
    return f"{BDAY_KEY.format(STEAM_IDS[name])}:{NOW.year}"


@given("today is the 15th of June 2025 around noon")
def _today(monkeypatch):
    monkeypatch.setattr(bday_module, "datetime", FrozenDatetime)


@given("the bday plugin is loaded", target_fixture="plugin")
def _plugin_loaded(db):
    setup_cvars({"qlx_commandPrefix": "!", "qlx_bday_mapscount": "1", "qlx_bday_factory": "ca"})
    when2(Plugin.change_map, any_).thenReturn(None)
    when2(Plugin.play_sound, any_).thenReturn(True)
    when2(Plugin.stop_sound).thenReturn(None)
    plugin = bday()
    plugin._db_instance = db
    return plugin


@given(parsers.parse('the birthday of {name:w} is "{birthday}"'))
def _birthday_is(db, name, birthday):
    db[BDAY_KEY.format(STEAM_IDS[name])] = birthday


@given(parsers.parse('the database knows "{name}" with the Steam ID {steam_id:d}'))
def _database_knows(db, name, steam_id):
    db[NAME_KEY.format(steam_id)] = name


@given("the delayed tasks run")
def _delayed_tasks_run():
    fake_runtime.run_delayed_tasks()


@given(parsers.parse("{name:w} picked {amount:d} birthday map this year"))
@given(parsers.parse("{name:w} picked {amount:d} birthday maps this year"))
def _picked_maps(db, name, amount):
    db[birthday_picks_key(name)] = amount


@given(parsers.parse('the maps plugin knows the maps "{first}" and "{second}"'))
def _maps_plugin(monkeypatch, first, second):
    maps = mock({"logged_maps": [first, second]}, strict=False)
    monkeypatch.setitem(Plugin._loaded_plugins, "maps", maps)


@given(parsers.parse('the maps_manager plugin knows the maps "{first}" and "{second}"'))
def _maps_manager_plugin(monkeypatch, first, second):
    maps_manager = mock({"installed_maps": [first, second]}, strict=False)
    monkeypatch.setitem(Plugin._loaded_plugins, "maps_manager", maps_manager)


@given(parsers.parse('the database names the map "{short}" "{long}"'))
def _database_names_map(db, short, long):
    db.hashes.setdefault(LONG_MAP_NAMES_KEY, {})[short] = long


@given("the karaoke plugin is loaded", target_fixture="karaoke")
def _karaoke_loaded(monkeypatch):
    karaoke = mock(strict=False)
    monkeypatch.setitem(Plugin._loaded_plugins, "karaoke", karaoke)
    return karaoke


@given(parsers.re(rf'(?P<name>{NAMES}) picked the map "(?P<mapname>.*)"'))
def _picked_map(players, mock_channel, name, mapname):
    minqlx.COMMANDS.handle_input(players[name], f"!bmap {mapname}", mock_channel)


@given(parsers.parse('the map changes to "{mapname}"'))
def _map_changes(mapname):
    minqlx.EVENT_DISPATCHERS["map"].dispatch(mapname, "ca")


@when_step(parsers.parse('{name:w} types "{message}" in the red team chat'))
def _types_in_red_team_chat(players, name, message):
    when(minqlx.CHAT_CHANNEL).reply(any_).thenReturn(None)
    minqlx.COMMANDS.handle_input(players[name], message, minqlx.RED_TEAM_CHAT_CHANNEL)
    fake_runtime.join_minqlx_threads()


@when_step(parsers.parse("{name:w} has loaded"))
def _has_loaded(plugin, players, name):
    minqlx.EVENT_DISPATCHERS["player_loaded"].dispatch(players[name])
    fake_runtime.run_delayed_tasks()


@when_step("the game ends")
def _game_ends(plugin):
    minqlx.EVENT_DISPATCHERS["game_end"].dispatch(game_end_data())


@when_step(parsers.parse('{name:w} joins the "{team}" team'))
def _joins_team(plugin, players, name, team):
    minqlx.EVENT_DISPATCHERS["team_switch"].dispatch(players[name], "spectator", team)


@then(parsers.re(rf'(?P<name>{NAMES}) is told "(?P<text>.*)"'))
def _is_told(players, name, text):
    players[name].assert_was_told(text)


@then(parsers.re(rf"(?P<name>{NAMES}) is not told anything"))
def _is_not_told(players, name):
    verify(players[name], times=0).tell(any_)


@then(parsers.parse('the main chat is told "{text}"'))
def _main_chat_is_told(text):
    verify(minqlx.CHAT_CHANNEL).reply(text)


@then(parsers.parse("the birthday of {name:w} is not stored yet"))
def _birthday_not_stored(db, name):
    assert BDAY_KEY.format(STEAM_IDS[name]) not in db


@then(parsers.parse('the birthday of {name:w} is stored as "{birthday}"'))
def _birthday_stored(db, name, birthday):
    assert db[BDAY_KEY.format(STEAM_IDS[name])] == birthday


@then(parsers.parse('the birthday of the Steam ID {steam_id:d} is stored as "{birthday}"'))
def _birthday_stored_for_steam_id(db, steam_id, birthday):
    assert db[BDAY_KEY.format(steam_id)] == birthday


@then(parsers.parse('the server changes to "{command}" three seconds later'))
def _server_changes_map(command):
    fake_runtime.run_delayed_tasks()
    verify(Plugin).change_map(command)


@then("the server does not change the map")
def _server_does_not_change_map():
    fake_runtime.run_delayed_tasks()
    verify(Plugin, times=0).change_map(any_)


@then(parsers.parse("{name:w} picked {amount:d} birthday map this year"))
@then(parsers.parse("{name:w} picked {amount:d} birthday maps this year"))
def _picked_maps_are(db, name, amount):
    assert int(db.data.get(birthday_picks_key(name), 0)) == amount


@then("the birthday song is played")
def _song_is_played():
    verify(Plugin).stop_sound()
    verify(Plugin).play_sound(BIRTHDAY_SONG)


@then("no birthday song is played")
def _no_song_is_played():
    verify(Plugin, times=0).play_sound(any_)


@then(parsers.parse('the karaoke plugin sings "{song}"'))
def _karaoke_sings(karaoke, song):
    assert karaoke.currentsong == song
    assert karaoke.double is True
    verify(karaoke).clrdouble(66, "_")
