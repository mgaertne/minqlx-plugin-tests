from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from mydiscordbot import *


class MyDiscordBotTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_game_in_warmup("ca")
        connected_players()
        self.discord = mock(spec=Bot, strict=False)
        setup_cvar("qlx_discordQuakeRelayMessageFilters", {"^\!s$", "^\!p$"}, set)
        self.plugin = mydiscordbot(discord_client=self.discord)

    def tearDown(self):
        unstub()

    def test_constructor(self):
        verify(self.discord).run()
        assert_plugin_sent_to_console(matches("mydiscordbot Version: "), atleast=1)

    def test_handle_unload_for_plugin(self):
        self.plugin.handle_plugin_unload("mydiscordbot")

        verify(self.discord).stop()

    def test_handle_unload_of_other_plugin(self):
        self.plugin.handle_plugin_unload("otherplugin")

        verify(self.discord, times=0).stop()

    def test_update_topics(self):
        self.plugin.update_topics()

        verify(self.discord).update_topics()

    def test_handle_ql_chat_message_relayed(self):
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "relayed message", minqlx.ChatChannel())

        verify(self.discord).relay_chat_message("Chatter", "", "relayed message")

    def test_handle_ql_chat_message_on_filtered_out_channel(self):
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "relayed message", minqlx.ConsoleChannel())

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_ql_chat_message_on_filtered_out_messagel(self):
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "!s", minqlx.RedTeamChatChannel())

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_player_connects(self):
        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(1, "Connecting Player"))

        verify(self.discord).relay_message("*Connecting Player connected.*")
        verify(self.discord).update_topics()

    def test_handle_player_with_asterisk_connects(self):
        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(1, "Connecting*Player"))

        verify(self.discord).relay_message("*Connecting*\**Player connected.*")

    def test_handle_player_disconnects(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "disconnected")

        verify(self.discord).relay_message("*Disconnecting Player disconnected.*")
        verify(self.discord).update_topics()

    def test_handle_player_times_out(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "timed out")

        verify(self.discord).relay_message("*Disconnecting Player timed out.*")
        verify(self.discord).update_topics()

    def test_handle_player_is_kicked(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "was kicked")

        verify(self.discord).relay_message("*Disconnecting Player was kicked.*")
        verify(self.discord).update_topics()

    def test_handle_player_is_kicked_with_reason(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "llamah")

        verify(self.discord).relay_message("*Disconnecting Player was kicked (llamah).*")
        verify(self.discord).update_topics()

    def test_handle_map(self):
        self.plugin.handle_map("Theatre of Pain", None)

        verify(self.discord).relay_message("*Changing map to Theatre of Pain...*")
        verify(self.discord).update_topics()

    def test_handle_vote_started_by_player(self):
        self.plugin.handle_vote_started(fake_player(1, "Votecaller"), "kick", "asdf")

        verify(self.discord).relay_message("*Votecaller called a vote: kick asdf*")

    def test_handle_vote_started_by_the_server(self):
        self.plugin.handle_vote_started(None, "map", "campgrounds")

        verify(self.discord).relay_message("*The server called a vote: map campgrounds*")

    def test_handle_vote_passed(self):
        votes = (4, 3)
        self.plugin.handle_vote_ended(votes, None, None, True)

        verify(self.discord).relay_message("*Vote passed (4 - 3).*")

    def test_handle_vote_failed(self):
        votes = (1, 8)
        self.plugin.handle_vote_ended(votes, None, None, False)

        verify(self.discord).relay_message("*Vote failed.*")

    def test_game_countdown(self):
        setup_game_in_warmup(game_type="ca", mapname="campgrounds", map_title="Campgrounds")
        undecorated(self.plugin.handle_game_countdown_or_end)(self.plugin)

        verify(self.discord).relay_message("Warmup on **Campgrounds** (CA) with **0/16** players. ")
        verify(self.discord).update_topics_on_relay_and_triggered_channels(
            "Warmup on **Campgrounds** (CA) with **0/16** players. ")

    def test_game_countdown_with_no_game(self):
        setup_no_game()
        undecorated(self.plugin.handle_game_countdown_or_end)(self.plugin)

        verify(self.discord, times=0).relay_message(any)
        verify(self.discord, times=0).update_topics_on_relay_and_triggered_channels(any)

    def test_cmd_discord_message_too_short(self):
        response = self.plugin.cmd_discord(fake_player(1, "Triggering Player"), ["!discord"], None)

        assert_that(response, is_(minqlx.RET_USAGE))

    def test_cmd_discord_message_triggered(self):
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discord(triggering_player, ["!discord", "asdf"], None)

        verify(self.discord).triggered_message(triggering_player, "asdf")
        assert_plugin_sent_to_console("Message to Discord chat cast!")

    def test_get_game_info_in_warmup(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "warmup"

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Warmup"))

    def test_get_game_info_in_countdown(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "countdown"

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match starting"))

    def test_get_game_info_in_progress(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "in_progress"
        mock_game.roundlimit = 8
        mock_game.red_score = 1
        mock_game.blue_score = 2

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match in progress: **1** - **2**"))

    def test_get_game_info_red_hit_roundlimit(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "in_progress"
        mock_game.roundlimit = 8
        mock_game.red_score = 8
        mock_game.blue_score = 2

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match ended: **8** - **2**"))

    def test_get_game_info_blue_hit_roundlimit(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "in_progress"
        mock_game.roundlimit = 8
        mock_game.red_score = 5
        mock_game.blue_score = 8

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match ended: **5** - **8**"))

    def test_get_game_info_unknown_game_state(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "asdf"
        mock_game.roundlimit = 8
        mock_game.red_score = 3
        mock_game.blue_score = 2

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Warmup"))

    def test_player_data_with_players_on_both_teams(self):
        connected_players(fake_player(1, "Player1", "red", score=1),
                          fake_player(2, "Player2", "blue", score=3),
                          fake_player(3, "Player3", "blue", score=2),
                          fake_player(4, "Player4", "red", score=5))

        player_data = mydiscordbot.player_data()

        assert_that(player_data, is_("\n**R:** **Player4**(5) **Player1**(1) \n**B:** **Player2**(3) **Player3**(2) "))

    def test_player_data_with_just_red_players(self):
        connected_players(fake_player(1, "Player1", "red"),
                          fake_player(4, "Player4", "red"))

        player_data = mydiscordbot.player_data()

        assert_that(player_data, is_("\n**R:** **Player1**(0) **Player4**(0) "))

    def test_player_data_with_just_blue_players(self):
        connected_players(fake_player(2, "Player2", "blue"),
                          fake_player(3, "Player3", "blue"))

        player_data = mydiscordbot.player_data()

        assert_that(player_data, is_("\n**B:** **Player2**(0) **Player3**(0) "))

    def test_team_data_with_empty_player_list(self):
        team_data = mydiscordbot.team_data(list())

        assert_that(team_data, is_(""))

    def test_team_data_with_limit(self):
        player_list = [fake_player(1, "Player1", "red", score=1),
                       fake_player(2, "Player2", "red", score=52),
                       fake_player(3, "Player3", "red", score=55),
                       fake_player(4, "Player4", "red", score=2),
                       fake_player(5, "Player5", "red", score=35),
                       fake_player(6, "Player6", "red", score=5),
                       fake_player(7, "Player7", "red", score=7),
                       ]
        team_data = mydiscordbot.team_data(player_list, limit=5)
        assert_that(team_data, is_("**Player3**(55) **Player2**(52) **Player5**(35) **Player7**(7) **Player6**(5) "))
