from types import SimpleNamespace

from minqlx_plugin_test import stand_in

import minqlx
from minqlx import Player
from team_shots import team_shots


class TestTeamShots:
    def test_damage_filters_non_game_and_invalid_events(self, monkeypatch, no_minqlx_game):
        plugin = team_shots()
        victim = stand_in(Player)
        attacker = stand_in(Player)
        plugin.handle_damage_event(victim, attacker, 50, 0, 1)
        monkeypatch.setattr(minqlx, "Game", lambda: SimpleNamespace(state="warmup"))
        plugin.handle_damage_event(victim, attacker, 50, 0, 1)

        assert plugin.team_damages == {}

    def test_game_countdown_resets_damage_state(self):
        plugin = team_shots()
        plugin.team_damages = {123: [(1, 20)]}

        plugin.handle_game_countdown()

        assert plugin.team_damages == {}
