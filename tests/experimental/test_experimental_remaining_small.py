from types import SimpleNamespace
from unittest.mock import Mock

import minqlx
from experimental import uptime as experimental_uptime
from experimental.spec_rotation import color_format_team, damage_this_round, other_team, spec_rotation
from experimental.team_shots import team_shots


def test_spec_rotation_helpers():
    assert other_team("red") == "blue"
    assert other_team("blue") == "red"
    assert other_team("spectator") == "draw"
    assert color_format_team("red") == "^1red^7"
    assert color_format_team("blue") == "^4blue^7"
    assert color_format_team("draw") == "draw"
    assert damage_this_round({123: 5}, 123) == 5
    assert damage_this_round({}, 123) == 0


def test_spec_rotation_resets_state_and_removes_client_from_rotation():
    plugin = spec_rotation()
    plugin.spec_rotation = [123, 456]
    plugin.spec_rotation_plugin_is_enabled = lambda: True
    player = SimpleNamespace(steam_id=123, tell=Mock())

    plugin.handle_client_command(player, "team s")

    assert plugin.spec_rotation == [456]
    player.tell.assert_called_once()
    plugin.handle_map_change("map", "ca")
    assert plugin.spec_rotation == []


def test_spec_rotation_selects_player_with_fewest_games():
    plugin = spec_rotation()
    first = SimpleNamespace(steam_id=1)
    second = SimpleNamespace(steam_id=2)

    class Database(dict):
        exists = dict.__contains__

    plugin.database = Database
    plugin._db_instance = Database({"minqlx:players:1:games_completed": "5"})

    assert plugin.find_games_here(first) == 5
    assert plugin.find_games_here(second) == 0
    assert plugin.find_player_to_spec([first, second]) is second


def test_team_shots_resets_damage_state():
    plugin = team_shots()
    plugin.team_damages = {123: [(1, 20)]}

    plugin.handle_game_countdown()

    assert plugin.team_damages == {}


def test_experimental_uptime_sends_two_messages(monkeypatch):
    plugin = experimental_uptime.uptime()
    now = experimental_uptime.datetime.datetime(2025, 1, 1, 12, 0)
    monkeypatch.setattr(
        experimental_uptime.datetime,
        "datetime",
        SimpleNamespace(
            now=lambda: now,
            fromtimestamp=lambda _value: now,
        ),
    )
    monkeypatch.setattr(experimental_uptime.distro, "lsb_release_info", lambda: {"description": "Test OS"})
    monkeypatch.setattr(experimental_uptime.psutil, "boot_time", lambda: 0)
    monkeypatch.setattr(experimental_uptime.psutil, "Process", lambda _pid: SimpleNamespace(create_time=lambda: 0))
    monkeypatch.setattr(experimental_uptime.humanize, "precisedelta", lambda *_args, **_kwargs: "one minute")
    monkeypatch.setattr(experimental_uptime.platform, "python_version", lambda: "3.test")
    plugin.msg = Mock()

    plugin.cmd_uptime(None, [], minqlx.CHAT_CHANNEL)

    assert plugin.msg.call_count == 2
