import logging
import time

import pytest
import redis
import requests

from mockito import mock, when, unstub, verify, spy2, patch  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import equal_to, assert_that, has_item
from requests import Response, RequestException
from undecorated import undecorated

from minqlx_plugin_test import (
    connected_players,
    fake_player,
    setup_cvars,
    assert_plugin_sent_to_console,
)

import minqlx
from minqlx import Plugin, CHAT_CHANNEL

from merciful_elo_limit import merciful_elo_limit, ConnectThread


class ThreadContextManager:
    def __init__(self, plugin):
        self.plugin = plugin

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        for steam_id, thread in self.plugin.connectthreads.items():
            if thread.is_alive():
                thread.join()
                self.plugin.handle_player_connect(
                    fake_player(steam_id, name="cleanup player")
                )


class TestMercifulEloLimit:
    @pytest.fixture(name="merciful_db")
    def merciful_db(self):
        self.plugin.database = redis.Redis  # type: ignore
        db = mock(spec=redis.Redis)
        self.plugin._db_instance = db  # pylint: disable=protected-access

        when(db).__getitem__(any_).thenReturn("42")  # pylint: disable=C2801
        when(db).exists(any_).thenReturn(False)
        when(db).zremrangebyscore(any_, any_, any_).thenReturn(None)
        when(db).zadd(any_, any_, any_).thenReturn(None)

        yield db
        unstub()

    @pytest.fixture(name="chat_channel")
    def chat_channel(self, mock_channel):
        original_chat_channel = minqlx.CHAT_CHANNEL
        minqlx.CHAT_CHANNEL = mock_channel
        yield
        minqlx.CHAT_CHANNEL = original_chat_channel

    def setup_method(self):
        setup_cvars(
            {
                "qlx_mercifulelo_minelo": "800",
                "qlx_mercifulelo_applicationgames": "10",
                "qlx_mercifulelo_daysbanned": "30",
                "qlx_owner": "42",
            }
        )

        self.plugin = merciful_elo_limit()
        self.plugin.remove_thread = lambda _: None

    def teardown_method(self):
        if (
            "mybalance" in self.plugin._loaded_plugins  # pylint: disable=protected-access
        ):
            del minqlx.Plugin._loaded_plugins[
                "mybalance"
            ]  # pylint: disable=protected-access
        if "balance" in self.plugin._loaded_plugins:  # pylint: disable=protected-access
            del minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
                "balance"
            ]
        if (
            "balancetwo" in self.plugin._loaded_plugins  # pylint: disable=protected-access
        ):
            del minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
                "balancetwo"
            ]
        unstub()

    def setup_balance_ratings(self, player_elos):
        gametype = None
        if len(player_elos) > 0:
            gametype = self.plugin.game.type_short  # type: ignore
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {"elo": elo}}
        minqlx.Plugin._loaded_plugins["balance"] = mock(  # pylint: disable=protected-access
            {"ratings": ratings}
        )

    # noinspection PyMethodMayBeStatic
    def setup_no_balance_plugin(self):
        if (
            "balance" in minqlx.Plugin._loaded_plugins  # pylint: disable=protected-access
        ):
            del minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
                "balance"
            ]
        if (
            "balancetwo" in minqlx.Plugin._loaded_plugins  # pylint: disable=protected-access
        ):
            del minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
                "balancetwo"
            ]

    # noinspection PyMethodMayBeStatic
    def setup_exception_list(self, plugin, players):
        balance_plugin = mock(Plugin)
        balance_plugin.exceptions = [player.steam_id for player in players]
        minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
            plugin
        ] = balance_plugin

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_resets_tracked_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.tracked_player_sids = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.tracked_player_sids, equal_to(set()))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_resets_announced_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.announced_player_elos = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.announced_player_elos, equal_to(set()))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_map_change_fetches_elos_of_connected_players(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 1200)})

        self.plugin.handle_map_change("thunderstruck", "ca")

        verify(
            self.plugin._loaded_plugins["balance"]  # pylint: disable=protected-access
        ).add_request(
            {player1.steam_id: "ca", player2.steam_id: "ca"},
            self.plugin.callback_ratings,
            CHAT_CHANNEL,
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_player_in_mybalance_exception_list(self):
        player = fake_player(123, "Fake Player1", team="spectator")
        self.setup_exception_list("mybalance", [player])

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_player_in_balancetwo_exception_list(self):
        player = fake_player(123, "Fake Player1", team="spectator")
        self.setup_exception_list("balancetwo", [player])

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_player_connect_with_no_game_setup(self):
        player = fake_player(123, "Fake Player1", team="spectator")

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_untracked_player(self, merciful_db):
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(False)

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_tracked_player_fetches_ratings(
        self, merciful_db
    ):
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(False)
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to("Fetching your skill rating..."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_tracked_player_ratings_fetched(
        self, merciful_db
    ):
        when(requests.Session).get(...).thenReturn(None)

        setup_cvars(
            {
                "qlx_mercifulelo_minelo": "800",
                "qlx_mercifulelo_applicationgames": "10",
                "qlx_mercifulelo_daysbanned": "30",
                "qlx_owner": "42",
                "qlx_balanceApi": "belo",
            }
        )

        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(player)

        verify(requests.Session).get(
            f"http://qlstats.net/belo/{player.steam_id}", timeout=any_
        )

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_fetch_elos_of_players_with_no_game_setup(self):
        self.setup_balance_ratings({})

        self.plugin.fetch_elos_of_players([])

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_unsupported_gametype(
        self, merciful_db, game_in_progress
    ):
        game_in_progress.type_short = "unsupported"
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(True)
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_unavailable_elo_is_allowed_to_connect(
        self, merciful_db, game_in_progress
    ):
        game_in_progress.type_short = "ca"
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(True)
        when(connect_thread).elo_for("ca").thenReturn(None)
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_elo_is_sufficient_to_connect(
        self, merciful_db, game_in_progress
    ):
        game_in_progress.type_short = "ca"
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(True)
        when(connect_thread).elo_for("ca").thenReturn("1200")
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_remaining_application_games(
        self, merciful_db, game_in_progress
    ):
        game_in_progress.type_short = "ca"
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player.steam_id}:minelo:games", any_, any_
        ).thenReturn([1])

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(True)
        when(connect_thread).elo_for("ca").thenReturn(400)
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_with_no_remaining_application_games(
        self, merciful_db, game_in_progress
    ):
        game_in_progress.type_short = "ca"
        player = fake_player(123, "Fake Player1", team="spectator")
        when(merciful_db).exists(
            f"minqlx:players:{player.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player.steam_id}:minelo:games", any_, any_
        ).thenReturn([1] * 10)

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_parsed().thenReturn(True)
        when(connect_thread).elo_for("ca").thenReturn(400)
        self.plugin.connectthreads[player.steam_id] = connect_thread

        return_code = self.plugin.handle_player_connect(player)

        assert_that(
            return_code,
            matches(
                "You used up all your.*application matches. Next application game available at.*"
            ),
        )

    @pytest.mark.parametrize(
        "game_in_progress", ["game_type=unsupported"], indirect=True
    )
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

        verify(
            self.plugin._loaded_plugins["balance"]  # pylint: disable=protected-access
        ).add_request(
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

    @pytest.mark.parametrize(
        "game_in_progress", ["game_type=unsupported"], indirect=True
    )
    def test_callback_ratings_with_unsupported_game_type(
        self, game_in_progress, merciful_db
    ):
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
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123, 455])

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(
            matches(".*Skill warning.*8.*matches left.*")
        )
        verify(player2).tell(
            matches(
                ".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"
            )
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_announces_information_to_other_players(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(time.sleep, lambda _: None)
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123, 456])

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(
            matches("Fake Player2.*is below.*, but has.*8.*application matches left.*")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_announces_information_to_other_players_just_once_per_connect(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})
        self.plugin.announced_player_elos = [456]

        patch(time.sleep, lambda _: None)
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123, 456])

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(
            matches("Player.*is below.*, but has 8 application matches left.*"), times=0
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_with_a_player_already_tracked(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})
        self.plugin.tracked_player_sids.add(player2.steam_id)

        patch(time.sleep, lambda _: None)
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123, 456])

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(
            matches("Player.*is below.*, but has 8 application matches left.*"), times=0
        )
        verify(player2, times=0).center_print(any_)
        verify(player2, times=0).tell(any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_makes_exception_for_player_in_exception_list(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list("mybalance", [player3])

        patch(time.sleep, lambda _: None)
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123, 456])

        self.plugin.callback_ratings([player1, player2, player3], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(
            matches(".*Skill warning.*8.*matches left.*")
        )
        verify(player2).tell(
            matches(
                ".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"
            )
        )
        verify(player3, times=0).center_print(any_)
        verify(player3, times=0).tell(any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_warns_low_elo_player_when_application_games_not_set(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(time.sleep, lambda _: None)
        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([123])

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(
            matches(".*Skill warning.*9.*matches left.*")
        )
        verify(player2).tell(
            matches(
                ".*Skill Warning.*qlstats.*below.*800.*9.*of 10 application matches.*"
            )
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_bans_low_elo_players_that_used_up_their_application_games(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        # noinspection PyPropertyAccess
        player2.connection_state = "active"
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([456] * 11)

        patch(minqlx.next_frame, lambda func: func)

        when(merciful_db).delete(any_).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2).kick(matches("You used up your.*application games.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_ratings_leaves_pending_low_elo_players_that_used_up_their_application_games(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        # noinspection PyPropertyAccess
        player2.connection_state = "pending"
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([456] * 11)

        patch(minqlx.next_frame, lambda func: func)

        when(merciful_db).delete(any_).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=0).kick(any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_increases_application_games_for_untracked_player(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        self.plugin.handle_round_start(1)

        verify(merciful_db).zadd(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_makes_exception_for_player_in_mybalance_exception_list(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list("mybalance", [player3])

        self.plugin.handle_round_start(1)

        verify(merciful_db).zadd(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        )
        verify(merciful_db, times=0).zadd(
            f"minqlx:players:{player3.steam_id}:minelo:games", any_, any_
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_starts_tracking_for_low_elo_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        self.plugin.handle_round_start(1)

        # noinspection PyTypeChecker
        assert_that(self.plugin.tracked_player_sids, has_item(player2.steam_id))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_resets_above_games_for_low_elo_player(
        self, merciful_db
    ):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        self.plugin.handle_round_start(1)

        verify(merciful_db).zremrangebyscore(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        )
        verify(merciful_db).zadd(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_round_start_skips_already_tracked_player(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.plugin.tracked_player_sids.add(player2.steam_id)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        self.plugin.handle_round_start(1)

        verify(merciful_db, times=0).zremrangebyscore(any_, any_, any_)
        verify(merciful_db, times=0).zadd(any_, any_, any_)

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_round_start_with_no_game_running(self, merciful_db):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({})

        self.plugin.handle_round_start(2)

        verify(
            self.plugin._loaded_plugins["balance"],  # pylint: disable=protected-access
            times=0,
        ).add_request(any_, any_, any_)

    @pytest.mark.parametrize(
        "game_in_progress", ["game_type=unsupported"], indirect=True
    )
    def test_handle_round_start_with_unsupported_gametype(
        self, game_in_progress, merciful_db
    ):
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
    def test_cmd_mercis_shows_currently_connected_merciful_players(
        self, mock_channel, merciful_db
    ):
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings(
            {(player, 1400), (player1, 801), (player2, 799), (player3, 900)}
        )

        when(merciful_db).exists(
            f"minqlx:players:{player1.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player1.steam_id}:minelo:games", any_, any_
        ).thenReturn([1] * 2)
        when(merciful_db).exists(
            f"minqlx:players:{player2.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        ).thenReturn([1] * 3)

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, "!mercis", mock_channel)

        mock_channel.assert_was_replied(
            matches(r"Fake Player2 \(elo: 799\):.*7.*application matches left")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mercis_replies_to_main_channel_instead_of_team_chat(
        self, chat_channel, merciful_db
    ):
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings(
            {(player, 1400), (player1, 801), (player2, 799), (player3, 900)}
        )

        when(merciful_db).exists(
            f"minqlx:players:{player1.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player1.steam_id}:minelo:games", any_, any_
        ).thenReturn([1] * 2)
        when(merciful_db).exists(
            f"minqlx:players:{player2.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{player2.steam_id}:minelo:games", any_, any_
        ).thenReturn([1] * 3)

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, "!mercis", minqlx.BLUE_TEAM_CHAT_CHANNEL)

        verify(minqlx.CHAT_CHANNEL).reply(
            matches(r"Fake Player2 \(elo: 799\):.*7.*application matches left")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mercis_shows_no_mercis_if_no_player_using_their_application_matches(
        self, merciful_db, chat_channel
    ):
        player = fake_player(666, "Cmd using Player")
        connected_players(player)
        self.setup_balance_ratings({(player, 1400)})

        when(merciful_db).zrangebyscore(any_, any_, any_).thenReturn([])

        # noinspection PyTypeChecker
        self.plugin.cmd_mercis(player, "!mercis", minqlx.CHAT_CHANNEL)

        verify(minqlx.CHAT_CHANNEL).reply(
            "There is currently no player within their application period connected."
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_with_no_player_provided(self):
        player = fake_player(666, "Cmd using Player")
        connected_players(player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(player, "!merci", minqlx.CHAT_CHANNEL)

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_with_non_existent_player(self):
        player = fake_player(666, "Cmd using Player")
        connected_players(player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(
            player, ["!merci", "non-existing-player"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        # noinspection PyUnresolvedReferences
        player.assert_was_told(matches(".*no players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_with_more_than_once_matching_player(self):
        player = fake_player(666, "Cmd using Player")
        matching_player1 = fake_player(123, "matching-Player1", _id=11)
        matching_player2 = fake_player(456, "matching-Player2", _id=12)
        connected_players(player, matching_player1, matching_player2)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(
            player, ["!merci", "matching"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        # noinspection PyUnresolvedReferences
        player.assert_was_told(
            matches("A total of .+2.* players matched for matching:")
        )
        # noinspection PyUnresolvedReferences
        player.assert_was_told(
            matches(
                f".*{matching_player1.id}.*{matching_player1.name}\n"
                f".*{matching_player2.id}.*{matching_player2.name}.*"
            )
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_grants_another_application_match_by_name(
        self, merciful_db, chat_channel
    ):
        player = fake_player(666, "Cmd using Player")
        tracked_player = fake_player(123, "TrackedPlayer")
        when(merciful_db).exists(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", any_, any_
        ).thenReturn([123, 456, 789])
        when(merciful_db).zrem(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", 789
        ).thenReturn(None)
        connected_players(player, tracked_player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(
            player, ["!merci", "TrackedPlayer"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        verify(minqlx.CHAT_CHANNEL).reply(
            matches("TrackedPlayer.* has been granted another application game")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_grants_another_application_match_by_steam_id(
        self, merciful_db, chat_channel
    ):
        player = fake_player(666, "Cmd using Player")
        tracked_player = fake_player(123, "TrackedPlayer")
        when(merciful_db).exists(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", any_, any_
        ).thenReturn([123, 456, 789])
        when(merciful_db).zrem(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", 789
        ).thenReturn(None)
        connected_players(player, tracked_player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(
            player, ["!merci", f"{tracked_player.steam_id}"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        verify(minqlx.CHAT_CHANNEL).reply(
            matches("TrackedPlayer.* has been granted another application game")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_merci_grants_another_application_match_by_id_in_game(
        self, merciful_db, chat_channel
    ):
        player = fake_player(666, "Cmd using Player")
        tracked_player = fake_player(123, "TrackedPlayer")
        when(merciful_db).exists(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games"
        ).thenReturn(True)
        when(merciful_db).zrangebyscore(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", any_, any_
        ).thenReturn([123, 456, 789])
        when(merciful_db).zrem(
            f"minqlx:players:{tracked_player.steam_id}:minelo:games", 789
        ).thenReturn(None)
        connected_players(player, tracked_player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_merci(
            player, ["!merci", f"{tracked_player.id}"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        verify(minqlx.CHAT_CHANNEL).reply(
            matches("TrackedPlayer.* has been granted another application game")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_remove_thread_removes_existing_connect_thread(self):
        plugin = merciful_elo_limit()
        # noinspection PyTypeChecker
        plugin.connectthreads[1234] = "asdf"

        undecorated(plugin.remove_thread)(plugin, 1234)

        assert_that(plugin.connectthreads, equal_to({}))

    @pytest.mark.usefixtures("game_in_progress")
    def test_remove_thread_does_nothing_if_thread_does_not_exist(self):
        plugin = merciful_elo_limit()
        # noinspection PyTypeChecker
        plugin.connectthreads[1234] = "asdf"

        undecorated(plugin.remove_thread)(plugin, 12345)

        assert_that(plugin.connectthreads, equal_to({1234: "asdf"}))


class TestConnectThread:
    @pytest.fixture
    def qlstats_response(self):
        response = mock(spec=Response)
        response.status_code = 200
        response.text = ""
        spy2(requests.Session.get)
        when(requests.Session).get(...).thenReturn(response)
        yield response
        unstub(response)

    @pytest.fixture(name="mocked_logger")
    def mocked_logger(self):
        spy2(minqlx.get_logger)
        mocked_logger = mock(logging.Logger)
        when(minqlx).get_logger("merciful_elo_limit").thenReturn(mocked_logger)
        when(mocked_logger).debug(any_).thenReturn(None)
        yield mocked_logger
        unstub(mocked_logger)

    def setup_method(self):
        self.connect_thread = ConnectThread(123, "elo")

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_elo_for_when_result_is_not_parsed_yet(self):
        return_code = self.connect_thread.elo_for("ca")

        assert_that(return_code, equal_to(None))

    def test_elo_for_when_result_did_not_contain_elo(self):
        self.connect_thread._is_parsed.set()  # pylint: disable=protected-access

        return_code = self.connect_thread.elo_for("ca")

        assert_that(return_code, equal_to(None))

    def test_elo_for_when_ratings_have_been_stored(self):
        self.connect_thread._is_parsed.set()  # pylint: disable=protected-access
        self.connect_thread._elo = {  # pylint: disable=protected-access
            "ca": {"elo": 1234}
        }

        return_code = self.connect_thread.elo_for("ca")

        assert_that(return_code, equal_to(1234))

    def test_exception_when_fetching_qlstats_response(self, mocked_logger):
        when(requests.Session).get(...).thenRaise(RequestException("Test Exception"))

        self.connect_thread.run()

        assert_that(self.connect_thread.is_parsed(), equal_to(False))
        verify(mocked_logger).debug(matches("request exception: Test Exception"))

    def test_with_missing_players_section_in_qlstats_response(
        self, qlstats_response, mocked_logger
    ):
        when(qlstats_response).json().thenReturn({})

        self.connect_thread.run()

        assert_that(self.connect_thread.is_parsed(), equal_to(False))
        verify(mocked_logger).debug(matches(".*Invalid response content.*"))

    def test_run_with_wrong_player_in_qlstats_response(
        self, qlstats_response, mocked_logger
    ):
        when(qlstats_response).json().thenReturn(
            {"players": [{"steamid": str(456), "ca": {"elo": 1234}}]}
        )

        self.connect_thread.run()

        assert_that(self.connect_thread.is_parsed(), equal_to(False))
        verify(mocked_logger).debug(
            matches(".*did not include data for.*requested player.*")
        )

    def test_proper_qlstats_response(self, qlstats_response):
        when(qlstats_response).json().thenReturn(
            {"players": [{"steamid": str(123), "ca": {"elo": 1234}}]}
        )

        self.connect_thread.run()

        assert_that(self.connect_thread.is_parsed(), equal_to(True))
        assert_that(self.connect_thread.elo_for("ca"), equal_to(1234))
