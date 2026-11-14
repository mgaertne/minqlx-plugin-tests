from unittest.mock import Mock

import pytest
from minqlx_plugin_test import connected_players, death_data, fake_player
from mockito import unstub

import minqlx
from experimental.env_dmg import env_dmg


class TestEnvDamage:
    def teardown_method(self):
        unstub()

    def test_map_clears_recorded_damage(self):
        plugin = env_dmg()
        plugin.recorded_entity_dmg = {7: [(1, 2)]}

        plugin.handle_map("map", "ca")

        assert plugin.recorded_entity_dmg == {}

    @pytest.mark.usefixtures("game_in_progress")
    def test_environment_damage_tracks_entity_and_attributes_death(self, monkeypatch):
        plugin = env_dmg()
        attacker = fake_player(123, "Attacker", team="red")
        victim = fake_player(456, "Victim", team="blue")
        connected_players(attacker, victim)
        entity = 1234
        entities = iter(([entity], []))
        monkeypatch.setattr(minqlx, "get_targetting_entities", lambda _entity: next(entities), raising=False)
        monkeypatch.setattr(minqlx, "MOD_ROCKET", 2, raising=False)
        monkeypatch.setattr(plugin, "player", lambda steam_id: attacker if steam_id == attacker.steam_id else None)

        plugin.handle_damage(entity, attacker, 20, 0, minqlx.MOD_ROCKET)
        plugin.scan_targetting_entities(entity, minqlx.MOD_TRIGGER_HURT, 0)

        assert plugin.recorded_entity_dmg[entity][0][1] == attacker.steam_id

    @pytest.mark.usefixtures("game_in_progress")
    def test_environment_death_ignores_unattributed_and_non_environment_deaths(self, monkeypatch):
        plugin = env_dmg()
        victim = fake_player(456, "Victim", team="blue")
        msg = Mock()
        monkeypatch.setattr(plugin, "msg", msg)

        plugin.handle_death(victim, victim, death_data(MOD="HURT"))
        plugin.handle_death(victim, None, death_data(MOD="ROCKET"))

        msg.assert_not_called()

    def test_environment_scan_records_unique_recent_inflictor(self, monkeypatch):
        plugin = env_dmg()
        entity = 1234
        plugin.recorded_entity_dmg = {entity: [(100, 123)]}
        entities = iter(([entity], []))
        monkeypatch.setattr(
            minqlx,
            "get_targetting_entities",
            lambda _entity: next(entities),
            raising=False,
        )

        plugin.scan_targetting_entities(entity, 7, 200)

        assert plugin.means_of_death_watchlist[7] == 123

    def test_environment_death_reports_attributed_kill(self, monkeypatch):
        plugin = env_dmg()
        victim = fake_player(456, "Victim", team="blue")
        killer = fake_player(123, "Killer", team="red")
        monkeypatch.setattr(plugin, "player", lambda _steam_id: killer)
        plugin.means_of_death_watchlist[minqlx.MOD_TRIGGER_HURT] = killer.steam_id
        msg = Mock()
        monkeypatch.setattr(plugin, "msg", msg)

        plugin.handle_death(victim, None, death_data(MOD="HURT"))

        msg.assert_called_once()
