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

    def tearDown(self):
        unstub()

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:
            del self.plugin._loaded_plugins["balance"]

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

    def setup_previous_players(self, *players):
        self.plugin.previous_round_player_steam_ids = [player.steam_id for player in players]

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

    def test_handle_round_start_remembers_steamd_ids(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        self.plugin.handle_round_start(3)

        assert_that(self.plugin.previous_round_player_steam_ids,
                    is_([player.steam_id for player in [red_player1, red_player2, blue_player1, blue_player2]]))

    def test_handle_game_countdown_resets_remembered_steam_ids(self):
        self.plugin.previous_round_player_steam_ids = [123, 456, 246, 975]

        self.plugin.handle_game_countdown()

        assert_that(self.plugin.previous_round_player_steam_ids, is_([]))
