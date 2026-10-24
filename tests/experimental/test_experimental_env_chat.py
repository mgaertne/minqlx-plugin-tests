from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from minqlx_plugin_test import connected_players, fake_player
from mockito import unstub

import minqlx
from experimental.chat_fraggers import chat_fraggers
from experimental.env_dmg import env_dmg
from experimental.team_shots import team_shots


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
        entity = object()
        entities = iter(([entity], []))
        monkeypatch.setattr(minqlx, "get_targetting_entities", lambda _entity: next(entities), raising=False)
        monkeypatch.setattr(minqlx, "MOD_HURT", 1, raising=False)
        monkeypatch.setattr(minqlx, "MOD_ROCKET", 2, raising=False)
        plugin.player = lambda steam_id: attacker if steam_id == attacker.steam_id else None

        plugin.handle_damage(entity, attacker, 20, 0, minqlx.MOD_ROCKET)
        plugin.scan_targetting_entities(entity, minqlx.MOD_HURT, 0)

        assert plugin.recorded_entity_dmg[entity][0][1] == attacker.steam_id

    @pytest.mark.usefixtures("game_in_progress")
    def test_environment_death_ignores_unattributed_and_non_environment_deaths(self):
        plugin = env_dmg()
        victim = fake_player(456, "Victim", team="blue")
        plugin.msg = Mock()

        plugin.handle_death(victim, victim, {"MOD": "HURT"})
        plugin.handle_death(victim, None, {"MOD": "ROCKET"})

        plugin.msg.assert_not_called()

    def test_environment_scan_records_unique_recent_inflictor(self, monkeypatch):
        plugin = env_dmg()
        entity = object()
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

    def test_environment_death_reports_attributed_kill(self):
        plugin = env_dmg()
        victim = fake_player(456, "Victim", team="blue")
        killer = fake_player(123, "Killer", team="red")
        plugin.player = lambda _steam_id: killer
        plugin.means_of_death_watchlist[1] = killer.steam_id
        plugin.msg = Mock()
        original = getattr(minqlx, "MOD_HURT", 1)
        minqlx.MOD_HURT = original

        plugin.handle_death(victim, None, {"MOD": "HURT"})

        plugin.msg.assert_called_once()


class TestChatFraggers:
    def teardown_method(self):
        unstub()

    @pytest.mark.usefixtures("game_in_progress")
    def test_damage_to_chatting_enemy_warns_below_threshold(self):
        attacker = fake_player(123, "Attacker", team="red")
        attacker.center_print = Mock()
        from experimental.chat_fraggers import warn_player

        warn_player(attacker, "warning")

        assert attacker.center_print.call_count == 1

    def test_round_countdown_resets_tracker(self):
        plugin = chat_fraggers()
        plugin.chat_tracker = {1: {2: 3}}
        plugin.handle_round_countdown(2)
        assert plugin.chat_tracker == {}

    def test_damage_event_ignores_missing_game(self, no_minqlx_game):
        plugin = chat_fraggers()
        assert plugin.handle_damage_event(object(), object(), 1, 0, 0) is None

    def test_kill_event_ignores_untracked_or_non_chatting(self, game_in_progress):
        plugin = chat_fraggers()
        victim = fake_player(2, "Victim", team="blue")
        killer = fake_player(1, "Killer", team="red")
        victim.state = SimpleNamespace(is_chatting=False)
        plugin.handle_kill(victim, killer, {})
        assert plugin.chat_tracker == {}


class TestTeamShots:
    def test_damage_filters_non_game_and_invalid_events(self, monkeypatch, no_minqlx_game):
        plugin = team_shots()
        assert plugin.handle_damage_event(object(), object(), 50, 0, 1) is None
        monkeypatch.setattr(minqlx, "Game", lambda: SimpleNamespace(state="warmup"))
        assert plugin.handle_damage_event(object(), object(), 50, 0, 1) is None

    @pytest.mark.usefixtures("game_in_progress")
    def test_damage_reaching_threshold_punishes_attacker(self):
        attacker = fake_player(123, "Attacker", team="red")
        attacker.health = 100
        attacker.armor = 50
        attacker.weapons = Mock()
        attacker.weapon = Mock()
        attacker.center_print = Mock()
        from experimental.chat_fraggers import punish_player

        punish_player(attacker, "punish")

        assert attacker.health == 1
        assert attacker.armor == 0
        assert attacker.weapon.call_count == 1

    @pytest.mark.usefixtures("game_in_progress")
    def test_kill_of_chatting_player_warns_or_punishes_from_tracked_damage(self):
        plugin = chat_fraggers()
        plugin.punishment_threshold = 10
        attacker = fake_player(123, "Attacker", team="red")
        target = fake_player(456, "Chatter", team="blue")
        target.state = SimpleNamespace(is_chatting=True)
        attacker.center_print = Mock()
        connected_players(attacker, target)
        plugin.chat_tracker = {attacker.steam_id: {target.steam_id: 5}}

        plugin.handle_kill(target, attacker, {})

        assert attacker.center_print.call_count == 1
