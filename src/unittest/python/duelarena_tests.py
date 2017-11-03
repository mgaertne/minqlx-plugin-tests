from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from duelarena import *


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
        self.plugin.initduel = True

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

    def assert_players_were_not_moved_to_any_team(self, *players):
        assert_that(self.plugin.switching_players, is_not(has_items(players)))
        for player in players:
            assert_player_was_put_on(player, any_team, times=0)

    def assert_player_was_put_to_team(self, player, matcher):
        assert_that(self.plugin.switching_players, has_item(player))
        assert_player_was_put_on(player, matcher)

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
        switching_player = fake_player(123, "Fake Player")
        self.plugin.switching_players.append(switching_player)
        self.plugin.scores[switching_player.steam_id] = 3

        return_code = self.plugin.handle_team_switch_event(switching_player, "don't care", "don't care")

        assert_that(self.plugin.switching_players, is_not(has_item(switching_player)))
        assert_that(switching_player.score, is_(3))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_to_blue_initiated_by_plugin(self):
        switching_player = fake_player(123, "Fake Player")
        self.plugin.switching_players.append(switching_player)

        return_code = self.plugin.handle_team_switch_event(switching_player, "don't care", "don't care")

        assert_that(self.plugin.switching_players, is_not(has_item(switching_player)))
        assert_that(switching_player.score, is_(0))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_unallowed_switch_from_spec_to_red(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player,
                               "Server is in DuelArena mode. You will automatically join. "
                               "Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_spec_to_blue(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player,
                               "Server is in DuelArena mode. You will automatically join. "
                               "Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_blue_to_red(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "blue", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player,
                               "Server is in DuelArena mode. You will automatically join. "
                               "Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_unallowed_switch_from_red_to_blue(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "red", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_told(switching_player,
                               "Server is in DuelArena mode. You will automatically join. "
                               "Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")

    def test_switching_to_spectators_is_always_allowed(self):
        switching_player = fake_player(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "red", "spectator")

        assert_that(return_code, is_(None))

    def test_2nd_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(2, "Player 2")
        connected_players(self.plugin, fake_player(1, "Player 1"), connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

        self.assert_duelarena_deactivated()

    def test_3rd_player_connects(self):
        self.deactivate_duelarena_mode()
        connecting_player = fake_player(3, "Player 3")
        connected_players(self.plugin, fake_player(1, "Player 1"), fake_player(2, "Player 2"), connecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(connecting_player)

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

        self.plugin.undelayed_handle_player_connected_or_disconnected(fake_player(5, "Player 5"))

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_handle_player_disconnect_deactivates_duelarena(self):
        player1 = fake_player(1, "Player 1", team="blue")
        player2 = fake_player(2, "Player 2")
        disconnecting_player = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          player1,
                          player2,
                          fake_player(3, "Player 3", team="red"))
        self.subscribe_players(player1, player2, disconnecting_player)

        self.plugin.undelayed_handle_player_connected_or_disconnected(disconnecting_player)

        assert_plugin_sent_to_console(self.plugin, "DuelArena has been deactivated! You are free to join.")
        self.assert_duelarena_deactivated()
        self.assert_subscribed_players(player2, player1)

    def test_handle_player_disconnect_activates_duelarena(self):
        self.deactivate_duelarena_mode()
        player1 = fake_player(1, "Player 1", team="blue")
        player2 = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3", team="red")
        player4 = fake_player(4, "Player 4")
        disconnecting_player = fake_player(6, "Player 6")
        connected_players(self.plugin,
                          player1,
                          player2,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(player1, player2, disconnecting_player, player3, player4)
        self.add_players_to_queue(player1, player2, disconnecting_player, player3, player4)
        when2(self.plugin.player, 6).thenReturn(None)

        self.plugin.undelayed_handle_player_connected_or_disconnected(disconnecting_player)

        assert_plugin_sent_to_console(self.plugin, "DuelArena activated!")
        assert_plugin_center_printed(self.plugin, "DuelArena activated!")
        self.assert_duelarena_activated()
        self.assert_duelarena_about_to_initialize()
        self.assert_subscribed_players(player1, player2, player3, player4)
        self.assert_player_queue(player1, player2, player3, player4)

    def test_handle_player_disconnect_removes_stored_score_when_duelarena_activated(self):
        self.activate_duelarena_mode()
        player1 = fake_player(1, "Player 1", team="blue")
        disconnecting_player = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3", team="red")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          player1,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(player1, disconnecting_player, player3, player4)
        self.add_players_to_queue(disconnecting_player, player4)
        self.plugin.scores[disconnecting_player.steam_id] = 5
        when2(self.plugin.player, 2).thenReturn(None)

        self.plugin.undelayed_handle_player_connected_or_disconnected(disconnecting_player)

        self.assert_duelarena_activated()
        self.assert_subscribed_players(player1, player3, player4)
        self.assert_player_queue(player4)
        assert_that(self.plugin.scores, not_(has_item(disconnecting_player.steam_id)))

    def test_handle_player_disconnect_activates_duelarena_in_warmup(self):
        self.deactivate_duelarena_mode()
        player1 = fake_player(1, "Player 1", team="blue")
        player2 = fake_player(2, "Player 2")
        player3 = fake_player(3, "Player 3", team="red")
        player4 = fake_player(4, "Player 4")
        disconnecting_player = fake_player(6, "Player 6")
        connected_players(self.plugin,
                          player1,
                          player2,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        setup_game_in_warmup()
        self.subscribe_players(player1, player2, disconnecting_player, player3, player4)
        self.add_players_to_queue(player1, player2, disconnecting_player, player3, player4)
        when2(self.plugin.player, 6).thenReturn(None)

        self.plugin.undelayed_handle_player_connected_or_disconnected(disconnecting_player)

        assert_plugin_sent_to_console(self.plugin, "DuelArena activated!")
        assert_plugin_center_printed(self.plugin, "DuelArena activated!")
        self.assert_duelarena_activated()
        self.assert_duelarena_finished_to_initialize()
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

        self.plugin.undelayed_handle_player_connected_or_disconnected(fake_player(6, "Player 6"))

        assert_plugin_sent_to_console(self.plugin, "Type ^6!d ^7for DuelArena!")
        assert_plugin_center_printed(self.plugin, "Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_game_countdown_doesn_t_do_anything_when_not_activated(self):
        self.deactivate_duelarena_mode()

        self.plugin.undelayed_handle_game_countdown()

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

        self.assert_player_was_put_to_team(blue_player, "red")
        assert_player_was_put_on(speccing_player, "spectator")
        self.assert_duelarena_finished_to_initialize()
        self.assert_player_queue(speccing_player, player4)

    def test_game_countdown_inits_duelarena_when_activated_and_keeps_red_player_on_red_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        player3 = fake_player(3, "Player 3", team="blue")
        player4 = fake_player(4, "Player 4")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          player3,
                          player4,
                          fake_player(5, "Player 5"))
        self.subscribe_players(player4, player3, blue_player, red_player)

        self.plugin.undelayed_handle_game_countdown()

        self.assert_players_were_not_moved_to_any_team(red_player, blue_player)
        self.assert_duelarena_finished_to_initialize()
        self.assert_player_queue(player3, player4)

    def test_move_players_to_teams_players_already_on_right_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="blue")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_players_were_not_moved_to_any_team(red_player, blue_player)

    def test_move_players_to_teams_players_on_opposing_teams(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="red")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_players_were_not_moved_to_any_team(red_player, blue_player)

    def test_move_players_to_teams_players_on_blue_team(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="blue")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))
        self.plugin.switching_players.append(red_player)
        self.plugin.switching_players.append(blue_player)

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_players_were_not_moved_to_any_team(red_player)
        self.assert_player_was_put_to_team(blue_player, "red")

    def test_move_players_to_teams_players_on_red_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_players_were_not_moved_to_any_team(red_player)
        self.assert_player_was_put_to_team(blue_player, "blue")

    def test_move_players_to_teams_one_player_speccing(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", "spectator")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_players_were_not_moved_to_any_team(red_player)
        self.assert_player_was_put_to_team(blue_player, "blue")

    def test_move_players_to_teams_both_players_speccing(self):
        red_player = fake_player(1, "Player 1", "spectator")
        blue_player = fake_player(2, "Player 2", "spectator")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_player_was_put_to_team(red_player, "red")
        self.assert_player_was_put_to_team(blue_player, "blue")

    def test_move_players_to_teams_red_player_speccing_blue_player_on_blue_team(self):
        red_player = fake_player(1, "Player 1", "spectator")
        blue_player = fake_player(2, "Player 2", "blue")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_player_was_put_to_team(red_player, "red")
        self.assert_players_were_not_moved_to_any_team(blue_player)

    def test_move_players_to_teams_red_player_speccing_blue_player_on_red_team(self):
        red_player = fake_player(1, "Player 1", "spectator")
        blue_player = fake_player(2, "Player 2", "red")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          fake_player(3, "Player 3", "red"))

        self.plugin.move_players_to_teams(red_player, blue_player)

        self.assert_player_was_put_to_team(red_player, "blue")
        self.assert_players_were_not_moved_to_any_team(blue_player)

    def test_move_non_players_to_spec_from_blue_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player = fake_player(3, "Player 3", team="blue")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player)
        self.plugin.switching_players.append(red_player)
        self.plugin.switching_players.append(blue_player)

        self.plugin.move_all_non_playing_players_to_spec()

        assert_player_was_put_on(speccing_player, "spectator")

    def test_move_non_players_to_spec_from_red_team(self):
        red_player = fake_player(1, "Player 1", team="blue")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player = fake_player(3, "Player 3", team="red")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player)
        self.plugin.switching_players.append(red_player)
        self.plugin.switching_players.append(blue_player)

        self.plugin.move_all_non_playing_players_to_spec()

        assert_player_was_put_on(speccing_player, "spectator")

    def test_move_non_players_to_spec_from_red_and_blue_team(self):
        red_player = fake_player(1, "Player 1", team="red")
        blue_player = fake_player(2, "Player 2", team="red")
        speccing_player1 = fake_player(3, "Player 3", team="blue")
        speccing_player2 = fake_player(4, "Player 4", team="red")
        connected_players(self.plugin,
                          red_player,
                          blue_player,
                          speccing_player1,
                          speccing_player2)
        self.plugin.switching_players.append(red_player)
        self.plugin.switching_players.append(blue_player)

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
        self.deactivate_duelarena_mode()
        self.activate_init_duelarena_mode()
        self.plugin.scores = {player4.steam_id: 3, red_player.steam_id: 5}

        self.plugin.undelayed_handle_round_end(None)

        self.assert_duelarena_finished_to_initialize()
        assert_that(self.plugin.scores, is_({}))

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

        self.assert_player_was_put_to_team(next_player, "blue")
        assert_player_was_put_on(blue_player, "spectator")
        self.assert_player_queue(player4, blue_player)

    def test_round_end_with_blue_player_won_duel(self):
        red_player = fake_player(1, "Player 1", team="red", score=2)
        blue_player = fake_player(2, "Player 2", team="blue", score=5)
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
        self.plugin.scores[next_player.steam_id] = 3

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "BLUE"})

        self.assert_player_was_put_to_team(next_player, "red")
        assert_player_was_put_on(red_player, "spectator")
        self.assert_player_queue(player4, red_player)
        assert_that(self.plugin.scores[red_player.steam_id], is_(2))

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

        self.assert_player_was_put_to_team(player4, "blue")
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

        assert_player_was_told(requesting_player,
                               "^6!duel^7 command not available with ^66^7 or more players connected")

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

        assert_plugin_sent_to_console(self.plugin,
                                      "Player 3 ^7entered the DuelArena queue. "
                                      "^61^7 more players needed to start DuelArena. "
                                      "Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue.")
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

        assert_plugin_sent_to_console(self.plugin,
                                      "Player 3 ^7entered the DuelArena. "
                                      "Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin,
                                      "DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 3 ")
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

        assert_plugin_sent_to_console(self.plugin,
                                      "Player 3 ^7entered the DuelArena. "
                                      "Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin,
                                      "DuelArena queue: "
                                      "^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 5 ^64th^7: Player 3 ")
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

        assert_plugin_sent_to_console(self.plugin,
                                      "Player 3 ^7entered the DuelArena. "
                                      "Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        assert_plugin_sent_to_console(self.plugin,
                                      "DuelArena queue: "
                                      "^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 5 "
                                      "^64th^7: Player 4 ^65th^7: Player 3 ")
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

        assert_plugin_sent_to_console(self.plugin,
                                      "There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")

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

        assert_plugin_sent_to_console(self.plugin,
                                      "DuelArena queue: ^61st^7: Player 1 ^62nd^7: Player 2 ^63rd^7: Player 3 "
                                      "^64th^7: Player 4 ^65th^7: Player 5 ")

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

        assert_player_was_told(requesting_player,
                               "^6!queue^7 command not available with ^66^7 or more players connected")
