from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

class TestDuelArena(unittest.TestCase):

    def setUp(self):
        self.plugin = duelarena()
        setup_plugin(self.plugin)
        setup_game_in_progress()
        self.activate_duelarena_mode()

    def tearDown(self):
        unstub()

    def subscribe_players(self, *players):
        for player in players:
            self.plugin.psub.insert(0, player.steam_id)

    def add_players_to_queue(self, *players):
        for player in players:
            self.plugin.queue.insert(0, player.steam_id)

    def deactivate_duelarena_mode(self):
        self.plugin.duelmode = False

    def activate_duelarena_mode(self):
        self.plugin.duelmode = True

    def activate_init_duelarena_mode(self):
        self.plugin.initmode = True

    def assert_duelarena_deactivated(self):
        assert_that(self.plugin.duelmode, is_(False), "DuelArena should have been deactivated, but was activated")

    def assert_duelarena_activated(self):
        assert_that(self.plugin.duelmode, is_(True), "DuelArena should have been activated, but was deactivated")

    def assert_duelarena_about_to_initialize(self):
        assert_that(self.plugin.initduel, is_(True), "DuelArena should have been set for initialization, but was not")

    def assert_duelarena_finished_to_initialize(self):
        assert_that(self.plugin.initduel, is_(False), "DuelArena should not have been set for initialization, but was")

    def assert_subscribed_players(self, *players):
        steam_ids = [player.steam_id for player in players]
        assert_that(self.plugin.psub, contains_inanyorder(*steam_ids))

    def assert_player_queue(self, *players):
        steam_ids = [player.steam_id for player in players]
        steam_ids.reverse()
        assert_that(self.plugin.queue, is_(steam_ids))

    def test_enqueue_players(self):
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3")
        self.add_players_to_queue(player1, player2, player3)

        self.assert_player_queue(player1, player2, player3)

    def test_switch_player_with_no_duelmode_active(self):
        self.deactivate_duelarena_mode()

        return_code = self.plugin.handle_team_switch_event(fake_player(123, "Fake Player"), "don't care",
                                                           "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_with_no_active_game(self):
        setup_no_game()

        return_code = self.plugin.handle_team_switch_event(fake_player(123, "Fake Player"), "don't care", "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_with_no_game_in_warmup(self):
        setup_game_in_warmup()

        return_code = self.plugin.handle_team_switch_event(fake_player(123, "Fake Player"), "don't care", "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_to_red_initiated_by_plugin(self):
        self.plugin.switching_player1 = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(self.plugin.switching_player1, "don't care", "don't care")

        assert_that(self.plugin.switching_player1, is_(None))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_to_blue_initiated_by_plugin(self):
        self.plugin.switching_player2 = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(self.plugin.switching_player2, "don't care", "don't care")

        assert_that(self.plugin.switching_player2, is_(None))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_unallowed_switch_from_spec_to_red(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player, "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_spec_to_blue(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player, "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_blue_to_red(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "blue", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player, "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_red_to_blue(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "red", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player, "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_2nd_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(2, "Player 2")
        connected_players(self.plugin, fake_player(1, "Player 1"), connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        self.assert_duelarena_deactivated()

    def test_3rd_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(3, "Player 3")
        connected_players(self.plugin, fake_player(1, "Player 1"), fake_player(2, "Player 2"), connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_4th_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          fake_player(1, "Player 1"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3"),
                          connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, ANY(str), times=0)
        assert_plugin_center_printed(self.plugin, ANY(str), times=0)
        self.assert_duelarena_deactivated()

    def test_5th_player_connects_when_duelarena_deactivated(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          fake_player(1, "Player 1"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3"),
                          fake_player(4, "Player 4"),
                          connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_5th_player_connects_when_duelarena_activated(self):
        connecting_player = fake_player(5, "Player 5")
        player1 = fake_player(1, "Player 1")
        player3 = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          player1,
                          fake_player(2, "Player 2"),
                          player3,
                          player4,
                          connecting_player)
        self.subscribe_players(player1, player3, player4)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, any(str), times=0)
        assert_plugin_center_printed(self.plugin, any(str), times=0)
        self.assert_duelarena_activated()

    def test_6th_player_connects_when_duelarena_activated(self):
        connecting_player = fake_player(5, "Player 5")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player6 = fake_player(6, "Player 6")
        connected_players(self.plugin,
                          player1,
                          player2,
                          fake_player(3, "Player 3"),
                          fake_player(4, "Player 4"),
                          connecting_player,
                          player6)
        self.subscribe_players(player1, player6, player2)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "DuelArena has been deactivated! You are free to join.")
        assert_plugin_center_printed(self.plugin, ANY(str), times=0)
        self.assert_duelarena_deactivated()

    def test_6th_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(6, "Player 6")
        connected_players(self.plugin,
                          fake_player(1, "Player 1"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3"),
                          fake_player(4, "Player 4"),
                          fake_player(5, "Player 5"),
                          connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, ANY(str), times=0)
        assert_plugin_center_printed(self.plugin, ANY(str), times=0)
        self.assert_duelarena_deactivated()

    def test_handle_round_count_when_duelarena_activated(self):
        connected_players(self.plugin,
                          fake_player(1, "Player 1", team="blue"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3", team="red"),
                          fake_player(4, "Player 4"))

        self.plugin.handle_round_countdown()

        assert_plugin_center_printed(self.plugin, "Player 3 ^2vs Player 1")

    def test_handle_round_count_when_duelarena_deactivated(self):
        self.deactivate_duelarena_mode()
        connected_players(self.plugin,
                          fake_player(1, "Player 1", team="blue"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3", team="red"),
                          fake_player(4, "Player 4"))

        self.plugin.handle_round_countdown()

        assert_plugin_center_printed(self.plugin, ANY(str), times=0)

    def test_handle_player_disconnect_broadcast_when_minimum_players_are_left(self):
        self.deactivate_duelarena_mode()
        connected_players(self.plugin,
                          fake_player(1, "Player 1", team="blue"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3", team="red"))

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_handle_player_disconnect_deactivates_duelarena(self):
        player1 = fake_player(1, "Player 1", team="blue")
        player2 = fake_player(2, "Player 2")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          player1,
                          player2,
                          fake_player(3, "Player 3", team="red"))
        self.subscribe_players(player1, player2, player4)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "DuelArena has been deactivated! You are free to join.")
        self.assert_duelarena_deactivated()
        self.assert_subscribed_players(player2, player1)

    def test_handle_player_disconnect_activates_duelarena(self):
        player1 = fake_player(1, "Player 1", team="blue")
        player2 = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3", team="red")
        player4 = fake_player(4, "Player 4")
        player6 = fake_player(6, "Player 6")
        self.deactivate_duelarena_mode()
        connected_players(self.plugin,
                          player1,
                          player2,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(player1, player2, player6, player3, player4)
        self.add_players_to_queue(player1, player2, player6, player3, player4)
        when2(self.plugin.player, 6).thenReturn(None)

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "DuelArena activated!")
        assert_plugin_center_printed(self.plugin, "DuelArena activated!")
        self.assert_duelarena_activated()
        self.assert_duelarena_about_to_initialize()
        self.assert_subscribed_players(player1, player2, player3, player4)
        self.assert_player_queue(player1, player2, player3, player4)

    def test_handle_player_disconnect_broadcasts_duelarena(self):
        self.deactivate_duelarena_mode()
        connected_players(self.plugin,
                          fake_player(1, "Player 1", team="blue"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3", team="red"),
                          fake_player(4, "Player 4"),
                          fake_player(5, "Player 5"))

        self.plugin.undelayed_handle_player_connected_or_disconnected()

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_game_countdown_inits_duelarena_when_activated_and_moved_players_to_right_teams(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2")
        speccing_player = fake_player(3, "Player 3", team="red")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, speccing_player, player4)
        self.add_players_to_queue(red_player, blue_player, speccing_player, player4)

        self.plugin.undelayed_handle_game_countdown()

        assert_that(self.plugin.switching_player1, is_(red_player))
        assert_that(self.plugin.switching_player2, is_(blue_player))
        assert_player_was_put_on(blue_player, "red")
        assert_player_was_put_on(speccing_player, "spectator")
        self.assert_duelarena_finished_to_initialize()
        self.assert_player_queue(speccing_player, player4)

    def test_game_countdown_inits_duelarena_when_activated_and_keeps_red_player_on_red_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        player3 = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(player4, player3, blue_player, red_player)

        self.plugin.undelayed_handle_game_countdown()

        assert_that(self.plugin.switching_player1, is_(red_player))
        assert_that(self.plugin.switching_player2, is_(blue_player))
        assert_player_was_put_on(blue_player, any_team, times=0)
        self.assert_duelarena_finished_to_initialize()
        self.assert_player_queue(player3, player4)

    def test_move_players_to_teams_players_already_on_right_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, any_team, times=0)

    def test_move_players_to_teams_players_on_opposing_teams(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="red")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, any_team, times=0)

    def test_move_players_to_teams_players_on_blue_team(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="blue")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, "red")

    def test_move_players_to_teams_players_on_red_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, "blue")

    def test_move_players_to_teams_one_player_speccing(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", "spectator")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, "blue")

    def test_move_players_to_teams_both_players_speccing(self):
        red_player = fake_player(1, "Player 1", "spectator")
        blue_player = fake_player(2, "Player 2", "spectator")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        assert_player_was_put_on(red_player, "red")
        assert_player_was_put_on(blue_player, "blue")

    def test_move_non_players_to_spec_from_blue_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player = fake_player(3, "Player 3", team="blue")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player)

        self.plugin.move_all_non_playing_players_to_spec()

        assert_player_was_put_on(speccing_player, "spectator")

    def test_move_non_players_to_spec_from_red_team(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player = fake_player(3, "Player 3", team="red")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player)

        self.plugin.move_all_non_playing_players_to_spec()

        assert_player_was_put_on(speccing_player, "spectator")

    def test_move_non_players_to_spec_from_red_and_blue_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player1 = fake_player(3, "Player 3", team="blue")
        speccing_player2 = fake_player(4, "Player 4", team="red")
        self.plugin.switching_player1 = red_player
        self.plugin.switching_player2 = blue_player
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player1,
                          speccing_player2)

        self.plugin.move_all_non_playing_players_to_spec()

        assert_player_was_put_on(speccing_player1, "spectator")
        assert_player_was_put_on(speccing_player2, "spectator")

    def test_game_end_with_no_active_game(self):
        setup_no_game()

        self.plugin.handle_game_end(None)

        verifyNoUnwantedInteractions()

    def test_game_end_with_deactivated_duelarena(self):
        self.deactivate_duelarena_mode()

        self.plugin.handle_game_end(None)

        verifyNoUnwantedInteractions()

    def test_game_end_with_activated_duelarena_red_team_won_stores_players_back_in_queue(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        player3 = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, player3, player4)
        self.add_players_to_queue(player3, player4)

        self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 2})

        self.assert_player_queue(red_player, player3, player4, blue_player)

    def test_game_end_with_activated_duelarena_blue_team_won_stores_players_back_in_queue(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        player3 = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, player3, player4)
        self.add_players_to_queue(player3, player4)

        self.plugin.handle_game_end({"TSCORE0": 5, "TSCORE1": 8})

        self.assert_player_queue(blue_player, player3, player4, red_player)

    def test_round_end_with_no_active_game(self):
        setup_no_game()

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with_no_ca_active(self):
        setup_game_in_progress(game_type="ft")

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_red_team_hit_roundlimit(self):
        setup_game_in_progress(roundlimit=8, red_score=8, blue_score=5)

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_blue_team_hit_roundlimit(self):
        setup_game_in_progress(roundlimit=8, red_score=1, blue_score=8)

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with_duelarena_deactived(self):
        self.deactivate_duelarena_mode()

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with_duel_arena_about_to_init(self):
        self.deactivate_duelarena_mode()
        self.activate_init_duelarena_mode()

        self.plugin.undelayed_handle_round_end(None)

        self.assert_duelarena_finished_to_initialize()

    def test_round_end_with_red_player_won_duel(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        next_player = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          next_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, next_player, player4)
        self.add_players_to_queue(next_player, player4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "RED"})

        assert_player_was_put_on(next_player, "blue")
        assert_that(self.plugin.switching_player2, is_(next_player))
        assert_player_was_put_on(blue_player, "spectator")
        self.assert_player_queue(player4, blue_player)

    def test_round_end_with_blue_player_won_duel(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        next_player = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          next_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, next_player, player4)
        self.add_players_to_queue(next_player, player4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "BLUE"})

        assert_player_was_put_on(next_player, "red")
        assert_that(self.plugin.switching_player1, is_(next_player))
        assert_player_was_put_on(red_player, "spectator")
        self.assert_player_queue(player4, red_player)

    def test_round_end_with_next_player_not_a_spectator_picks_next_from_queue(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        next_player = fake_player(3, "Player 3", team="free")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          next_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, next_player, player4)
        self.add_players_to_queue(next_player, player4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "RED"})

        assert_player_was_put_on(player4, "blue")
        assert_that(self.plugin.switching_player2, is_(player4))
        assert_player_was_put_on(blue_player, "spectator")
        self.assert_player_queue(blue_player)

    def test_round_end_with_no_next_player(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        next_player = fake_player(3, "Player 3", team="free")
        player4 = fake_player(4, "Player 4", team="free")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          next_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, next_player, player4)
        self.add_players_to_queue(next_player, player4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "RED"})

        self.assert_player_queue()
        self.assert_duelarena_deactivated()
        assert_plugin_sent_to_console(self.plugin, "DuelArena has been deactivated! You are free to join.")

    def test_round_end_with_draw(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        next_player = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          next_player,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(red_player, blue_player, next_player, player4)
        self.add_players_to_queue(next_player, player4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "DRAW"})

        assert_player_was_put_on(red_player, any_team, times=0)
        assert_player_was_put_on(blue_player, any_team, times=0)
        assert_player_was_put_on(next_player, any_team, times=0)
        self.assert_player_queue(next_player, player4)

    def test_duel_cmd_with_too_many_connected_players(self):
        requesting_player = fake_player(6, "Player 6")
        connected_players(self.plugin,
                          fake_player(1, "Player 1"),
                          fake_player(2, "Player 2"),
                          fake_player(3, "Player 3"),
                          fake_player(4, "Player 4"),
                          fake_player(5, "Player 5"),
                          requesting_player)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_player_was_told(requesting_player, "^6!duel^7 command not available with ^66^7 or more players connected")

    def test_duel_cmd_second_player_subscribes(self):
        self.deactivate_duelarena_mode()
        player2 = fake_player(2, "Player 2")
        requesting_player = fake_player(3, "Player 3")
        connected_players(self.plugin,
                          fake_player(1, "Player 1"),
                          player2,
                          requesting_player,
                          fake_player(4, "Player 4"),
                          fake_player(5, "Player 5"))
        self.subscribe_players(player2)
        self.add_players_to_queue(player2)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7entered the DuelArena queue. ^61^7 more players needed to start DuelArena. Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 3 ")
        self.assert_subscribed_players(player2, requesting_player)
        self.assert_player_queue(player2, requesting_player)
        self.assert_duelarena_deactivated()

    def test_duel_cmd_third_player_subscribes(self):
        self.deactivate_duelarena_mode()
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        requesting_player = fake_player(3, "Player 3")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          fake_player(4, "Player 4"),
                          fake_player(5, "Player 5"))
        self.subscribe_players(player2, player1)
        self.add_players_to_queue(player2, player1)
        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 3 ")
        self.assert_subscribed_players(player1, player2, requesting_player)
        self.assert_player_queue(player2, player1, requesting_player)
        self.assert_duelarena_activated()

    def test_duel_cmd_fourth_player_subscribes(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          fake_player(4, "Player 4"),
                          player5)
        self.subscribe_players(player2, player1, player5)
        self.add_players_to_queue(player2, player1, player5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 5 ^64th^7: Player 3 ")
        self.assert_subscribed_players(requesting_player, player5, player1, player2)
        self.assert_player_queue(player2, player1, player5, requesting_player)
        self.assert_duelarena_activated()

    def test_duel_cmd_fifth_player_subscribes(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player4 = fake_player(4, "Player 4")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          player4,
                          player5)
        self.subscribe_players(player2, player1, player5, player4)
        self.add_players_to_queue(player2, player1, player5, player4)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 5 ^64th^7: Player 4 ^65th^7: Player 3 ")
        self.assert_subscribed_players(requesting_player, player5, player1, player2, player4)
        self.assert_player_queue(player2, player1, player5, player4, requesting_player)
        self.assert_duelarena_activated()

    def test_duel_cmd_fifth_player_unsubscribes(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1", "red")
        player2 = fake_player(2, "Player 2", "blue")
        player4 = fake_player(4, "Player 4")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          player4,
                          player5)
        self.subscribe_players(requesting_player, player2, player4, player1, player5)
        self.add_players_to_queue(requesting_player, player4, player5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7left DuelArena.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 4 ^62nd^7: Player 5 ")
        self.assert_subscribed_players(player5, player4, player1, player2)
        self.assert_player_queue(player4, player5)
        self.assert_duelarena_activated()

    def test_duel_cmd_fourth_player_unsubscribes(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1", "red")
        player2 = fake_player(2, "Player 2", "blue")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          fake_player(4, "Player 4"),
                          player5)
        self.subscribe_players(requesting_player, player2, player1, player5)
        self.add_players_to_queue(requesting_player, player5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7left DuelArena.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 5 ")
        self.assert_subscribed_players(player5, player1, player2)
        self.assert_player_queue(player5)
        self.assert_duelarena_activated()

    def test_duel_cmd_player_not_in_queue_unsubscribes(self):
        requesting_player = fake_player(3, "Player 3", "red")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2", "blue")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          fake_player(4, "Player 4"),
                          player5)
        self.subscribe_players(requesting_player, player2, player1, player5)
        self.add_players_to_queue(player1, player5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7left DuelArena.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 1 ^62nd^7: Player 5 ")
        self.assert_subscribed_players(player5, player1, player2)
        self.assert_player_queue(player1, player5)
        self.assert_duelarena_activated()

    def test_duel_cmd_third_player_unsubscribes(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1", "red")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          fake_player(2, "Player 2", "blue"),
                          requesting_player, fake_player(4, "Player 4"),
                          player5)
        self.subscribe_players(requesting_player, player1, player5)
        self.add_players_to_queue(requesting_player, player5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        assert_plugin_sent_to_console(self.plugin, "Player 3 ^7left DuelArena.")
        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 5 ")
        assert_plugin_sent_to_console(self.plugin, "DuelArena has been deactivated! You are free to join.")
        self.assert_subscribed_players(player5, player1)
        self.assert_player_queue(player5)
        self.assert_duelarena_deactivated()

    def test_print_empty_queue(self):
        requesting_player = fake_player(1, "Player 1")
        connected_players(self.plugin, requesting_player)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        assert_plugin_sent_to_console(self.plugin, "There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")

    def test_print_queue_with_players(self):
        requesting_player = fake_player(3, "Player 3")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player4 = fake_player(4, "Player 4")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          requesting_player,
                          player4,
                          player5)
        self.add_players_to_queue(player1, player2, requesting_player, player4, player5)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        assert_plugin_sent_to_console(self.plugin, "DuelArena queue: ^61st^7: Player 1 ^62nd^7: Player 2 ^63rd^7: Player 3 ^64th^7: Player 4 ^65th^7: Player 5 ")

    def test_print_queue_with_too_many_connected_players(self):
        requesting_player = fake_player(6, "Player 6")
        player1 = fake_player(1, "Player 1")
        player2 = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3")
        player4 = fake_player(4, "Player 4")
        player5 = fake_player(5, "Player 5")
        connected_players(self.plugin,
                          player1,
                          player2,
                          player3,
                          player4,
                          player5,
                          requesting_player)
        self.add_players_to_queue(player1, player2, player3, player4, player5)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        assert_player_was_told(requesting_player, "^6!queue^7 command not available with ^66^7 or more players connected")


import minqlx

MIN_ACTIVE_PLAYERS = 3  # with <3 connected and subscribed players we deactive DuelArena
MAX_ACTIVE_PLAYERS = 5  # with >5 connected players we deactivate DuelArena

DUEL_ARENA_ANNOUNCEMENT = "Type ^6!d ^7for DuelArena!"


class duelarena(minqlx.Plugin):
    """DuelArena will start automatically if at least 3 players opted in (!duel or !d) to the queue.

    DuelArena will be deactivated automatically if connected players exceed the player_limit (default 5), or if there are only 2 players left, or if too many players opted out.
    """

    def __init__(self):

        self.add_hook("team_switch_attempt", self.handle_team_switch_event)
        self.add_hook("player_disconnect", self.handle_player_disco)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_command(("duel", "d"), self.cmd_duel)
        self.add_command(("queue", "q"), self.cmd_printqueue)

        self.duelmode = False  # global gametype switch
        self.initduel = False  # initial player setup switch
        self.psub = []  # steam_ids of players subscribed to DuelArena
        self.queue = []  # queue for rotating players
        self.switching_player1 = None  # force spec exception for this player
        self.switching_player2 = None  # force spec exception for this player

    # Don't allow players to join manually when DuelArena is active
    def handle_team_switch_event(self, player, old, new):
        if not self.duelmode: return
        if not self.game: return
        if self.game.state == "warmup": return

        # If we initiated this switch, allow it
        if player == self.switching_player1:
            self.switching_player1 = None
            return

        if player == self.switching_player2:
            self.switching_player2 = None
            return

        # If they wanted to join a team, halt this hook at enginge-level and other hooks from being called
        if new in ['red', 'blue']:
            player.tell(
                "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")
            return minqlx.RET_STOP_ALL

    # When a player connects, display them a message and check if we should switch duel arena
    @minqlx.delay(4)
    def handle_player_connect(self, player):
        self.undelayed_handle_player_connected_or_disconnected()

    # When a player disconnects, display them a message and check if we should switch duel arena
    @minqlx.delay(3)
    def handle_player_disco(self, player, reason):
        self.undelayed_handle_player_connected_or_disconnected()

    def undelayed_handle_player_connected_or_disconnected(self):
        self.switch_duelarena_if_necessary()

        player_count = self.count_connected_players()

        if (player_count == MIN_ACTIVE_PLAYERS or player_count == MAX_ACTIVE_PLAYERS) and not self.duelmode:
            self.center_print(DUEL_ARENA_ANNOUNCEMENT)
            self.msg(DUEL_ARENA_ANNOUNCEMENT)

    def handle_round_countdown(self, *args, **kwargs):

        if not self.duelmode: return

        teams = self.teams()
        self.center_print("{} ^2vs {}".format(teams["red"][-1].name, teams["blue"][-1].name))

    # When a game is about to start and duelmode is active, initialize
    @minqlx.delay(3)
    def handle_game_countdown(self):
        self.undelayed_handle_game_countdown()

    def undelayed_handle_game_countdown(self):
        if not self.duelmode: return
        self.init_duel()

    def handle_game_end(self, data):
        if not self.game: return
        if not self.duelmode: return

        # put both players back to the queue, winner first position, loser last position
        winner, loser = self.extract_winning_and_losing_team_from_game_end_data(data)

        teams = self.teams()

        self.queue.insert(0, teams[loser][-1].steam_id)
        self.queue.append(teams[winner][-1].steam_id)

    def extract_winning_and_losing_team_from_game_end_data(self, data):
        if int(data['TSCORE1']) > int(data['TSCORE0']):
            return "blue", "red"
        return "red", "blue"

    @minqlx.delay(1.5)
    def handle_round_end(self, data):
        self.undelayed_handle_round_end(data)

    def undelayed_handle_round_end(self, data):

        # Not in CA? Do nothing
        if (not self.game) or (self.game.type_short != "ca"): return

        # Last round? Do nothing
        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.initduel:
            self.init_duel()
            return

        if not self.duelmode:
            return

        losing_team = self.extract_losing_team_from_round_end_data(data)
        if not losing_team:
            return  # Draw? Do nothing

        next_player = self.player(self.queue.pop())

        teams = self.teams()

        while not next_player or next_player not in teams['spectator']:
            try:
                next_player = self.player(self.queue.pop())
            except IndexError:
                self.deactivate_duelarena_mode()
                return

        losing_player = teams[losing_team][-1]

        self.put_player_on_team(next_player, losing_team)
        self.put_player_to_spectators_and_back_in_duel_queue(losing_player)

    def extract_losing_team_from_round_end_data(self, data):
        if data["TEAM_WON"] == "RED": return "blue"
        if data["TEAM_WON"] == "BLUE": return "red"
        return None

    def put_player_on_team(self, player, team):
        if team == "red": self.switching_player1 = player
        if team == "blue": self.switching_player2 = player
        player.put(team)

    def put_player_to_spectators_and_back_in_duel_queue(self, losing_player):
        self.queue.insert(0, losing_player.steam_id)
        losing_player.put("spectator")

    def cmd_duel(self, player, msg, channel):

        if self.count_connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!duel^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        self.checklists()

        if self.player_is_subscribed(player):
            self.unsubscribe_player(player)
            self.msg("{} ^7left DuelArena.".format(player.name))
            self.printqueue()
            if not self.should_duelmode_be_activated():
                self.deactivate_duelarena_mode()
            return

        self.subscribe_player(player)
        if not self.should_duelmode_be_activated():
            self.msg(
                "{} ^7entered the DuelArena queue. ^6{}^7 more players needed to start DuelArena. Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue."
                    .format(player.name, MIN_ACTIVE_PLAYERS - len(self.psub)))
            self.printqueue()
            return

        self.msg(
            "{} ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.".format(player.name))
        self.printqueue()
        self.activate_duelarena_mode()

    def cmd_printqueue(self, player, msg, channel):

        if self.count_connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!queue^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        self.printqueue()

    def printqueue(self):

        if len(self.queue) == 0:
            self.msg("There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")
            return

        qstring = ""

        for steam_id in self.queue:
            player = self.player(steam_id)
            indicator = self.position_of_player_in_queue(player)
            place = "{}th".format(indicator)
            if indicator == 1:
                place = "1st"
            elif indicator == 2:
                place = "2nd"
            elif indicator == 3:
                place = "3rd"
            qstring = "^6{}^7: {} ".format(place, player.name) + qstring

        self.msg("DuelArena queue: {}".format(qstring))

    def position_of_player_in_queue(self, player):
        return len(self.queue) - self.queue.index(player.steam_id)

    def init_duel(self):

        self.checklists()

        self.insert_subscribed_players_to_queue_if_necessary()

        self.switching_player1 = self.player(self.queue.pop())
        self.switching_player2 = self.player(self.queue.pop())

        self.move_players_to_teams()

        self.move_all_non_playing_players_to_spec()

        self.initduel = False

    def insert_subscribed_players_to_queue_if_necessary(self):
        for _p in [steam_id for steam_id in self.psub if steam_id not in self.queue]:
            self.queue.insert(0, _p)

    def switch_duelarena_if_necessary(self):

        self.checklists()

        if self.duelmode and not self.should_duelmode_be_activated():
            self.deactivate_duelarena_mode()
            return

        if not self.duelmode and self.should_duelmode_be_activated():
            self.activate_duelarena_mode()

    def checklists(self):

        self.queue[:] = [sid for sid in self.queue if self.player(sid) and self.player(sid).ping < 990]

        self.psub[:] = [sid for sid in self.psub if self.player(sid) and self.player(sid).ping < 990]

    ## Helper functions

    def count_connected_players(self):
        return len(self.players())

    def player_is_subscribed(self, player):
        return player.steam_id in self.psub

    def player_is_enqueued(self, player):
        return player.steam_id in self.queue

    def subscribe_player(self, player):
        if not self.player_is_enqueued(player): self.queue.insert(0, player.steam_id)
        self.psub.append(player.steam_id)

    def unsubscribe_player(self, player):
        if self.player_is_enqueued(player): self.queue.remove(player.steam_id)
        self.psub.remove(player.steam_id)

    def should_duelmode_be_activated(self):
        player_count = self.count_connected_players()

        return player_count in range(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS+1) and len(self.psub) >= MIN_ACTIVE_PLAYERS

    def activate_duelarena_mode(self):
        self.duelmode = True
        self.msg("DuelArena activated!")
        self.center_print("DuelArena activated!")
        if self.game and self.game.state == "in_progress":
            self.initduel = True

    def deactivate_duelarena_mode(self):
        self.duelmode = False
        self.msg("DuelArena has been deactivated! You are free to join.")

    def move_players_to_teams(self):

        teams = self.teams()

        if self.switching_player1 in teams["red"]:
            if self.switching_player2 not in teams["blue"]:
                self.switching_player2.put("blue")
            return

        if self.switching_player1 in teams["blue"]:
            if self.switching_player2 not in teams["red"]:
                self.switching_player2.put("red")
            return

        if self.switching_player2 in teams["blue"]:
            self.switching_player1.put("red")
            return

        if self.switching_player2 in teams["red"]:
            self.switching_player1.put("blue")
            return

        self.switching_player1.put("red")
        self.switching_player2.put("blue")

    def move_all_non_playing_players_to_spec(self):

        teams = self.teams()

        for player in [player for player in teams['red'] + teams['blue']
                       if player not in [self.switching_player1, self.switching_player2]]:
                player.put("spectator")
