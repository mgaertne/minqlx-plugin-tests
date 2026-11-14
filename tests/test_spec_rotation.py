from unittest.mock import Mock

from minqlx_plugin_test import stand_in, use_database

from minqlx import Player
from spec_rotation import color_format_team, damage_this_round, other_team, spec_rotation


def test_spec_rotation_helpers():
    assert other_team("red") == "blue"
    assert other_team("blue") == "red"
    assert other_team("spectator") == "draw"
    assert color_format_team("red") == "^1red^7"
    assert color_format_team("blue") == "^4blue^7"
    assert color_format_team("draw") == "draw"
    assert damage_this_round({123: 5}, 123) == 5
    assert damage_this_round({}, 123) == 0


def test_spec_rotation_resets_state_and_removes_client_from_rotation(monkeypatch):
    plugin = spec_rotation()
    plugin.spec_rotation = [123, 456]
    monkeypatch.setattr(plugin, "spec_rotation_plugin_is_enabled", lambda: True)
    tell = Mock()
    player = stand_in(Player, steam_id=123, tell=tell)

    plugin.handle_client_command(player, "team s")

    assert plugin.spec_rotation == [456]
    tell.assert_called_once()
    plugin.handle_map_change("map", "ca")
    assert plugin.spec_rotation == []


def test_spec_rotation_selects_player_with_fewest_games():
    plugin = spec_rotation()
    first = stand_in(Player, steam_id=1)
    second = stand_in(Player, steam_id=2)

    class Database(dict):
        exists = dict.__contains__

    use_database(plugin, Database({"minqlx:players:1:games_completed": "5"}), Database)

    assert plugin.find_games_here(first) == 5
    assert plugin.find_games_here(second) == 0
    assert plugin.find_player_to_spec([first, second]) is second
