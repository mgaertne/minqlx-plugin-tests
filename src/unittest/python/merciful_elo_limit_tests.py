from minqlx_plugin_test import *

import logging
import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from redis import Redis

from merciful_elo_limit import *


class MercifulEloLimitTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "zmq_stats_enable": ("0", None),
            "qlx_mercifulelo_minelo": (800, int),
            "qlx_mercifulelo_applicationgames": (10, int),
            "qlx_mercifulelo_abovegames": (10, int),
            "qlx_mercifulelo_daysbanned": (30, int)
        })
        spy2(minqlx.get_cvar)
        when(minqlx).get_cvar("qlx_owner").thenReturn("42")

        setup_game_in_progress()
        self.plugin = merciful_elo_limit()
        self.reply_channel = mocked_channel()

        self.plugin.database = Redis
        self.db = mock(Redis)
        self.plugin._db_instance = self.db

        when(self.db).__getitem__(any).thenReturn("42")

    def tearDown(self):
        unstub()

    def setup_balance_ratings(self, player_elos):
        gametype = None
        if len(player_elos) > 0:
            gametype = self.plugin.game.type_short
        ratings = {}
        for player, elo in player_elos:
            ratings[player.steam_id] = {gametype: {'elo': elo}}
        self.plugin._loaded_plugins["balance"] = mock({'ratings': ratings})

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:
            del self.plugin._loaded_plugins["balance"]

    def setup_exception_list(self, players):
        mybalance_plugin = mock(Plugin)
        mybalance_plugin.exceptions = [player.steam_id for player in players]
        self.plugin._loaded_plugins["mybalance"] = mybalance_plugin

    def test_handle_map_change_resets_tracked_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.tracked_player_sids = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.tracked_player_sids, is_([]))

    def test_handle_map_change_resets_announced_player_ids(self):
        connected_players()
        self.setup_balance_ratings([])
        self.plugin.announced_player_elos = [123, 455]

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.announced_player_elos, is_([]))

    def test_handle_map_change_fetches_elos_of_connected_players(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 1200)})

        self.plugin.handle_map_change("thunderstruck", "ca")

        verify(self.plugin._loaded_plugins["balance"]).add_request(
            {player1.steam_id: 'ca', player2.steam_id: 'ca'},
            self.plugin.callback_ratings, minqlx.CHAT_CHANNEL
        )

    def test_handle_player_connect_fetches_elo_of_connecting_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connecting_player = fake_player(789, "Connecting Player")
        connected_players(player1, player2, connecting_player)
        self.setup_balance_ratings({(player1, 900), (player2, 1200), (connecting_player, 1542)})

        self.plugin.handle_player_connect(connecting_player)

        verify(self.plugin._loaded_plugins["balance"]).add_request(
            {connecting_player.steam_id: 'ca'},
            self.plugin.callback_ratings, minqlx.CHAT_CHANNEL
        )

    def test_fetch_elos_of_players_with_no_game_setup(self):
        setup_no_game()
        self.setup_balance_ratings({})

        self.plugin.fetch_elos_of_players([])

        verify(self.plugin._loaded_plugins["balance"], times=0).add_request(any, any, any)

    def test_fetch_elos_of_players_with_unsupported_gametype(self):
        setup_game_in_progress("unsupported")
        self.setup_balance_ratings({})

        self.plugin.fetch_elos_of_players([])

        verify(self.plugin._loaded_plugins["balance"], times=0).add_request(any, any, any)

    def test_fetch_elos_of_player_with_no_balance_plugin(self):
        mocked_logger = mock(spec=logging.Logger)
        spy2(minqlx.get_logger)
        when(minqlx).get_logger(self.plugin).thenReturn(mocked_logger)
        self.setup_no_balance_plugin()

        self.plugin.fetch_elos_of_players([])

        verify(mocked_logger).warning(matches("Balance plugin not found.*"))

    def test_handle_round_countdown_with_no_game(self):
        setup_no_game()
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.handle_round_countdown(1)

        verify(self.plugin._loaded_plugins["balance"], times=0).add_request(any, any, any)

    def test_handle_round_countdown_fetches_elos_of_players_in_teams(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 1200), (player3, 1600)})

        self.plugin.handle_round_countdown(4)

        verify(self.plugin._loaded_plugins["balance"]).add_request(
            {player1.steam_id: 'ca', player2.steam_id: 'ca'},
            self.plugin.callback_ratings, minqlx.CHAT_CHANNEL
        )

    def test_callback_ratings_with_no_game_running(self):
        setup_no_game()
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.callback_ratings([], minqlx.CHAT_CHANNEL)

        verify(self.db, times=0).get(any)

    def test_callback_ratings_with_unsupported_game_type(self):
        setup_game_in_progress("unsupported")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Speccing Player", team="spectator")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({})

        self.plugin.callback_ratings([], minqlx.CHAT_CHANNEL)

        verify(self.db, times=0).get(any)

    def test_callback_ratings_warns_low_elo_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.thread, lambda func: func)
        patch(time.sleep, lambda int: None)
        when(self.db).get(any).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*8.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"))

    def test_callback_ratings_announces_information_to_other_players(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.thread, lambda func: func)
        patch(time.sleep, lambda int: None)
        when(self.db).get(any).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(matches("Fake Player2.*is below.*, but has.*8.*application matches left.*"))

    def test_callback_ratings_announces_information_to_other_players_just_once_per_connect(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})
        self.plugin.announced_player_elos = [456]

        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.thread, lambda func: func)
        patch(time.sleep, lambda int: None)
        when(self.db).get(any).thenReturn("2")

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(matches("Player.*is below.*, but has 8 application matches left.*"), times=0)

    def test_callback_ratings_makes_exception_for_player_in_exception_list(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list([player3])

        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.thread, lambda func: func)
        patch(time.sleep, lambda int: None)
        when(self.db).get(any).thenReturn("2")

        self.plugin.callback_ratings([player1, player2, player3], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*8.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*8.*of 10 application matches.*"))
        verify(player3, times=0).center_print(any)
        verify(player3, times=0).tell(any)

    def test_callback_ratings_warns_low_elo_player_when_application_games_not_set(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.thread, lambda func: func)
        patch(time.sleep, lambda int: None)
        when(self.db).get(any).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(player2, times=12).center_print(matches(".*Skill warning.*10.*matches left.*"))
        verify(player2).tell(matches(".*Skill Warning.*qlstats.*below.*800.*10.*of 10 application matches.*"))

    def test_callback_ratings_bans_low_elo_players_that_used_up_their_application_games(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(self.db).get(any).thenReturn("11")
        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))
        patch(minqlx.next_frame, lambda func: func)

        when(self.db).delete(any).thenReturn(None)

        self.plugin.callback_ratings([player1, player2], minqlx.CHAT_CHANNEL)

        verify(minqlx.COMMANDS).handle_input(any, any, any)
        verify(self.db).delete("minqlx:players:{}:minelo:abovegames".format(player2.steam_id))
        verify(self.db).delete("minqlx:players:{}:minelo:freegames".format(player2.steam_id))

    def test_handle_round_start_increases_application_games_for_untracked_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(False)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).incr("minqlx:players:{}:minelo:freegames".format(player2.steam_id))

    def test_handle_round_start_makes_exception_for_player_in_exception_list(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="red")
        connected_players(player1, player2, player3)
        self.setup_balance_ratings({(player1, 900), (player2, 799), (player3, 600)})
        self.setup_exception_list([player3])

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(False)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).incr("minqlx:players:{}:minelo:freegames".format(player2.steam_id))
        verify(self.db, times=0).incr("minqlx:players:{}:minelo:freegames".format(player3.steam_id))

    def test_handle_round_start_starts_tracking_for_low_elo_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(False)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        assert_that(self.plugin.tracked_player_sids, has_item(player2.steam_id))

    def test_handle_round_start_resets_above_games_for_low_elo_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(True)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).delete("minqlx:players:{}:minelo:abovegames".format(player2.steam_id))

    def test_handle_round_start_increases_above_games_for_application_games_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(True)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).incr("minqlx:players:{}:minelo:abovegames".format(player2.steam_id))

    def test_handle_round_start_increases_above_games_for_application_games_player_with_no_aobve_games_set(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(self.db).get(any).thenReturn("1")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(True)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).incr("minqlx:players:{}:minelo:abovegames".format(player2.steam_id))

    def test_handle_round_start_starts_tracking_of_above_elo_players_for_application_games_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(self.db).get(any).thenReturn("3")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(True)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        assert_that(self.plugin.tracked_player_sids, has_item(player2.steam_id))

    def test_handle_round_start_removes_minelo_db_entries_for_above_elo_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({(player1, 900), (player2, 801)})

        when(self.db).get(any).thenReturn("11")
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(True)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db).delete("minqlx:players:{}:minelo:freegames".format(player2.steam_id))
        verify(self.db).delete("minqlx:players:{}:minelo:abovegames".format(player2.steam_id))

    def test_handle_round_start_skips_already_tracked_player(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.plugin.tracked_player_sids.append(player2.steam_id)
        self.setup_balance_ratings({(player1, 900), (player2, 799)})

        when(self.db).get(any).thenReturn(3)
        when(self.db).delete(any).thenReturn(None)
        when(self.db).exists(any).thenReturn(False)
        when(self.db).incr(any).thenReturn(None)

        self.plugin.handle_round_start(1)

        verify(self.db, times=0).delete(any)
        verify(self.db, times=0).delete(any)

    def test_handle_round_start_with_unsupported_gametype(self):
        setup_game_in_progress("unsupported")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        self.setup_balance_ratings({})

        self.plugin.handle_round_start(2)

        verify(self.plugin._loaded_plugins["balance"], times=0).add_request(any, any, any)

    def test_handle_round_start_with_no_balance_plugin(self):
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        connected_players(player1, player2)
        mocked_logger = mock(spec=logging.Logger)
        spy2(minqlx.get_logger)
        when(minqlx).get_logger(self.plugin).thenReturn(mocked_logger)
        self.setup_no_balance_plugin()

        self.plugin.handle_round_start(5)

        verify(mocked_logger, atleast=1).warning(matches("Balance plugin not found.*"))

    def test_cmd_mercis_shows_currently_connected_merciful_players(self):
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings({(player, 1400), (player1, 801), (player2, 799), (player3, 900)})

        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player1.steam_id)).thenReturn("2")
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player2.steam_id)).thenReturn("3")
        when(self.db).get("minqlx:players:{}:minelo:abovegames".format(player1.steam_id)).thenReturn("6")
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player.steam_id)).thenReturn(None)
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player3.steam_id)).thenReturn(None)

        self.plugin.cmd_mercis(player, ["!mercis"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Fake Player1 \(elo: 801\):.*8.*application matches "
                                                               "left,.*6.*matches above.*"))
        assert_channel_was_replied(self.reply_channel, matches("Fake Player2 \(elo: 799\):.*7.*application matches "
                                                               "left"))

    def test_cmd_mercis_replies_to_main_cbannel_instead_of_team_chat(self):
        self.addCleanup(self.reset_chat_channel, minqlx.CHAT_CHANNEL)
        minqlx.CHAT_CHANNEL = mocked_channel()
        player = fake_player(666, "Cmd using Player")
        player1 = fake_player(123, "Fake Player1", team="red")
        player2 = fake_player(456, "Fake Player2", team="blue")
        player3 = fake_player(789, "Fake Player3", team="blue")
        connected_players(player, player1, player2, player3)
        self.setup_balance_ratings({(player, 1400), (player1, 801), (player2, 799), (player3, 900)})

        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player1.steam_id)).thenReturn("2")
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player2.steam_id)).thenReturn("3")
        when(self.db).get("minqlx:players:{}:minelo:abovegames".format(player1.steam_id)).thenReturn("6")
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player.steam_id)).thenReturn(None)
        when(self.db).get("minqlx:players:{}:minelo:freegames".format(player3.steam_id)).thenReturn(None)

        self.plugin.cmd_mercis(player, ["!mercis"], minqlx.BLUE_TEAM_CHAT_CHANNEL)

        assert_channel_was_replied(minqlx.CHAT_CHANNEL, matches("Fake Player1 \(elo: 801\):.*8.*application matches "
                                                                "left,.*6.*matches above.*"))
        assert_channel_was_replied(minqlx.CHAT_CHANNEL, matches("Fake Player2 \(elo: 799\):.*7.*application matches "
                                                                "left"))

    def reset_chat_channel(self, original_chat_channel):
        minqlx.CHAT_CHANNEL = original_chat_channel

    def test_cmd_mercis_shows_no_mercis_if_no_player_using_their_application_matches(self):
        player = fake_player(666, "Cmd using Player")
        connected_players(player)
        self.setup_balance_ratings({(player, 1400)})

        when(self.db).get(any).thenReturn(None)

        self.plugin.cmd_mercis(player, ["!mercis"], minqlx.CHAT_CHANNEL)

        assert_plugin_sent_to_console(any, times=0)
