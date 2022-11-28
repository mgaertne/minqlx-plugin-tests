from unittest.mock import patch, Mock

import pytest

from minqlx_plugin_test import setup_plugin, setup_cvars, connected_players, \
    fake_player, assert_plugin_sent_to_console, assert_player_was_put_on

from mockito import unstub  # type: ignore
from mockito.matchers import matches  # type: ignore

from undecorated import undecorated  # type: ignore

import minqlx
from minqlx import Plugin
from auto_rebalance import auto_rebalance


class TestAutoRebalance:

    @pytest.fixture
    def mocked_balance_plugin(self):
        mocked_balance_plugin = Mock()
        patch.object(mocked_balance_plugin, "callback_teams")
        patch.object(mocked_balance_plugin, "add_request")
        Plugin._loaded_plugins["balance"] = mocked_balance_plugin  # pylint: disable=protected-access
        return mocked_balance_plugin

    def setup_method(self):
        setup_plugin()
        setup_cvars({
            "qlx_rebalanceScoreDiffThreshold": "3",
            "qlx_rebalanceWinningStreakThreshold": "3",
            "qlx_rebalanceNumAnnouncements": "2"
        })
        connected_players()
        self.plugin = auto_rebalance()

    @staticmethod
    def teardown_method():
        unstub()

    def setup_balance_ratings(self, player_elos):
        gametype = self.plugin.game.type_short  # type: ignore
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {'elo': elo}}
        mocked_balance_plugin = Mock()
        mocked_balance_plugin.ratings = ratings
        self.plugin._loaded_plugins["balance"] = mocked_balance_plugin  # pylint: disable=protected-access

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:  # pylint: disable=protected-access
            del self.plugin._loaded_plugins["balance"]  # pylint: disable=protected-access

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_team_switch_attempt_no_game_running(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_last_new_player_changes_back_to_spec(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        last_new_player = fake_player(42, "Last New Player", "red")
        connected_players(red_player, blue_player, last_new_player)

        self.plugin.last_new_player_id = last_new_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(last_new_player, "red", "spectator")

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id is None

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_attempt_game_in_warmup(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "any")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_not_from_spectator(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "red")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_to_spectator(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "blue", "spectator")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_rebalance_not_set_for_teamswitch_events(self):
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_no_balance_plugin_loaded(self):
        self.setup_no_balance_plugin()
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert return_code == minqlx.RET_NONE
        assert_plugin_sent_to_console(matches(".*not possible.*"))

    def test_handle_team_switch_attempt_unsupported_gametype(self, game_in_progress):
        game_in_progress.type_short = "rr"
        self.setup_balance_ratings([])
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_first_player_joins(self):
        self.setup_balance_ratings([])
        player = fake_player(42, "Fake Player")
        connected_players(player)

        return_code = self.plugin.handle_team_switch_attempt(player, "spectator", "red")

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id == player.steam_id

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_second_player_joins_same_team(self):
        self.setup_balance_ratings([])
        red_player = fake_player(123, "Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (new_player, 1200)])
        self.plugin.last_new_player_id = red_player.steam_id

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert return_code == minqlx.RET_STOP_ALL
        assert self.plugin.last_new_player_id is None
        assert_player_was_put_on(new_player, "blue")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_third_player_joins(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id == new_player.steam_id

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_fourth_player_joins_no_last_id_set(self):
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(246, "Blue Player", "blue")
        new_red_player = fake_player(41, "New Red Player", "red")
        new_player = fake_player(42, "New Player", "spectator")
        connected_players(red_player, blue_player, new_red_player, new_player)

        self.setup_balance_ratings([(red_player, 1200), (blue_player, 1200),
                                    (new_red_player, 1200), (new_player, 1200)])

        return_code = self.plugin.handle_team_switch_attempt(new_player, "spectator", "red")

        assert return_code == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
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

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id is None

    @pytest.mark.usefixtures("game_in_progress")
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

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id is None

    @pytest.mark.usefixtures("game_in_progress")
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

        assert return_code == minqlx.RET_STOP_ALL
        assert self.plugin.last_new_player_id is None
        assert_player_was_put_on(new_player, "blue")

    @pytest.mark.usefixtures("game_in_progress")
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

        assert return_code == minqlx.RET_STOP_ALL
        assert self.plugin.last_new_player_id is None
        assert_player_was_put_on(new_player, "blue")
        assert_player_was_put_on(new_blue_player, "red")

    @pytest.mark.usefixtures("game_in_progress")
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

        assert return_code == minqlx.RET_NONE
        assert self.plugin.last_new_player_id is None
        assert_player_was_put_on(new_player, "blue", times=0)
        assert_player_was_put_on(new_blue_player, "red")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_resets_last_new_player_id(self):
        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        self.plugin.handle_round_start(3)

        assert self.plugin.last_new_player_id is None

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_round_end_no_game_running(self):
        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_wrong_gametype(self, game_in_progress):
        game_in_progress.type_short = "rr"

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_roundlimit_reached(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 8
        game_in_progress.blue_score = 3

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_suggestion_threshold_not_met(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 4
        game_in_progress.blue_score = 3

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_teams_unbalanced(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 1

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"), blue_player1)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_teams_callback_called(self, mocker, mocked_balance_plugin, game_in_progress):
        add_request_spy = mocker.spy(mocked_balance_plugin, "add_request")
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 1

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        players = {p.steam_id: "ca" for p in [red_player1, red_player2, blue_player1, blue_player2]}

        add_request_spy.assert_called_once_with(players, mocked_balance_plugin.callback_teams, minqlx.CHAT_CHANNEL)

    def test_handle_round_end_no_balance_plugin(self, game_in_progress):
        self.setup_no_balance_plugin()
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 1

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)

        return_code = undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert return_code == minqlx.RET_NONE

    def test_handle_round_end_winner_is_tracked_for_winning_streak(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 3
        game_in_progress.blue_score = 1

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)
        self.plugin.winning_teams = ["red", "blue", "red"]

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        assert self.plugin.winning_teams == ["red", "blue", "red", "red"]

    def test_handle_round_end_winning_streak_triggers_teams_callback(
            self, mocker, mocked_balance_plugin, game_in_progress):
        add_request_spy = mocker.spy(mocked_balance_plugin, "add_request")
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 3
        game_in_progress.blue_score = 1

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)
        self.plugin.winning_teams = ["blue", "red", "red"]

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        players = {p.steam_id: "ca" for p in [red_player1, red_player2, blue_player1, blue_player2]}
        add_request_spy.assert_called_once_with(players, mocked_balance_plugin.callback_teams, minqlx.CHAT_CHANNEL)

    def test_handle_round_end_winning_streak_triggers_teams_callback_already_called_multiple_times(
            self, mocker, mocked_balance_plugin, game_in_progress):
        add_request_spy = mocker.spy(mocked_balance_plugin, "add_request")
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 4
        game_in_progress.blue_score = 3

        red_player1 = fake_player(123, "Red Player1", "red")
        red_player2 = fake_player(456, "Red Player2", "red")
        blue_player1 = fake_player(246, "Blue Player1", "blue")
        blue_player2 = fake_player(975, "Blue Player2", "blue")
        connected_players(red_player1, red_player2, fake_player(42, "Spec Player", "spectator"),
                          blue_player1, blue_player2)
        self.plugin.winning_teams = ["blue", "blue", "blue", "red", "red", "red", "red"]

        undecorated(self.plugin.handle_round_end)(self.plugin, {"TEAM_WON": "RED"})

        add_request_spy.assert_not_called()

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_game_start_initializes_winning_teams(self):
        self.plugin.winning_teams = ["red", "draw", "blue"]

        self.plugin.handle_reset_winning_teams()

        assert self.plugin.winning_teams == []
