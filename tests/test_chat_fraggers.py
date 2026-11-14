from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from minqlx_plugin_test import connected_players, fake_player, kill_data, stand_in
from mockito import unstub

from chat_fraggers import chat_fraggers, punish_player, warn_player
from minqlx import Player


class TestChatFraggers:
    def teardown_method(self):
        unstub()

    @pytest.mark.usefixtures("game_in_progress")
    def test_damage_to_chatting_enemy_warns_below_threshold(self):
        attacker = fake_player(123, "Attacker", team="red")
        attacker.center_print = Mock()

        warn_player(attacker, "warning")

        assert attacker.center_print.call_count == 1

    def test_round_countdown_resets_tracker(self):
        plugin = chat_fraggers()
        plugin.chat_tracker = {1: {2: 3}}
        plugin.handle_round_countdown(2)
        assert plugin.chat_tracker == {}

    def test_damage_event_ignores_missing_game(self, no_minqlx_game):
        plugin = chat_fraggers()
        plugin.handle_damage_event(stand_in(Player), stand_in(Player), 1, 0, 0)

        assert plugin.chat_tracker == {}

    def test_kill_event_ignores_untracked_or_non_chatting(self, game_in_progress):
        plugin = chat_fraggers()
        victim = fake_player(2, "Victim", team="blue")
        killer = fake_player(1, "Killer", team="red")
        victim.state = SimpleNamespace(is_chatting=False)
        plugin.handle_kill(victim, killer, kill_data())
        assert plugin.chat_tracker == {}

    @pytest.mark.usefixtures("game_in_progress")
    def test_punishment_strips_armor_health_and_weapons(self):
        attacker = fake_player(123, "Attacker", team="red")
        attacker.health = 100
        attacker.armor = 50
        attacker.weapons = Mock()
        attacker.weapon = Mock()
        attacker.center_print = Mock()

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

        plugin.handle_kill(target, attacker, kill_data())

        assert attacker.center_print.call_count == 1
