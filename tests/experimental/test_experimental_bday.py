from datetime import datetime
from unittest.mock import Mock

from minqlx_plugin_test import fake_player

import minqlx
from experimental.bday import BDAY_KEY, bday


class TestBday:
    def test_cleaned_up_long_map_name(self):
        plugin = bday()

        assert plugin.cleaned_up_longmapname("Long Map-Name!") == "longmapname"

    def test_next_birthdate_moves_past_birthdays_to_next_year(self, monkeypatch):
        plugin = bday()
        monkeypatch.setattr("experimental.bday.datetime", Mock(now=lambda: datetime(2025, 6, 1)))

        assert plugin.next_birthdate(datetime(2000, 5, 31)).year == 2026
        assert plugin.next_birthdate(datetime(2000, 6, 15)).year == 2025

    def test_birthday_state_and_map_pick_limit(self):
        plugin = bday()
        player = fake_player(123, "Birthday Player")
        values = {BDAY_KEY.format(player.steam_id): "15.6."}

        class Database(dict):
            def __contains__(self, key):
                return key in values

            def __getitem__(self, key):
                return values[key]

        plugin._db_instance = Database()
        plugin.number_of_bday_maps = 1

        assert plugin.has_birthday_set(player)
        assert plugin.can_still_pick_bday_map(player)
        values[f"{BDAY_KEY.format(player.steam_id)}:{datetime.today().year}"] = "1"
        assert not plugin.can_still_pick_bday_map(player)

    def test_resolve_short_map_name_uses_installed_map_and_reports_ambiguity(self):
        plugin = bday()
        plugin._loaded_plugins = {"maps": Mock(logged_maps=["campgrounds", "camps"])}
        player = fake_player(123, "Player")
        player.tell = Mock()
        plugin._db_instance = Mock()
        plugin._db_instance.hgetall.return_value = {}

        assert plugin.resolve_short_mapname("campgrounds", player) == "campgrounds"
        assert plugin.resolve_short_mapname("camp", player) is None
        assert player.tell.call_count == 3

    def test_confirm_birthday_stores_pending_date(self):
        plugin = bday()
        player = fake_player(123, "Player")
        player.tell = Mock()
        plugin.pending_bday_confirmations[player.steam_id] = "1.1."
        plugin.database = dict
        plugin._db_instance = {}

        plugin.cmd_confirmbday(player, [], None)

        assert plugin._db_instance[BDAY_KEY.format(player.steam_id)] == "1.1."
        assert player.steam_id not in plugin.pending_bday_confirmations

    def test_confirm_birthday_without_pending_confirmation_notifies_player(self):
        plugin = bday()
        player = fake_player(123, "Player")
        player.tell = Mock()

        plugin.cmd_confirmbday(player, [], None)

        player.tell.assert_called_once()

    def test_bday_command_rejects_invalid_argument_count(self):
        plugin = bday()
        plugin.database = dict
        plugin._db_instance = {}
        player = fake_player(123, "Player")

        assert plugin.cmd_bday(player, ["!bday"], None) == minqlx.RET_USAGE
