from minqlx_plugin_test import *

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from auto_rebalance import *


class AutoRebalanceTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "qlx_rebalanceSuggestionThreshold": (3, int)
        })
        setup_game_in_progress()
        connected_players()
        self.plugin = auto_rebalance()

    def tearDown(self):
        unstub()

    def setup_balance_ratings(self, player_elos):
        gametype = self.plugin.game.type_short
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {'elo': elo}}
        self.plugin._loaded_plugins["balance"] = mock({'ratings': ratings})

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:
            del self.plugin._loaded_plugins["balance"]

    def test_handle_team_switch_attempt_no_game_running(self):
        setup_no_game()
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_last_new_player_changes_back_to_spec(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        last_new_player = fake_player(42, "Last New Player", "red")
        connected_players(red_player, blue_player, last_new_player)

        self.plugin.last_new_player_id = last_new_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(last_new_player, "red", "spectator")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_game_in_warmup(self):
        setup_game_in_warmup()
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_not_from_spectator(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_to_spectator(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "spectator")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_rebalance_not_set_for_teamswitch_events(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_no_balance_plugin_loaded(self):
        self.setup_no_balance_plugin()
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_plugin_sent_to_console(matches(".*not possible.*"))

    def test_handle_team_switch_attempt_unsupported_gametype(self):
        setup_game_in_progress(game_type="rr")
        self.setup_balance_ratings([])
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_first_player_joins(self):
        self.setup_balance_ratings([])
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(player.steam_id))

    def test_handle_team_switch_attempt_second_player_joins_same_team(self):
        self.setup_balance_ratings([])
        red_player = fake_player(123, "Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_that(self.plugin.last_new_player_id, is_(None))
        assert_player_was_put_on(new_player, "blue")

    def test_handle_team_switch_attempt_third_player_joins(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(new_player.steam_id))

    def test_handle_team_switch_attempt_fourth_player_joins_no_last_id_set(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_team_switch_attempt_fourth_player_joins_last_player_disconnected(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = 666

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_teams_already_balanced(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = new_red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "blue")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_wrong_teams(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = new_red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_put_on(new_player, "blue")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_would_lead_to_less_optimal_teamss(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_blue_player = fake_player(41, "New Red Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_blue_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1400),
                                    (new_blue_player, 1400), (new_player, 1200)])
        self.plugin.last_new_player_id = new_blue_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_player_was_put_on(new_player, "blue")
        assert_player_was_put_on(new_blue_player, "red")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_team_switch_attempt_fourth_player_joins_not_to_better_balanced_team(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_blue_player = fake_player(41, "New Red Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_blue_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1400),
                                    (new_blue_player, 1400), (new_player, 1200)])
        self.plugin.last_new_player_id = new_blue_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "blue")

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_player_was_put_on(new_player, "blue", times=0)
        assert_player_was_put_on(new_blue_player, "red")
        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_round_start_resets_last_new_player_id(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        self.plugin.handle_round_start(3)

        assert_that(self.plugin.last_new_player_id, is_(None))

    def test_handle_round_end_no_game_running(self):
        setup_no_game()

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_round_end_wrong_gametype(self):
        setup_game_in_progress(game_type="rr")

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_round_end_roundlimit_reached(self):
        setup_game_in_progress(roundlimit=8, red_score=8, blue_score=3)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_round_end_suggestion_threshold_not_met(self):
        setup_game_in_progress(roundlimit=8, red_score=4, blue_score=3)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_round_end_teams_unbalanced(self):
        setup_game_in_progress(roundlimit=8, red_score=5, blue_score=1)

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"), blue_player1)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(minqlx.RET_NONE))

    def test_handle_round_end_teams_callback_called(self):
        mocked_balance_plugin = mock()
        mocked_balance_plugin.callback_teams = lambda: None
        Plugin._loaded_plugins["balance"] = mocked_balance_plugin
        setup_game_in_progress(game_type="ca", roundlimit=8, red_score=5, blue_score=1)

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        players = dict([(p.steam_id, "ca") for p in [red_player1, red_player2, blue_player1, blue_player2]])
        verify(mocked_balance_plugin).add_request(players, mocked_balance_plugin.callback_teams, minqlx.CHAT_CHANNEL)

    def test_handle_round_end_no_balance_plugin(self):
        self.setup_no_balance_plugin()
        setup_game_in_progress(game_type="ca", roundlimit=8, red_score=5, blue_score=1)

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert_that(return_code, is_(None))
