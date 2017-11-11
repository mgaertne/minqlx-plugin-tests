from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from duelarena2 import *


class DuelArenaTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_game_in_progress("ca")
        connected_players()
        self.plugin = duelarena()
        self.activate_duelarena()

    def activate_duelarena(self):
        self.plugin.duelmode = True

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

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectator", "blue")

        self.assert_duelarena_activated()
        assert_player_was_told(switching_player,
                               "Server is now in ^6DuelArena^7 mode. You will automatically rotate with round loser.")
        assert_that(return_code, is_(minqlx.RET_STOP_ALL))

    def setup_duelarena_players(self, *players):
        for player in players:
            self.plugin.playerset.append(player.steam_id)

    def assert_duelarena_activated(self):
        assert_that(self.plugin.duelmode, is_(True))

    def deactivate_duelarena(self):
        self.plugin.duelmode = False

    def test_when_red_player_switches_to_spec_she_is_removed_from_playerset(self):
        switching_player = fake_player(1, "Switching Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
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

    def test_when_player_switch_to_spec_initiiated_by_plugin_clear_field(self):
        switching_player = fake_player(1, "Switching Player", "blue")
        red_player = fake_player(2, "Blue Player", "red")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(spec_player,
                          red_player,
                          switching_player)
        self.setup_duelarena_players(switching_player, red_player, spec_player)
        self.plugin.player_spec = switching_player.steam_id
        self.activate_duelarena()

        self.plugin.handle_team_switch_event(switching_player, "red", "spectator")

        assert_that(self.plugin.player_spec, is_(None))

    def test_when_game_in_warmup_announcement_is_shown(self):
        setup_game_in_warmup()
        switching_player = fake_player(3, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player,
                          blue_player,
                          switching_player)
        self.setup_duelarena_players(red_player, blue_player, switching_player)

        self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        assert_plugin_center_printed("Ready up for ^6DuelArena^7!")
        assert_plugin_sent_to_console(
            "Ready up for ^6DuelArena^7! Round winner stays in, loser rotates with spectator.")

    def test_when_game_in_warmup_with_too_few_players(self):
        setup_game_in_warmup()
        switching_player = fake_player(3, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player,
                          blue_player,
                          switching_player)
        self.setup_duelarena_players(red_player)

        self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        assert_plugin_center_printed("Ready up for ^6DuelArena^7!", times=0)
        assert_plugin_sent_to_console("Ready up for ^6DuelArena^7! Round winner stays in, loser rotates with spectator.", times=0)

    def test_when_duelarena_not_activated_allow_switch(self):
        switching_player = fake_player(3, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player,
                          blue_player,
                          switching_player)
        self.setup_duelarena_players(red_player)
        self.deactivate_duelarena()

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        assert_that(return_code, is_(None))

    def test_plugin_initiated_switch_to_red(self):
        switching_player = fake_player(1, "Switching Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "red")
        connected_players(switching_player,
                          blue_player,
                          spec_player)
        self.plugin.player_red = switching_player
        self.setup_duelarena_players(switching_player, blue_player, spec_player)

        self.plugin.handle_team_switch_event(switching_player, "spectator", "red")

        assert_that(self.plugin.player_red, is_(None))

    def test_plugin_initiated_switch_to_blue(self):
        red_player = fake_player(1, "Red Player", "red")
        switching_player = fake_player(2, "Switching Player")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player,
                          switching_player,
                          spec_player)
        self.plugin.player_blue = switching_player
        self.setup_duelarena_players(red_player, switching_player, spec_player)

        self.plugin.handle_team_switch_event(switching_player, "spectator", "blue")

        assert_that(self.plugin.player_blue, is_(None))

    def test_when_player_disconnects_she_gets_removed_from_playerset(self):
        red_player = fake_player(1, "Red Player", "red")
        disconnecting_player = fake_player(2, "Disconnecting Player")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player,
                          disconnecting_player,
                          spec_player)
        self.setup_duelarena_players(red_player, disconnecting_player, spec_player)

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_player_not_in_playerset_disconnects_nothing_happens(self):
        red_player = fake_player(1, "Red Player", "red")
        disconnecting_player = fake_player(2, "Disconnecting Player")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player,
                          disconnecting_player,
                          spec_player)
        self.setup_duelarena_players(red_player, spec_player)

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_playerset_does_not_contain(disconnecting_player)