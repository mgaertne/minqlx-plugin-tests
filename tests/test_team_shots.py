from types import SimpleNamespace

import minqlx
from team_shots import team_shots


class TestTeamShots:
    def test_damage_filters_non_game_and_invalid_events(self, monkeypatch, no_minqlx_game):
        plugin = team_shots()
        assert plugin.handle_damage_event(object(), object(), 50, 0, 1) is None
        monkeypatch.setattr(minqlx, "Game", lambda: SimpleNamespace(state="warmup"))
        assert plugin.handle_damage_event(object(), object(), 50, 0, 1) is None

    def test_game_countdown_resets_damage_state(self):
        plugin = team_shots()
        plugin.team_damages = {123: [(1, 20)]}

        plugin.handle_game_countdown()

        assert plugin.team_damages == {}
