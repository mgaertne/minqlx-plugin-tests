from minqlx_plugin_test import *

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from auto_rebalance import *


class AutoRebalanceTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_game_in_progress()
        connected_players()
        self.plugin = auto_rebalance()
        self.plugin.rebalance_method = "countdown"

    def tearDown(self):
        unstub()

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:
            del self.plugin._loaded_plugins["balance"]

    def test_handle_team_switch_attempt_no_game_running(self):
        setup_no_game()
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_game_in_warmup(self):
        setup_game_in_warmup()
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_not_from_spectator(self):
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_to_spectator(self):
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "spectator")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_rebalance_not_set_for_teamswitch_events(self):
        self.plugin.rebalance_method = "countdown"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_no_balance_plugin_loaded(self):
        self.setup_no_balance_plugin()
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_plugin_sent_to_console(matches(".*not possible.*"))

    def test_handle_team_switch_attempt_unsupported_gametype(self):
        setup_game_in_progress(game_type="rr")
        self.setup_balance_ratings([])
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_first_player_joins(self):
        self.setup_balance_ratings([])
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(player.steam_id))

    def test_handle_team_switch_attempt_second_player_joins_same_team(self):
        self.setup_balance_ratings([])
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, new_player)

        self.setup_previous_players(red_player)
        self.setup_balance_ratings([(red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_that(self.plugin.last_new_player_id, is_(None))
        assert_player_was_put_on(new_player, "blue")

    def test_handle_team_switch_attempt_third_player_joins(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_player)

        self.setup_previous_players(red_player, blue_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(new_player.steam_id))

    def test_handle_team_switch_attempt_fourth_player_joins_no_last_id_set(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_red_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_fourth_player_joins_last_player_disconnected(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_red_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = 666

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_teams_already_balanced(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_red_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = new_red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "blue")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_wrong_teams(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_red_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = new_red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_put_on(new_player, "blue")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_would_lead_to_less_optimal_teamss(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_blue_player = fake_player(41, "New Red Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_blue_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_blue_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1400),
                                    (new_blue_player, 1400), (new_player, 1200)])
        self.plugin.last_new_player_id = new_blue_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_put_on(new_player, "blue")
        assert_player_was_put_on(new_blue_player, "red")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_not_to_better_balanced_team(self):
        self.plugin.rebalance_method = "teamswitch"
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_blue_player = fake_player(41, "New Red Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_blue_player, new_player)

        self.setup_previous_players(red_player, blue_player, new_blue_player)
        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1400),
                                    (new_blue_player, 1400), (new_player, 1200)])
        self.plugin.last_new_player_id = new_blue_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "blue")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_player_was_put_on(new_player, "blue", times=0)
        assert_player_was_put_on(new_blue_player, "red")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_round_countdown_rebalance_method_during_team_switch(self):
        self.plugin.rebalance_method = "teamswitch"

        self.plugin.handle_round_countdown(5)

        assert_plugin_sent_to_console(any, times=0)

    def test_handle_round_countdown_prints_message_when_balance_plugin_not_loaded(self):
        self.setup_no_balance_plugin()

        self.plugin.handle_round_countdown(5)

        assert_plugin_sent_to_console(matches(".*not possible.*"))

    def setup_balance_ratings(self, player_elos):
        gametype = self.plugin.game.type_short
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {'elo': elo}}
        self.plugin._loaded_plugins["balance"] = mock({'ratings': ratings})

    def test_handle_round_countdown_does_nothing_for_non_supported_gametypes(self):
        setup_game_in_progress(game_type="rr")
        self.setup_balance_ratings([])

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console(any, times=0)

    def test_handle_round_countdown_does_nothing_for_first_round(self):
        self.setup_balance_ratings([])

        self.plugin.handle_round_countdown(1)

        assert_plugin_sent_to_console(any, times=0)

    def setup_previous_players(self, *players):
        self.plugin.balanced_player_steam_ids = [player.steam_id for player in players]

    def test_handle_round_countdown_nothing_to_rebalance(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        new_player1 = fake_player(42, "New Player1", "red")
        new_player2 = fake_player(43, "New Player2", "blue")
        connected_players(red_player1, red_player2, blue_player1, blue_player2, new_player1, new_player2)

        self.setup_previous_players(red_player1, red_player2, blue_player1, blue_player2)
        self.setup_balance_ratings([(red_player1, 1200), (red_player2, 1200), (blue_player1, 1200),
                                    (blue_player2, 1200), (new_player1, 1200), (new_player2, 1200)])

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console("New players detected: {}, {}".format(new_player1.name, new_player2.name))
        assert_plugin_sent_to_console(matches(".*Nothing to rebalance"))

    def test_handle_round_countdown_two_new_players_are_switched(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        new_player1 = fake_player(42, "New Player1", "red")
        new_player2 = fake_player(43, "New Player2", "blue")
        connected_players(red_player1, red_player2, blue_player1, blue_player2, new_player1, new_player2)

        self.setup_previous_players(red_player1, red_player2, blue_player1, blue_player2)
        self.setup_balance_ratings([(red_player1, 1100), (red_player2, 1100), (blue_player1, 1200),
                                    (blue_player2, 1200), (new_player1, 1200), (new_player2, 1400)])

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console("New players detected: {}, {}".format(new_player1.name, new_player2.name))
        assert_players_switched(new_player1, new_player2)

    def test_handle_round_countdown_six_new_players_are_rebalanced(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        new_player1 = fake_player(42, "New Player1", "red")
        new_player2 = fake_player(43, "New Player2", "blue")
        new_player3 = fake_player(44, "New Player3", "red")
        new_player4 = fake_player(45, "New Player4", "blue")
        new_player5 = fake_player(46, "New Player5", "red")
        new_player6 = fake_player(47, "New Player6", "blue")
        connected_players(red_player1, red_player2, blue_player1, blue_player2,
                          new_player1, new_player2, new_player3, new_player4, new_player5, new_player6)

        self.setup_previous_players(red_player1, red_player2, blue_player1, blue_player2)
        self.setup_balance_ratings([(red_player1, 1100), (red_player2, 1100), (blue_player1, 1200),
                                    (blue_player2, 1200), (new_player1, 1200), (new_player2, 1200),
                                    (new_player3, 1400), (new_player4, 1400), (new_player5, 1200),
                                    (new_player6, 1400)])

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console("New players detected: {}"
                                      .format(", ".join([new_player1.name, new_player3.name, new_player5.name,
                                                         new_player2.name, new_player4.name, new_player6.name])))
        assert_players_switched(new_player1, new_player4)

    def test_handle_round_countdown_does_nothing_with_no_new_joiners(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)
        self.setup_previous_players(red_player1, red_player2, blue_player1, blue_player2)

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console(matches("New players detected: .*"), times=0)

    def test_handle_round_countdown_does_nothing_with_just_one_new_joiner(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "red"),
                          blue_player1, blue_player2)
        self.setup_previous_players(red_player1, red_player2, blue_player1, blue_player2)

        self.plugin.handle_round_countdown(3)

        assert_plugin_sent_to_console(matches("New players detected: .*"), times=0)

    def test_handle_round_start_remembers_steamd_ids(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        self.plugin.handle_round_start(3)

        assert_that(self.plugin.balanced_player_steam_ids,
                    is_([player.steam_id for player in [red_player1, red_player2, blue_player1, blue_player2]]))

    def test_handle_game_countdown_resets_remembered_steam_ids(self):
        self.plugin.balanced_player_steam_ids = [123, 456, 246, 975]

        self.plugin.handle_game_countdown()

        assert_that(self.plugin.balanced_player_steam_ids, is_([]))

    def test_cmd_rebalance_method_shows_usage_for_too_few_parameters(self):
        player = fake_player(123, "Fake Player")

        return_code = self.plugin.cmd_rebalance_method(player, ["!rebalanceMethod"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))
        assert_player_was_told(player, "Current rebalance method is: ^4countdown^7")

    def test_cmd_rebalance_method_shows_usage_for_too_many_parameters(self):
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(123, "Fake Player")

        return_code = self.plugin.cmd_rebalance_method(player, ["!rebalanceMethod", "asdf", "qwerty"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))
        assert_player_was_told(player, "Current rebalance method is: ^4teamswitch^7")

    def test_cmd_rebalance_method_shows_usage_for_invalid_parameter(self):
        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(123, "Fake Player")

        return_code = self.plugin.cmd_rebalance_method(player, ["!rebalanceMethod", "asdf"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))
        assert_player_was_told(player, "Current rebalance method is: ^4teamswitch^7")

    def test_cmd_rebalance_method_set_to_another_value(self):
        spy2(Plugin.set_cvar)
        when2(Plugin.set_cvar, any, any).thenReturn(None)

        self.plugin.rebalance_method = "teamswitch"
        player = fake_player(123, "Fake Player")

        self.plugin.cmd_rebalance_method(player, ["!rebalanceMethod", "countdown"], None)

        assert_player_was_told(player, "Rebalance method set to: ^4countdown^7")
        assert_that(self.plugin.rebalance_method, is_("countdown"))
        verify(Plugin).set_cvar("qlx_rebalanceMethod", "countdown")
