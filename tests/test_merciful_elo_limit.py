import time
import logging

import pytest
import redis

from minqlx_plugin_test import (
    connected_players,
    fake_player,
    assert_plugin_sent_to_console,
    setup_cvars,
)

from mockito import mock, when, unstub, verify, patch, spy2, when2  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import equal_to, assert_that, has_item

import minqlx
from minqlx import Plugin, CHAT_CHANNEL

from merciful_elo_limit import merciful_elo_limit


class TestMercifulEloLimit:
    @pytest.fixture(name="merciful_db")
    def merciful_db(self):
        self.plugin.database = redis.Redis  # type: ignore
        db = mock(spec=redis.Redis)
        self.plugin._db_instance = db  # pylint: disable=protected-access

        when(db).__getitem__(any_).thenReturn("42")  # pylint: disable=C2801
        yield db
        unstub()

    def setup_method(self):
        setup_cvars(
            {
                "qlx_mercifulelo_minelo": "800",
                "qlx_mercifulelo_applicationgames": "10",
                "qlx_mercifulelo_abovegames": "10",
                "qlx_mercifulelo_daysbanned": "30",
                "qlx_owner": "42",
            }
        )

        self.plugin = merciful_elo_limit()

    @staticmethod
    def teardown_method():
        unstub()

    def setup_balance_ratings(self, player_elos):
        gametype = None
        if len(player_elos) > 0:
            gametype = self.plugin.game.type_short  # type: ignore
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {"elo": elo}}
        self.plugin._loaded_plugins["balance"] = mock({"ratings": ratings})  # pylint: disable=protected-access

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:  # pylint: disable=protected-access
            del self.plugin._loaded_plugins["balance"]  # pylint: disable=protected-access

    def setup_exception_list(self, players):
        mybalance_plugin = mock(Plugin)
        mybalance_plugin.exceptions = [player.steam_id for player in players]
        self.plugin._loaded_plugins["mybalance"] = mybalance_plugin  # pylint: disable=protected-access

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_resets_tracked_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.tracked_player_sids = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.tracked_player_sids, equal_to([]))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_resets_announced_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.announced_player_elos = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.announced_player_elos, equal_to([]))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_fetches_elos_of_connected_players(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 1200)})

        self.plugin.handle_map_change("thunderstruck", "ca")

        verify(self.plugin._loaded_plugins["balance"]).add_request(  # pylint: disable=protected-access
            {player1.steam_id: "ca", player2.steam_id: "ca"},
            self.plugin.callback_ratings,
            CHAT_CHANNEL,
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_fetches_elo_of_connecting_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connecting_player = fake_player(789, "Connecting Player")
        connected_players(player1, player2, connecting_player)
        self.setup_balance_ratings({(player1, 900), (player2, 1200), (connecting_player, 1542)})

        self.plugin.handle_player_connect(connecting_player)

        verify(self.plugin._loaded_plugins["balance"]).add_request(  # pylint: disable=protected-access
            {connecting_player.steam_id: "ca"},
            self.plugin.callback_ratings,
            CHAT_CHANNEL,
        )

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_fetch_elos_of_players_with_no_game_setup(self):
        self.setup_balance_ratings({})

        self.plugin.fetch_elos_of_players([])

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.parametrize("game_in_progress", ["game_type=unsupported"], indirect=True)
    def test_fetch_elos_of_players_with_unsupported_gametype(self, game_in_progress):
        self.setup_balance_ratings({})

        self.plugin.fetch_elos_of_players([])

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_fetch_elos_of_player_with_no_balance_plugin(self):
        mocked_logger = mock(spec=logging.Logger, strict=False)
        spy2(minqlx.get_logger)
        when(minqlx).get_logger(self.plugin).thenReturn(mocked_logger)
        self.setup_no_balance_plugin()

        self.plugin.fetch_elos_of_players([])

        verify(mocked_logger).warning(matches("Balance plugin not found.*"))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_round_countdown_with_no_game(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.handle_round_countdown(1)

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_countdown_fetches_elos_of_players_in_teams(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 1200), (player3, 1600)})

        self.plugin.handle_round_countdown(4)

        verify(self.plugin._loaded_plugins["balance"]).add_request(  # pylint: disable=protected-access
            {player1.steam_id: "ca", player2.steam_id: "ca"},
            self.plugin.callback_ratings,
            CHAT_CHANNEL,
        )

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_callback_ratings_with_no_game_running(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.callback_ratings([], minqlx.CHAT_CHANNEL)

        verify(merciful_db, times=0).get(any_)

    @pytest.mark.parametrize("game_in_progress", ["game_type=unsupported"], indirect=True)
    def test_callback_ratings_with_unsupported_game_type(self, game_in_progress, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.callback_ratings([], minqlx.CHAT_CHANNEL)

        verify(merciful_db, times=0).get(any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_warns_low_elo_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(time.sleep, lambda _: None)
        when(merciful_db).get(any_).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*8.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_announces_information_to_other_players(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(time.sleep, lambda _: None)
        when(merciful_db).get(any_).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(matches("Fake Player2.*is below.*, but has.*8.*application matches left.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_announces_information_to_other_players_just_once_per_connect(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})
        self.plugin.announced_player_elos = [456]

        patch(time.sleep, lambda _: None)
        when(merciful_db).get(any_).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(matches("Player.*is below.*, but has 8 application matches left.*"), times=0)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_makes_exception_for_player_in_exception_list(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list([player3])

        patch(time.sleep, lambda _: None)
        when(merciful_db).get(any_).thenReturn("2")

        self.plugin.callback_ratings([player1, player2, player3], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*8.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"))
        verify(player3, times=0).center_print(any_)
        verify(player3, times=0).tell(any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_warns_low_elo_player_when_application_games_not_set(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(time.sleep, lambda _: None)
        when(merciful_db).get(any_).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*10.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*10.*of 10 application matches.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_bans_low_elo_players_that_used_up_their_application_games(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).get(any_).thenReturn("11")
        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any_, any_, any_).thenReturn(None)

        patch(minqlx.next_frame, lambda func: func)

        when(merciful_db).delete(any_).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(minqlx.COMMANDS).handle_input(any_, any_, any_)
        verify(merciful_db).delete(f"minqlx:players:{player2.steam_id}:minelo:abovegames")
        verify(merciful_db).delete(f"minqlx:players:{player2.steam_id}:minelo:freegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_increases_application_games_for_untracked_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(False)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).incr(f"minqlx:players:{player2.steam_id}:minelo:freegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_makes_exception_for_player_in_exception_list(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list([player3])

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(False)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).incr(f"minqlx:players:{player2.steam_id}:minelo:freegames")
        verify(merciful_db, times=0).incr(f"minqlx:players:{player3.steam_id}:minelo:freegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_starts_tracking_for_low_elo_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(False)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        # noinspection PyTypeChecker
        assert_that(self.plugin.tracked_player_sids, has_item(player2.steam_id))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_resets_above_games_for_low_elo_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(True)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).delete(f"minqlx:players:{player2.steam_id}:minelo:abovegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_increases_above_games_for_application_games_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(True)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).incr(f"minqlx:players:{player2.steam_id}:minelo:abovegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_increases_above_games_for_application_games_player_with_no_aobve_games_set(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(merciful_db).get(any_).thenReturn("1")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(True)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).incr(f"minqlx:players:{player2.steam_id}:minelo:abovegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_starts_tracking_of_above_elo_players_for_application_games_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(merciful_db).get(any_).thenReturn("3")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(True)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        # noinspection PyTypeChecker
        assert_that(self.plugin.tracked_player_sids, has_item(player2.steam_id))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_removes_minelo_db_entries_for_above_elo_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(merciful_db).get(any_).thenReturn("11")
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(True)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db).delete(f"minqlx:players:{player2.steam_id}:minelo:freegames")
        verify(merciful_db).delete(f"minqlx:players:{player2.steam_id}:minelo:abovegames")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_skips_already_tracked_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.plugin.tracked_player_sids.append(player2.steam_id)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).get(any_).thenReturn(3)
        when(merciful_db).delete(any_).thenReturn(None)
        when(merciful_db).exists(any_).thenReturn(False)
        when(merciful_db).incr(any_).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(merciful_db, times=0).delete(any_)
        verify(merciful_db, times=0).delete(any_)

    @pytest.mark.parametrize("game_in_progress", ["game_type=unsupported"], indirect=True)
    def test_handle_round_start_with_unsupported_gametype(self, game_in_progress, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({})

        self.plugin.handle_round_start(2)

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_with_no_balance_plugin(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        mocked_logger = mock(spec=logging.Logger, strict=False)
        spy2(minqlx.get_logger)
        when(minqlx).get_logger(self.plugin).thenReturn(mocked_logger)
        self.setup_no_balance_plugin()

        self.plugin.handle_round_start(5)

        verify(mocked_logger, atleast=1).warning(matches("Balance plugin not found.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mercequal_toshows_currently_connected_merciful_players(self, mock_channel, merciful_db):
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings({(player, 1400), (player1, 801), (player2, 799), (player3, 900)})

        when(merciful_db).get(f"minqlx:players:{player1.steam_id}:minelo:freegames").thenReturn("2")
        when(merciful_db).get(f"minqlx:players:{player2.steam_id}:minelo:freegames").thenReturn("3")
        when(merciful_db).get(f"minqlx:players:{player1.steam_id}:minelo:abovegames").thenReturn("6")
        when(merciful_db).get(f"minqlx:players:{player.steam_id}:minelo:freegames").thenReturn(None)
        when(merciful_db).get(f"minqlx:players:{player3.steam_id}:minelo:freegames").thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, ["!mercis"], mock_channel)

        mock_channel.assert_was_replied(
            matches(r"Fake Player1 \(elo: 801\):.*8.*application matches left,.*6.*matches above.*")
        )
        mock_channel.assert_was_replied(matches(r"Fake Player2 \(elo: 799\):.*7.*application matches left"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mercequal_toreplies_to_main_cbannel_instead_of_team_chat(self, mock_channel, merciful_db):
        minqlx.CHAT_CHANNEL = mock_channel
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings({(player, 1400), (player1, 801), (player2, 799), (player3, 900)})

        when(merciful_db).get(f"minqlx:players:{player1.steam_id}:minelo:freegames").thenReturn("2")
        when(merciful_db).get(f"minqlx:players:{player2.steam_id}:minelo:freegames").thenReturn("3")
        when(merciful_db).get(f"minqlx:players:{player1.steam_id}:minelo:abovegames").thenReturn("6")
        when(merciful_db).get(f"minqlx:players:{player.steam_id}:minelo:freegames").thenReturn(None)
        when(merciful_db).get(f"minqlx:players:{player3.steam_id}:minelo:freegames").thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, ["!mercis"], minqlx.BLUE_TEAM_CHAT_CHANNEL)

        mock_channel.assert_was_replied(
            matches(r"Fake Player1 \(elo: 801\):.*8.*application matches left,.*6.*matches above.*")
        )
        mock_channel.assert_was_replied(matches(r"Fake Player2 \(elo: 799\):.*7.*application matches left"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mercequal_toshows_no_mercequal_toif_no_player_using_their_application_matches(self, merciful_db):
        player = fake_player(666, "Cmd using Player")
        connected_players(player)
        self.setup_balance_ratings({(player, 1400)})

        when(merciful_db).get(any_).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, ["!mercis"], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(any_, times=0)
