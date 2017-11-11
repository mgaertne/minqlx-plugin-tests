from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from duelarena2 import *


class DuelArenaTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_game_in_warmup("ca")
        connected_players()
        self.plugin = duelarena()

    def tearDown(self):
        unstub()

    def test_when_no_running_game_allow_player_switch_attempt(self):
        switching_player = fake_player(1, "Switching Player")
        connected_players(switching_player)
        setup_no_game()

        return_code = self.plugin.handle_team_switch_event(switching_player, "red", "spectator")

        assert_that(return_code, is_(None))

    def test_when_player_tries_to_join_any_team_she_gets_added_to_playerset(self):
        switching_player = fake_player(1, "Switching Player")
        connected_players(switching_player)

        self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        self.assert_playerset_contains(switching_player)

    def assert_playerset_contains(self, *players):
        for player in players:
            assert_that(self.plugin.playerset, contains_inanyorder(player.steam_id))

    def test_when_third_player_tries_to_join_duelarena_gets_activated(self):
        switching_player = fake_player(3, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player,
                          blue_player,
                          switching_player)
        self.setup_duelarena_players(red_player, blue_player)
        self.deactivate_duelarena()

        self.plugin.handle_team_switch_event(switching_player, "spectator", "blue")

        self.assert_duelarena_activated()

    def setup_duelarena_players(self, *players):
        for player in players:
            self.plugin.playerset.append(player.steam_id)

    def assert_duelarena_activated(self):
        assert_that(self.plugin.duelmode, is_(True))

    def deactivate_duelarena(self):
        self.plugin.duelmode = False

    def test_when_red_player_switches_to_spec_she_is_removed_from_playerset(self):
        spec_player = fake_player(3, "Switching Player")
        switching_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(spec_player,
                          blue_player,
                          switching_player)
        self.setup_duelarena_players(switching_player, blue_player, spec_player)
        self.activate_duelarena()

        self.plugin.handle_team_switch_event(switching_player, "red", "spectator")

        self.assert_playerset_does_not_contain(switching_player)

    def activate_duelarena(self):
        self.plugin.duelmode = True

    def assert_playerset_does_not_contain(self, *players):
        for player in players:
            assert_that(self.plugin.playerset, not_(contains_inanyorder(player.steam_id)))
