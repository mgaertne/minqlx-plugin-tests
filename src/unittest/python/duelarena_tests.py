from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from duelarena import *


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
        player_ids = set(player.steam_id for player in players)
        assert_that(self.plugin.playerset, is_(player_ids))

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

        self.assert_duelarena_has_been_activated()
        assert_player_was_told(switching_player,
                               "Server is now in ^6DuelArena^7 mode. You will automatically rotate with round loser.")
        assert_that(return_code, is_(minqlx.RET_STOP_ALL))

    def setup_duelarena_players(self, *players):
        for player in players:
            self.plugin.playerset.add(player.steam_id)

    def assert_duelarena_has_been_activated(self):
        assert_that(self.plugin.duelmode, is_(True))
        assert_plugin_center_printed("DuelArena activated!")
        assert_plugin_sent_to_console(
            "DuelArena activated! Round winner stays in, loser rotates with spectator. Hit 8 rounds first to win!")

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

    def assert_playerset_does_not_contain(self, *players):
        for player in players:
            assert_that(self.plugin.playerset, not_(contains_inanyorder(player.steam_id)))

    def test_when_player_switches_to_spec_during_warmup_she_is_removed_from_queue(self):
        setup_game_in_warmup()
        switching_player = fake_player(2, "Switching Player", "blue")
        red_player = fake_player(1, "Red Player", "red")
        spec_player = fake_player(3, "Speccingg Player")
        connected_players(switching_player, red_player, spec_player)
        self.setup_duelarena_players(switching_player, red_player)
        self.activate_duelarena()

        self.plugin.handle_team_switch_event(switching_player, "blue", "spectator")

        self.assert_queue_does_not_contain(switching_player)

    def assert_queue_does_not_contain(self, *players):
        for player in players:
            assert_that(self.plugin.queue, not_(contains(player.steam_id)))

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
        assert_plugin_sent_to_console(
            "Ready up for ^6DuelArena^7! Round winner stays in, loser rotates with spectator.", times=0)

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

    def test_when_fifth_player_tries_to_join_in_forced_duelarena_duelarena_deactivates(self):
        switching_player = fake_player(5, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1")
        spec_player2 = fake_player(4, "Speccing Player2")
        connected_players(red_player, blue_player, spec_player1, spec_player2, switching_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2)
        self.queue_up_players(spec_player1, spec_player2)
        self.setup_forced_duelmode()

        self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        self.assert_playerset_contains(red_player, blue_player, spec_player1, spec_player2, switching_player)
        self.assert_queue_contains(spec_player1, spec_player2)

    def setup_forced_duelmode(self):
        self.plugin.duelarenastrategy = ForcedDuelArenaStrategy(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS)

    def test_when_sixth_player_tries_to_join_in_forced_duelarena_duelarena_deactivates(self):
        switching_player = fake_player(6, "Switching Player")
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1")
        spec_player2 = fake_player(4, "Speccing Player2")
        spec_player3 = fake_player(5, "Speccing Player3")
        connected_players(red_player, blue_player, spec_player1, spec_player2, spec_player3, switching_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2, spec_player3)
        self.queue_up_players(spec_player1, spec_player2, spec_player3)
        self.setup_forced_duelmode()

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectator", "any")

        assert_that(return_code, is_(None))
        self.assert_duelarena_has_been_deactivated()

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

    def test_handle_round_countdown_when_not_in_duelmode(self):
        self.deactivate_duelarena()

        return_code = self.plugin.handle_round_countdown(42)

        assert_that(return_code, is_(None))

    def test_handle_round_countdown_announces_matching_parties(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        speccing_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, speccing_player)
        self.setup_duelarena_players(red_player, blue_player, speccing_player)
        self.queue_up_players(speccing_player)

        self.plugin.handle_round_countdown(3)

        assert_plugin_center_printed("Red Player ^2vs^7 Blue Player")
        assert_plugin_sent_to_console("DuelArena: Red Player ^2vs^7 Blue Player")

    def queue_up_players(self, *players):
        for player in players:
            self.plugin.queue.insert(0, player.steam_id)

    def test_handle_round_countdown_with_one_team_empty(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "spectator")
        speccing_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, speccing_player)
        self.setup_duelarena_players(red_player, blue_player, speccing_player)
        self.queue_up_players(speccing_player)

        self.plugin.handle_round_countdown(3)

        assert_plugin_center_printed(any(str), times=0)
        assert_plugin_sent_to_console(any(str), times=0)

    def test_handle_round_countdown_when_duel_was_aborted(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "spectator")
        speccing_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, speccing_player)
        self.setup_duelarena_players(red_player, blue_player, speccing_player)
        self.queue_up_players(speccing_player)
        self.setup_scores({red_player: 5, blue_player: 2, speccing_player: 2})
        self.plugin.print_reset_scores = True

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console("DuelArena results:")
        assert_plugin_sent_to_console("Place ^31.^7 Red Player ^7(Wins:^25^7)")
        assert_plugin_sent_to_console("Place ^32.^7 Blue Player ^7(Wins:^22^7)")
        assert_plugin_sent_to_console("Place ^32.^7 Speccing Player ^7(Wins:^22^7)")

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
        self.activate_duelarena()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_in_duelarena_third_player_disconnects_duelarena_deactivates(self):
        red_player = fake_player(1, "Red Player", "red")
        disconnecting_player = fake_player(2, "Disconnecting Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, disconnecting_player, spec_player)
        self.setup_duelarena_players(red_player, disconnecting_player, spec_player)
        self.queue_up_players(spec_player)
        self.activate_duelarena()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_deactivated()

    def assert_duelarena_has_been_deactivated(self):
        assert_that(self.plugin.duelmode, is_(False))
        assert_that(self.plugin.initduel, is_(False))
        assert_plugin_center_printed("DuelArena deactivated!")
        assert_plugin_sent_to_console("DuelArena has been deactivated!")

    def test_when_not_in_duelarena_fourth_player_disconnects_duelarena_activates(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player, disconnecting_player)
        self.queue_up_players(spec_player, disconnecting_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_activated()
        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_not_in_duelarena_fourth_player_disconnects_duelarena_activates_during_warmup(self):
        setup_game_in_warmup()
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player, disconnecting_player)
        self.queue_up_players(spec_player, disconnecting_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_activated()
        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_not_in_duelarena_fifth_player_disconnects_duelarena_activates_with_forceduel(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1")
        spec_player2 = fake_player(5, "Speccing Player2")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player, spec_player1, spec_player2)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2, disconnecting_player)
        self.queue_up_players(spec_player1, disconnecting_player, spec_player2)
        self.deactivate_duelarena()
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_activated()
        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_not_in_duelarena_fifth_player_disconnects_duelarena_activates_with_forceduel_during_warmup(self):
        setup_game_in_warmup()
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1")
        spec_player2 = fake_player(5, "Speccing Player2")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player, spec_player1, spec_player2)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2, disconnecting_player)
        self.queue_up_players(spec_player1, disconnecting_player, spec_player2)
        self.deactivate_duelarena()
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_activated()
        self.assert_playerset_does_not_contain(disconnecting_player)

    def test_when_in_forced_duelarena_fourth_player_disconnects_duelarena_stays_activated(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player, disconnecting_player)
        self.queue_up_players(spec_player, disconnecting_player)
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        assert_that(self.plugin.duelmode, is_(True))

    def test_third_player_disconnects_duelarena_deactivates_with_forceduel(self):
        setup_game_in_progress(red_score=5, blue_score=3)
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        disconnecting_player = fake_player(3, "Disconnecting Player")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player, disconnecting_player)
        self.queue_up_players(disconnecting_player)
        self.setup_forced_duelmode()
        self.setup_scores({red_player: 7, blue_player: 5, disconnecting_player: 7})

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_deactivated()
        assert_that(self.plugin.print_reset_scores, is_(True))

    def test_third_player_disconnects_duelarena_deactivates_with_forceduel_during_warmup(self):
        setup_game_in_warmup()
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player, disconnecting_player)
        self.queue_up_players(disconnecting_player)
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        self.assert_duelarena_has_been_deactivated()
        assert_that(self.plugin.initduel, is_(False))

    def test_when_disconnecting_player_voted_remove_his_vote(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        disconnecting_player = fake_player(4, "Disconnecting Player")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player, disconnecting_player)
        self.queue_up_players(disconnecting_player)
        self.players_voted_for_duelarena(disconnecting_player)

        undecorated(self.plugin.handle_player_disco)(self.plugin, disconnecting_player, "ragequit")

        assert_that(self.plugin.duelvotes, not_(contains_inanyorder(disconnecting_player.steam_id)))

    def players_voted_for_duelarena(self, *players):
        for player in players:
            self.plugin.duelvotes.add(player.steam_id)

    def test_when_third_player_loaded_announce_duelarena_to_her(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        loaded_player = fake_player(3, "Loaded Player")
        connected_players(red_player, blue_player, loaded_player)
        self.setup_duelarena_players(red_player, blue_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, join to activate DuelArena! Round winner stays in, loser rotates with spectator.")

    def test_when_player_was_loaded_directly_on_team(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        loaded_player = fake_player(3, "Loaded Player", "red")
        connected_players(red_player, blue_player, loaded_player)
        self.setup_duelarena_players(red_player, blue_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, join to activate DuelArena! Round winner stays in, loser rotates with spectator.", times=0)

    def test_when_first_player_was_loaded(self):
        loaded_player = fake_player(4, "Loaded Player")
        connected_players(loaded_player)

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(loaded_player, any(str), times=0)

    def test_when_second_player_was_loaded(self):
        red_player = fake_player(1, "Red Player", "red")
        loaded_player = fake_player(3, "Loaded Player")
        connected_players(red_player, loaded_player)
        self.setup_duelarena_players(red_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, join to activate DuelArena! Round winner stays in, loser rotates with spectator.", times=0)

    def test_when_fourth_player_was_loaded(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "spectator")
        loaded_player = fake_player(4, "Loaded Player")
        connected_players(red_player, blue_player, spec_player, loaded_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.deactivate_duelarena()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, type ^6!duel^7 or ^6!d^7 to vote for DuelArena! Round winner stays in, loser rotates with "
            "spectator. Hit 8 rounds first to win!")

    def test_when_sixth_player_was_loaded(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1", "spectator")
        spec_player2 = fake_player(4, "Speccing Player2", "spectator")
        spec_player3 = fake_player(5, "Speccing Player3", "spectator")
        loaded_player = fake_player(6, "Loaded Player")
        connected_players(red_player, blue_player, spec_player1, spec_player2, spec_player3, loaded_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player1)
        self.queue_up_players(spec_player1)
        self.activate_duelarena()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(loaded_player, any(str), times=0)

    def test_when_fifth_player_is_loaded_during_running_forced_duelarena_that_just_started(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1", "spectator")
        spec_player2 = fake_player(3, "Speccing Player2", "spectator")
        loaded_player = fake_player(5, "Loaded Player")
        connected_players(red_player, blue_player, spec_player1, spec_player2, loaded_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2)
        self.queue_up_players(spec_player1, spec_player2)
        self.activate_duelarena()
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, DuelArena match is in progress. Join to enter DuelArena! Round winner stays in, loser "
            "rotates with spectator.")

    def test_when_fifth_player_is_loaded_during_running_forced_duelarena_may_be_aborted(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1", "spectator")
        spec_player2 = fake_player(4, "Speccing Player2", "spectator")
        loaded_player = fake_player(5, "Loaded Player")
        connected_players(red_player, blue_player, spec_player1, spec_player2, loaded_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player1, spec_player2)
        self.queue_up_players(spec_player1, spec_player2)
        self.setup_scores({red_player: 0, blue_player: 0, spec_player1: 2, spec_player2: 0})
        self.activate_duelarena()
        self.setup_forced_duelmode()

        undecorated(self.plugin.handle_player_loaded)(self.plugin, loaded_player)

        assert_player_was_told(
            loaded_player,
            "Loaded Player, by joining DuelArena will be aborted and server switches to standard CA!")

    def test_inits_duelmode_when_game_countdown_starts(self):
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)

        undecorated(self.plugin.handle_game_countdown)(self.plugin)

        assert_that(self.plugin.duelmode, is_(True))

    def test_deactivates_duelarena_when_game_countdown_starts_with_too_few_players(self):
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player)

        undecorated(self.plugin.handle_game_countdown)(self.plugin)

        self.assert_duelarena_has_been_deactivated()

    def test_does_nothing_when_game_countdown_starts_with_too_many_players(self):
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player1 = fake_player(3, "Speccing Player1")
        spec_player2 = fake_player(4, "Speccing Player2")

        connected_players(red_player, blue_player, spec_player1, spec_player2)
        self.setup_duelarena_players(red_player, blue_player)

        undecorated(self.plugin.handle_game_countdown)(self.plugin)

        self.assert_duelarena_has_been_deactivated()

    def test_handle_game_end_with_no_game_ending(self):
        setup_no_game()

        return_code = self.plugin.handle_game_end({})

        assert_that(return_code, is_(None))

    def test_handle_game_end_with_not_duelarena_active(self):
        self.deactivate_duelarena()

        return_code = self.plugin.handle_game_end({})

        assert_that(return_code, is_(None))

    def test_handle_game_end_red_team_wins_puts_winner_back_to_queue(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)

        self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 3})

        self.assert_queue_contains(red_player, spec_player, blue_player)

    def assert_queue_contains(self, *players):
        player_ids = [player.steam_id for player in players]
        player_ids.reverse()
        assert_that(self.plugin.queue, is_(player_ids))

    def test_handle_game_end_blue_team_wins_puts_winner_back_to_queue(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)

        self.plugin.handle_game_end({"TSCORE0": 2, "TSCORE1": 8})

        self.assert_queue_contains(blue_player, spec_player, red_player)

    def test_handle_game_end_prints_results(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 7, blue_player: 5, spec_player: 7})

        self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 3})

        assert_plugin_sent_to_console("DuelArena results:")
        assert_plugin_sent_to_console("Place ^31.^7 Red Player ^7(Wins:^28^7)")
        assert_plugin_sent_to_console("Place ^32.^7 Speccing Player ^7(Wins:^27^7)")
        assert_plugin_sent_to_console("Place ^33.^7 Blue Player ^7(Wins:^25^7)")

    def setup_scores(self, scores):
        for player in scores.keys():
            self.plugin.scores[player.steam_id] = scores[player]

    def test_handle_game_end_winner_already_quit(self):
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(blue_player, spec_player)
        self.setup_duelarena_players(fake_player(1, "Red Player", "red"), blue_player, spec_player)
        self.queue_up_players(spec_player)

        return_code = self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 3})

        assert_that(return_code, is_(None))

    def test_handle_game_end_winner_already_quit_with_scores(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 7, blue_player: 5, spec_player: 6})

        self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 3})

        assert_plugin_sent_to_console("DuelArena results:")
        assert_plugin_sent_to_console("Place ^31.^7 <Player disconnected> ^7(Wins:^27^7)")
        assert_plugin_sent_to_console("Place ^32.^7 Speccing Player ^7(Wins:^26^7)")
        assert_plugin_sent_to_console("Place ^33.^7 Blue Player ^7(Wins:^25^7)")

    def test_handle_game_end_loser_already_quit(self):
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(blue_player, spec_player)
        self.setup_duelarena_players(fake_player(1, "Red Player", "red"), blue_player, spec_player)
        self.queue_up_players(spec_player)

        return_code = self.plugin.handle_game_end({"TSCORE0": 6, "TSCORE1": 8})

        assert_that(return_code, is_(None))

    def test_handle_round_end_with_no_game(self):
        setup_no_game()

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "DRAW"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_with_wrong_gametype(self):
        setup_game_in_progress("ft")

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "DRAW"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_with_red_team_hit_roundlimit(self):
        setup_game_in_progress(roundlimit=8, red_score=8, blue_score=4)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_with_blue_team_hit_roundlimit(self):
        setup_game_in_progress(roundlimit=8, red_score=3, blue_score=8)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_inits_duelarena(self):
        setup_game_in_progress(red_score=5, blue_score=7)
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_that(self.plugin.duelmode, is_(True))
        assert_that(self.plugin.initduel, is_(False))
        self.assert_scores_are({red_player: 0, blue_player: 0, spec_player: 0})
        assert_game_addteamscore("red", -5)
        assert_game_addteamscore("blue", -7)

    def test_handle_round_end_puts_playerset_to_queue_if_not_enqueued(self):
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        self.assert_queue_contains(spec_player)

    def test_handle_round_end_puts_specs_on_teams_to_spec(self):
        red_player = fake_player(1, "Red Player" "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(spec_player, "spectator")

    def test_handle_round_end_players_already_on_correct_teams(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, any(str), times=0)
        assert_player_was_put_on(blue_player, any(str), times=0)

    def test_handle_round_end_players_already_on_opposing_teams(self):
        red_player = fake_player(1, "Red Player", "blue")
        blue_player = fake_player(2, "Blue Player", "red")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, any(str), times=0)
        assert_player_was_put_on(blue_player, any(str), times=0)

    def test_handle_round_end_both_players_on_red(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "red")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, any(str), times=0)
        assert_player_was_put_on(blue_player, "blue")

    def test_handle_round_end_just_red_player_on_blue_team(self):
        red_player = fake_player(1, "Red Player", "blue")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "red")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, any(str), times=0)
        assert_player_was_put_on(blue_player, "red")

    def test_handle_round_end_just_blue_player_on_blue_team_red_on_spec(self):
        red_player = fake_player(1, "Red Player", "spectator")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "red")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, "red")
        assert_player_was_put_on(blue_player, any(str), times=0)

    def test_handle_round_end_just_blue_player_on_red_team_red_on_spec(self):
        red_player = fake_player(1, "Red Player", "spectator")
        blue_player = fake_player(2, "Blue Player", "red")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, "blue")
        assert_player_was_put_on(blue_player, any(str), times=0)

    def test_handle_round_end_both_players_on_spec(self):
        red_player = fake_player(1, "Red Player", "spectator")
        blue_player = fake_player(2, "Blue Player", "spectator")
        spec_player = fake_player(3, "Speccing Player", "blue")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(red_player, blue_player, spec_player)
        self.plugin.initduel = True

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_player_was_put_on(red_player, "red")
        assert_player_was_put_on(blue_player, "blue")

    def test_handle_round_end_with_no_duelarena_active(self):
        self.deactivate_duelarena()

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_with_a_draw(self):
        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "DRAW"})

        assert_that(return_code, is_(None))

    def test_handle_round_end_red_player_won_stores_red_score(self):
        setup_game_in_progress(red_score=6, blue_score=3)
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 5, blue_player: 3, spec_player: 7})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        self.assert_scores_are({red_player: 6, blue_player: 3, spec_player: 7})

    def assert_scores_are(self, scores):
        scores_with_steam_ids = {player.steam_id: value for player, value in scores.items()}
        assert_that(self.plugin.scores, is_(scores_with_steam_ids))

    def test_handle_round_end_blue_player_won_stores_blue_score(self):
        setup_game_in_progress(red_score=5, blue_score=4)
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 5, blue_player: 3, spec_player: 7})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "BLUE"})

        self.assert_scores_are({red_player: 5, blue_player: 4, spec_player: 7})

    def test_handle_round_end_next_player_already_on_team(self):
        setup_game_in_progress(red_score=6, blue_score=3)
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player", "red")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 5, blue_player: 3, spec_player: 7})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        self.assert_duelarena_has_been_deactivated()

    def test_handle_round_end_red_player_won_puts_switching_queued_player_to_losing_team(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 5, blue_player: 3, spec_player: 7})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_player_was_put_on(spec_player, "blue")
        assert_player_was_put_on(blue_player, "spectator")
        assert_player_was_told(
            blue_player, "Blue Player, you've been put back to DuelArena queue. Prepare for your next duel!")
        self.assert_queue_contains(blue_player)

    def test_handle_round_end_red_player_won_puts_blue_player_on_spec(self):
        setup_game_in_progress(red_score=6, blue_score=3)
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        spec_player = fake_player(3, "Speccing Player")
        connected_players(red_player, blue_player, spec_player)
        self.setup_duelarena_players(red_player, blue_player, spec_player)
        self.queue_up_players(spec_player)
        self.setup_scores({red_player: 5, blue_player: 3, spec_player: 7})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_game_addteamscore("blue", 4)

    def test_handle_round_end_when_player_queue_empty_duelarena_is_deactivated(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player)
        self.setup_scores({red_player: 5, blue_player: 3})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        self.assert_duelarena_has_been_deactivated()

    def test_handle_round_end_when_next_player_no_longer_available(self):
        red_player = fake_player(1, "Red Player", "red")
        blue_player = fake_player(2, "Blue Player", "blue")
        connected_players(red_player, blue_player)
        self.setup_duelarena_players(red_player, blue_player)
        self.queue_up_players(fake_player(42, "no longer connected Player"))
        self.setup_scores({red_player: 5, blue_player: 3})

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        self.assert_duelarena_has_been_deactivated()

    def test_handle_map_change_resets_duelarena(self):
        self.setup_forced_duelmode()
        self.players_voted_for_duelarena(fake_player(42, "Fake Player"))
        self.plugin.duelmode = True
        self.plugin.initduel = True

        self.plugin.handle_map_change("TheatreOfPain", None)

        assert_that(self.plugin.duelarenastrategy, instance_of(AutoDuelArenaStrategy))
        assert_that(self.plugin.duelvotes, is_(set()))
        assert_that(self.plugin.duelmode, is_(False))
        assert_that(self.plugin.initduel, is_(False))

    def test_cmd_duelarena_wrong_usage_in_auto_state(self):
        return_code = self.plugin.cmd_duelarena(None, "!duelarena", None)

        assert_that(return_code, is_(minqlx.RET_USAGE))
        assert_plugin_sent_to_console("Current DuelArena state is: ^6auto")

    def test_cmd_duelarena_invalid_parameter_in_force_state(self):
        self.setup_forced_duelmode()

        return_code = self.plugin.cmd_duelarena(None, "!duelarena asdf", None)

        assert_that(return_code, is_(minqlx.RET_USAGE))
        assert_plugin_sent_to_console("Current DuelArena state is: ^6force")

    def test_cmd_duelarena_set_to_forced(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        connected_players(
            voting_player,
            fake_player(2, "Fake Player"),
            fake_player(3, "Fake Player"),
            fake_player(4, "Fake Player"))
        self.plugin.cmd_duelarena(None, ["!duelarena", "force"], None)

        assert_plugin_sent_to_console("^7Duelarena is now ^6forced^7!")
        assert_that(self.plugin.duelarenastrategy, instance_of(ForcedDuelArenaStrategy))

    def test_cmd_duelarena_set_to_automatic(self):
        self.plugin.forceduel = True
        self.plugin.cmd_duelarena(None, ["!duelarena", "auto"], None)

        assert_plugin_sent_to_console("^7Duelarena is now ^6automatic^7!")
        assert_that(self.plugin.duelarenastrategy, instance_of(AutoDuelArenaStrategy))

    def test_cmd_duel_when_duelarena_already_running(self):
        self.plugin.cmd_duel(None, "!d", None)

        assert_plugin_sent_to_console("^7DuelArena already active!")

    def test_cmd_duel_not_during_warmup(self):
        self.deactivate_duelarena()

        self.plugin.cmd_duel(None, "!d", None)

        assert_plugin_sent_to_console("^7DuelArena votes only allowed in warmup!")

    def test_cmd_duel_with_too_few_connected_players(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        connected_players(
            voting_player,
            fake_player(2, "Fake Player"))

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^6!duel^7 votes only available with ^63-4^7 players connected")

    def test_cmd_duel_with_too_many_connected_players(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        connected_players(
            voting_player,
            fake_player(2, "Fake Player"),
            fake_player(3, "Fake Player"),
            fake_player(4, "Fake Player"),
            fake_player(5, "Fake Player"),
            fake_player(6, "Fake Player"))

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^6!duel^7 votes only available with ^63-4^7 players connected")

    def test_cmd_duel_player_already_voted(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        connected_players(
            voting_player,
            fake_player(2, "Fake Player"),
            fake_player(3, "Fake Player"))
        self.players_voted_for_duelarena(voting_player)

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("Voting Player^7 you already voted for DuelArena!")

    def test_cmd_duel_first_player_votes(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        connected_players(
            voting_player,
            fake_player(2, "Fake Player"),
            fake_player(3, "Fake Player"),
            fake_player(4, "Fake Player"))

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^7Total DuelArena votes = ^61^7, but I need ^62^7 more to activate DuelArena.")
        self.assert_players_voted(voting_player)

    def assert_players_voted(self, *players):
        player_ids = [player.steam_id for player in players]
        assert_that(self.plugin.duelvotes, contains_inanyorder(*player_ids))

    def test_cmd_duel_second_player_of_four_votes(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        voted_player1 = fake_player(2, "Fake Player")
        connected_players(
            voting_player,
            voted_player1,
            fake_player(3, "Fake Player"),
            fake_player(4, "Fake Player"))
        self.players_voted_for_duelarena(voted_player1)

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^7Total DuelArena votes = ^62^7, but I need ^61^7 more to activate DuelArena.")
        self.assert_players_voted(voting_player, voted_player1)

    def test_cmd_duel_third_player_of_four_votes_and_vote_passes(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        voted_player1 = fake_player(2, "Fake Player")
        voted_player2 = fake_player(3, "Fake Player")
        connected_players(
            voting_player,
            voted_player1,
            voted_player2,
            fake_player(4, "Fake Player"))
        self.players_voted_for_duelarena(voted_player1, voted_player2)

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^7Total DuelArena votes = ^63^7, vote passed!")
        self.assert_players_voted(voting_player, voted_player1, voted_player2)

    def test_cmd_duel_vote_passes(self):
        setup_game_in_warmup()
        self.deactivate_duelarena()
        voting_player = fake_player(1, "Voting Player")
        voted_player1 = fake_player(2, "Fake Player")
        voted_player2 = fake_player(3, "Fake Player")
        connected_players(
            voting_player,
            voted_player1,
            voted_player2,
            fake_player(4, "Fake Player"))
        self.setup_duelarena_players(voted_player1, voted_player2, voting_player)
        self.players_voted_for_duelarena(voted_player1, voted_player2)

        self.plugin.cmd_duel(voting_player, "!d", None)

        assert_plugin_sent_to_console("^7Total DuelArena votes = ^63^7, vote passed!")
        assert_plugin_played_sound("sound/vo/vote_passed.ogg")
        assert_that(self.plugin.duelarenastrategy, instance_of(ForcedDuelArenaStrategy))
        self.assert_duelarena_has_been_activated()

    def test_check_abort_with_game_in_warmup(self):
        setup_game_in_warmup()

        assert_that(self.plugin.duelarena_should_be_aborted(
            self.plugin.game,
            self.plugin.playerset,
            self.plugin.scores
        ), is_(False))

    def test_check_abort_with_just_right_connected_players(self):
        self.setup_duelarena_players(
            fake_player(1, "Fake Player"), fake_player(2, "Fake Player"), fake_player(3, "Fake Player"))

        assert_that(self.plugin.duelarena_should_be_aborted(
            self.plugin.game,
            self.plugin.playerset,
            self.plugin.scores
        ), is_(False))

    def test_check_abort_with_too_many_players_already_played_a_bit(self):
        player1 = fake_player(1, "Fake Player")
        player2 = fake_player(2, "Fake Player")
        player3 = fake_player(3, "Fake Player")
        player4 = fake_player(4, "Fake Player")
        player5 = fake_player(5, "Fake Player")
        self.setup_duelarena_players(player1, player2, player3, player4, player5)
        self.setup_scores({player1: 6, player2: 6, player3: 7, player4: 3})

        assert_that(self.plugin.duelarena_should_be_aborted(
            self.plugin.game,
            self.plugin.playerset,
            self.plugin.scores
        ), is_(False))

    def test_check_abort_with_too_many_players_already_not_played_enough(self):
        player1 = fake_player(1, "Fake Player")
        player2 = fake_player(2, "Fake Player")
        player3 = fake_player(3, "Fake Player")
        player4 = fake_player(4, "Fake Player")
        player5 = fake_player(5, "Fake Player")
        self.setup_duelarena_players(player1, player2, player3, player4, player5)
        self.setup_duelarena_players(player1, player2, player3, player4)
        self.setup_scores({player1: 2, player2: 3, player3: 5, player4: 3})

        assert_that(self.plugin.duelarena_should_be_aborted(
            self.plugin.game,
            self.plugin.playerset,
            self.plugin.scores
        ), is_(True))
