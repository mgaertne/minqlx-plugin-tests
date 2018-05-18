from minqlx_plugin_test import *

import logging
import time

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from mydiscordbot import *

from discord.ext.commands import Bot


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
        chatter = fake_player(1, "Chatter")
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "relayed message", minqlx.ChatChannel())

        verify(self.discord).relay_chat_message(player_that_matches(chatter), "", "relayed message")

    def test_handle_ql_chat_message_on_filtered_out_channel(self):
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "relayed message", minqlx.ConsoleChannel())

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_ql_chat_message_on_filtered_out_messagel(self):
        self.plugin.handle_ql_chat(fake_player(1, "Chatter"), "!s", minqlx.RedTeamChatChannel())

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_player_connects(self):
        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(1, "Connecting Player"))

        verify(self.discord).relay_message("_Connecting Player connected._")
        verify(self.discord).update_topics()

    def test_handle_player_with_asterisk_connects(self):
        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(1, "Connecting*Player"))

        verify(self.discord).relay_message("_Connecting\*Player connected._")

    def test_handle_player_with_underscore_connects(self):
        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(1, "Connecting_Player"))

        verify(self.discord).relay_message("_Connecting\_Player connected._")

    def test_handle_player_disconnects(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "disconnected")

        verify(self.discord).relay_message("_Disconnecting Player disconnected._")
        verify(self.discord).update_topics()

    def test_handle_player_times_out(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "timed out")

        verify(self.discord).relay_message("_Disconnecting Player timed out._")
        verify(self.discord).update_topics()

    def test_handle_player_is_kicked(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "was kicked")

        verify(self.discord).relay_message("_Disconnecting Player was kicked._")
        verify(self.discord).update_topics()

    def test_handle_player_is_kicked_with_reason(self):
        undecorated(self.plugin.handle_player_disconnect)(self.plugin,
                                                          fake_player(1, "Disconnecting Player"),
                                                          "llamah")

        verify(self.discord).relay_message("_Disconnecting Player was kicked (llamah)._")
        verify(self.discord).update_topics()

    def test_handle_map(self):
        self.plugin.handle_map("Theatre of Pain", None)

        verify(self.discord).relay_message("*Changing map to Theatre of Pain...*")
        verify(self.discord).update_topics()

    def test_handle_vote_started_by_player(self):
        self.plugin.handle_vote_started(fake_player(1, "Votecaller"), "kick", "asdf")

        verify(self.discord).relay_message("_Votecaller called a vote: kick asdf_")

    def test_handle_vote_started_by_the_server(self):
        self.plugin.handle_vote_started(None, "map", "campgrounds")

        verify(self.discord).relay_message("_The server called a vote: map campgrounds_")

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

    def test_get_game_info_red_player_dropped_out(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "in_progress"
        mock_game.roundlimit = 8
        mock_game.red_score = -999
        mock_game.blue_score = 3

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match ended: **-999** - **3**"))

    def test_get_game_info_blue_player_dropped_out(self):
        mock_game = mock(spec=minqlx.Game, strict=False)
        mock_game.state = "in_progress"
        mock_game.roundlimit = 8
        mock_game.red_score = 5
        mock_game.blue_score = -999

        game_info = mydiscordbot.get_game_info(mock_game)

        assert_that(game_info, is_("Match ended: **5** - **-999**"))

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

    def test_cmd_discordbot_invalid(self):
        triggering_player = fake_player(1, "Triggering Player")
        return_code = self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "asdf"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_discordbot_too_many_arguments(self):
        triggering_player = fake_player(1, "Triggering Player")
        return_code = self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "status", "asdf"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_discordbot_status(self):
        when(self.discord).status().thenReturn("Discord status message")
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "status"], chat_channel)

        verify(chat_channel).reply("Discord status message")

    def test_cmd_discordbot_status2(self):
        when(self.discord).status().thenReturn("Discord status message")
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot"], chat_channel)

        verify(chat_channel).reply("Discord status message")

    def test_cmd_discordbot_connect(self):
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "connect"], chat_channel)

        verify(chat_channel).reply("Connecting to Discord...")
        verify(self.discord).run()

    def test_cmd_discordbot_connect_when_already_connected(self):
        when(self.discord).is_discord_logged_in().thenReturn(True)
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "connect"], chat_channel)

        verify(chat_channel).reply("Connecting to Discord...")
        verify(self.discord, times=0).run()

    def test_cmd_discordbot_disconnect(self):
        when(self.discord).is_discord_logged_in().thenReturn(True)
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "disconnect"], chat_channel)

        verify(chat_channel).reply("Disconnecting from Discord...")
        verify(self.discord).stop()

    def test_cmd_discordbot_disconnect_when_already_disconnected(self):
        when(self.discord).is_discord_logged_in().thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "disconnect"], chat_channel)

        verify(chat_channel).reply("Disconnecting from Discord...")
        verify(self.discord, times=0).stop()

    def test_cmd_discordbot_reconnect(self):
        when(self.discord).is_discord_logged_in().thenReturn(True).thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "reconnect"], chat_channel)

        verify(chat_channel).reply("Reconnecting to Discord...")
        verify(self.discord).stop()
        verify(self.discord).run()

    def test_cmd_discordbot_reconnect_when_disconnected(self):
        when(self.discord).is_discord_logged_in().thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        chat_channel = mock(spec=minqlx.AbstractChannel)
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot", "reconnect"], chat_channel)

        verify(chat_channel).reply("Reconnecting to Discord...")
        verify(self.discord, times=0).stop()
        verify(self.discord).run()


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


def mocked_coro(return_value=None):

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return return_value

    return mock_coro()


def mocked_user(id=777, name="Some-Discord-User", nick=None):
    user = mock(spec=discord.User)

    user.id = id
    user.name = name
    user.nick = nick
    user.mention = "<@%s>" % user.id

    return user


def mocked_channel(id=666, name="channel-name", channel_type=ChannelType.text, topic=None):
    channel = mock(spec=discord.TextChannel)

    channel.id = id
    channel.name = name
    channel.type = channel_type
    channel.topic = topic
    channel.mention = "<#%s>" % channel.id

    when(channel).send(any).thenReturn(mocked_coro())
    when(channel).edit(topic=any).thenReturn(mocked_coro())

    return channel


def mocked_message(content="message content", user=mocked_user(), channel=mocked_channel()):
    message = mock(spec=discord.Message)

    message.clean_content = content
    message.author = user
    message.channel = channel

    return message


class DiscordHelpFormatterTests(unittest.TestCase):

    def setUp(self):
        self.formatter = DiscordHelpFormatter()
        self.formatter.context = mock({'send': mocked_coro})
        self.formatter.context.prefix = "!"
        self.formatter.context.invoked_with = "help"
        self.formatter.context.bot = mock({'description': 'Mocked Bot'}, spec=Bot)
        self.formatter.context.bot.user = mocked_user()
        help_command = mock({'name': 'help', 'description': 'Fake Help', 'short_doc': 'Fake Help',
                             'hidden': False, 'cog_name': None, 'aliases': []})
        when(help_command).can_run(self.formatter.context).thenReturn(mocked_coro(True))
        fake_command = mock({'name': 'fake', 'description': 'Fake Command', 'short_doc': 'Fake Command',
                             'hidden': False, 'cog_name': None, 'aliases': []})
        when(fake_command).can_run(self.formatter.context).thenReturn(mocked_coro(True))
        self.formatter.context.bot.all_commands = {help_command.name: help_command, fake_command.name: fake_command}
        self.formatter.command = self.formatter.context.bot
        when(self.formatter.context.bot).can_run(any).thenReturn(mocked_coro(True))

    def tearDown(self):
        unstub()

    def setup_v0_16_discord_library(self):
        discord.version_info = discord.VersionInfo(major=0, minor=1, micro=16, releaselevel="", serial=0)

    def setup_v1_discord_library(self):
        discord.version_info = discord.VersionInfo(major=1, minor=0, micro=0, releaselevel="", serial=0)

    def test_get_ending_note(self):
        ending_note = self.formatter.get_ending_note()

        assert_that(ending_note, is_("Type !help command for more info on a command."))

    def test_format_v0_16(self):
        self.setup_v0_16_discord_library()

        patch(HelpFormatter.format, lambda: ["```\nMocked Bot\n\n"
                                             "\u200bNo Category:\n"
                                             "  fake Fake Command\n"
                                             "  help Fake Help\n\n"
                                             "Type !help command for more info on a command.\n```"])

        when(self.formatter.context.bot).can_run(self.formatter.context).thenReturn(True)

        pages = self.formatter.format()

        assert_that(pages, is_(["```\nMocked Bot\n\n"
                                "\u200bminqlx Commands:\n"
                                "  fake Fake Command\n"
                                "  help Fake Help\n\n"
                                "Type !help command for more info on a command.\n```"]))

    def test_format_v0_16_help_not_applicable(self):
        self.setup_v0_16_discord_library()

        when(self.formatter.context.bot).can_run(self.formatter.context).thenReturn(False)

        pages = self.formatter.format()

        assert_that(pages, is_([]))

    @async_test
    async def test_format_v1(self):
        self.setup_v1_discord_library()

        when(self.formatter.context.bot).can_run(self.formatter.context)\
            .thenReturn(mocked_coro(True))\
            .thenReturn(mocked_coro(True))

        pages = (await self.formatter.format())

        assert_that(pages, is_(["```\nMocked Bot\n\n"
                                "\u200bminqlx Commands:\n"
                                "  fake Fake Command\n"
                                "  help Fake Help\n\n"
                                "Type !help command for more info on a command.\n```"]))

    @async_test
    async def test_format_v1_help_not_applicable(self):
        self.setup_v1_discord_library()

        when(self.formatter.context.bot).can_run(self.formatter.context)\
            .thenReturn(mocked_coro(False))

        pages = (await self.formatter.format())

        assert_that(pages, is_([]))


class DiscordChannelTests(unittest.TestCase):

    def setUp(self):
        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))

        self.client = mock(spec=SimpleAsyncDiscord)
        when(self.client).send_to_discord_channels(any, any).thenReturn(None)

        self.author = mocked_user()
        self.author.display_name = "Discord-User"

        self.discord_channel = mocked_channel()

        self.minqlx_discord_channel = DiscordChannel(self.client, self.author, self.discord_channel)

    def teardown(self):
        unstub()

    def test_reply(self):
        self.minqlx_discord_channel.reply("asdf")

        verify(self.client).send_to_discord_channels({self.discord_channel.id}, "asdf")


class DiscordDummyPlayerTests(unittest.TestCase):

    def setUp(self):
        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))

        self.client = mock(spec=SimpleAsyncDiscord)
        when(self.client).send_to_discord_channels(any, any).thenReturn(None)

        self.author = mocked_user()
        self.author.display_name = "Discord-User"

        self.discord_channel = mocked_channel()

        self.dummy_player = DiscordDummyPlayer(self.client, self.author, self.discord_channel)

    def teardown(self):
        unstub()

    def test_channel(self):
        channel = self.dummy_player.channel

        assert_that(channel, is_(DiscordChannel(self.client, self.author, self.discord_channel)))

    def test_tell(self):
        self.dummy_player.tell("asdf")

        verify(self.client).send_to_discord_channels({self.discord_channel.id}, "asdf")


class SimpleAsyncDiscordTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()

        spy2(minqlx.get_cvar)
        when2(minqlx.get_cvar, "qlx_owner").thenReturn("1234567890")

        setup_cvars({
            "qlx_discordBotToken": ("bottoken", None),
            "qlx_discordRelayChannelIds": ({"1234"}, set),
            "qlx_discordTriggeredChannelIds": ({"456", "789"}, set),
            "qlx_discordUpdateTopicOnTriggeredChannels": (True, bool),
            "qlx_discordKeepTopicSuffixChannelIds": ({"1234", "456"}, set),
            "qlx_discordTriggerTriggeredChannelChat": ("trigger", None),
            "qlx_discordCommandPrefix": ("%", None),
            "qlx_discordTriggerStatus": ("minqlx", None),
            "qlx_discordMessagePrefix": ("[DISCORD]", None),
            "qlx_displayChannelForDiscordRelayChannels": (False, bool),
            "qlx_discordReplaceMentionsForRelayedMessages": (False, bool),
            "qlx_discordReplaceMentionsForTriggeredMessages": (True, bool),
            "qlx_discordAdminPassword": ("adminpassword", None),
            "qlx_discordAuthCommand": ("auth", None),
            "qlx_discordExecPrefix": ("exec", None)
        })

        self.logger = mock(spec=logging.Logger)
        self.discord = SimpleAsyncDiscord("version information", self.logger)

        self.setup_v1_discord_library()

    def tearDown(self):
        unstub()

    def setup_v0_16_discord_library(self):
        discord.version_info = discord.VersionInfo(major=0, minor=1, micro=16, releaselevel="", serial=0)
        self.setup_discord_client_mock_common()

        when(self.discord_client).send_message(any, any).thenReturn(mocked_coro())
        when(self.discord_client).say(any).thenReturn(mocked_coro())
        self.discord_client.is_logged_in = True

        self.discord.discord = self.discord_client

    def setup_discord_client_mock_common(self):
        self.discord_client = mock(spec=Bot)

        when(self.discord_client).change_presence(game=any).thenReturn(mocked_coro())

        self.discord_client.user = mock(discord.User)
        self.discord_client.user.name = "Bot Name"
        self.discord_client.user.id = 24680

        self.discord_client.loop = asyncio.get_event_loop()

    def setup_v1_discord_library(self):
        discord.version_info = discord.VersionInfo(major=1, minor=0, micro=0, releaselevel="", serial=0)
        self.setup_discord_client_mock_common()

        when(self.discord_client).is_ready().thenReturn(True)

        self.discord.discord = self.discord_client

    def mocked_context(self, prefix="%", bot=None, message=mocked_message(), invoked_with="asdf"):
        context = mock({'send': mocked_coro})
        context.prefix = prefix
        context.bot = self.discord_client
        if bot is not None:
            context.bot = bot
        context.message = message
        context.invoked_with = invoked_with

        return context

    def relay_channel(self):
        channel = mocked_channel(id=1234, name="relay-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def triggered_channel(self):
        channel = mocked_channel(id=456, name="triggered-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def uninteresting_channel(self):
        channel = mocked_channel(id=987, name="uninteresting-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def setup_discord_members(self, *users):
        when(self.discord_client).get_all_members().thenReturn([user for user in users])

    def setup_discord_channels(self, *channels):
        when(self.discord_client).get_all_channels().thenReturn([channel for channel in channels])

    def verify_added_command(self, name, callback, checks=None):
        if checks is None:
            verify(self.discord_client).add_command(arg_that(lambda command: command.name == name and
                                                             command.callback == callback))
        else:
            verify(self.discord_client).add_command(arg_that(lambda command: command.name == name and
                                                             command.callback == callback and
                                                             command.checks == checks))

    def test_status_connected(self):
        status = self.discord.status()

        assert_that(status, is_("Discord connection up and running."))

    def test_status_no_client(self):
        self.discord.discord = None

        status = self.discord.status()

        assert_that(status, is_("No discord connection set up."))

    def test_status_client_not_connected(self):
        when(self.discord_client).is_ready().thenReturn(False)

        status = self.discord.status()

        assert_that(status, is_("Discord client not connected."))

    @async_test
    async def test_initialize_bot(self):
        self.discord.initialize_bot(self.discord_client)

        self.verify_added_command(name="version", callback=self.discord.version)
        self.verify_added_command(name="minqlx", callback=self.discord.trigger_status,
                                  checks=[self.discord.is_message_in_relay_or_triggered_channel])
        self.verify_added_command(name="trigger", callback=self.discord.triggered_chat,
                                  checks=[self.discord.is_message_in_triggered_channel])
        self.verify_added_command(name="auth", callback=self.discord.auth)
        self.verify_added_command(name="exec", callback=self.discord.qlx,
                                  checks=[self.discord.is_private_message, self.discord.is_authed])
        verify(self.discord_client).add_listener(self.discord.on_ready)
        verify(self.discord_client).add_listener(self.discord.on_message)

    @async_test
    async def test_version_v0_16(self):
        self.setup_v0_16_discord_library()

        context = self.mocked_context()

        await self.discord.version(context)

        verify(self.discord_client).say("```version information```")

    @async_test
    async def test_version_v1(self):
        context = self.mocked_context()

        await self.discord.version(context)

        verify(context).send("```version information```")

    def test_is_private_message_v0_16(self):
        self.setup_v0_16_discord_library()

        context = self.mocked_context()
        context.message.channel.is_private = True

        is_private = self.discord.is_private_message(context)

        assert_that(is_private, is_(True))

    def test_is_private_message_v1(self):
        context = self.mocked_context()

        is_private = self.discord.is_private_message(context)

        assert_that(is_private, is_(False))

    def test_user_not_authed(self):
        context = self.mocked_context()

        is_authed = self.discord.is_authed(context)

        assert_that(is_authed, is_(False))

    def test_user_has_authed(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        self.discord.authed_discord_ids.add(user.id)

        is_authed = self.discord.is_authed(context)

        assert_that(is_authed, is_(True))

    def test_user_with_no_auth_attempts_is_not_barred(self):
        context = self.mocked_context()

        is_barred = self.discord.is_barred_from_auth(context)

        assert_that(is_barred, is_(False))

    def test_user_with_two_auth_attempts_is_not_barred(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        self.discord.auth_attempts[user.id] = 1

        is_barred = self.discord.is_barred_from_auth(context)

        assert_that(is_barred, is_(False))

    def test_user_has_no_auth_attempts_left(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        self.discord.auth_attempts[user.id] = 0

        is_barred = self.discord.is_barred_from_auth(context)

        assert_that(is_barred, is_(True))

    @async_test
    async def test_successful_auth(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        await self.discord.auth(context, "adminpassword")

        assert_that(self.discord.authed_discord_ids, is_({user.id}))
        verify(context).send(matches(".*successfully authenticated.*"))

    @async_test
    async def test_first_failed_auth_attempt(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        await self.discord.auth(context, "wrong password")

        assert_that(self.discord.auth_attempts, contains(user.id))
        verify(context).send(matches(".*Wrong password.*"))

    @async_test
    async def test_third_failed_auth_attempt_bars_user_from_auth(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        self.discord.auth_attempts[user.id] = 1

        patch(threading.Timer, "start", lambda: None)

        await self.discord.auth(context, "wrong password")

        assert_that(self.discord.auth_attempts[user.id], is_(0))
        verify(context).send(matches(".*Maximum authentication attempts reached.*"))

    @async_test
    async def test_third_failed_auth_attempt_bars_user_from_auth_and_resets_attempts(self):
        user = mocked_user()
        context = self.mocked_context(message=mocked_message(user=user))

        self.discord.auth_attempts[user.id] = 1

        patch(threading.Event, "wait", lambda *args: None)

        await self.discord.auth(context, "wrong password")

        time.sleep(0.00001)

        assert_that(self.discord.auth_attempts, not_(contains(user.id)))

    @async_test
    async def test_qlx_executes_command(self):
        context = self.mocked_context()

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))
        patch(minqlx.next_frame, lambda func: func)

        await self.discord.qlx(context, "exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)

    @async_test
    async def test_qlx_fails_to_execute_command_v0_16(self):
        self.setup_v0_16_discord_library()

        context = self.mocked_context()

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenRaise(Exception())

        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))
        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.log_exception, lambda: None)

        await self.discord.qlx(context, "exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)
        verify(self.discord_client).send_message(any, matches(".*Exception.*"))

    @async_test
    async def test_qlx_fails_to_execute_command_v1(self):
        context = self.mocked_context()

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenRaise(Exception())

        patch(minqlx.PlayerInfo, lambda *args: mock(spec=minqlx.PlayerInfo))
        patch(minqlx.next_frame, lambda func: func)
        patch(minqlx.log_exception, lambda: None)

        await self.discord.qlx(context, "exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)
        verify(context).send(matches(".*Exception.*"))

    def test_is_message_in_relay_or_triggered_channel_in_relay_channel_v0_16(self):
        context = self.mocked_context(message=mocked_message(channel=mocked_channel(id="1234")))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_relay_or_triggered_channel_in_triggered_channels_v0_16(self):
        context = self.mocked_context(message=mocked_message(channel=mocked_channel(id="456")))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_relay_or_triggered_channel_not_in_any_channels_v0_16(self):
        context = self.mocked_context(message=mocked_message(channel=mocked_channel(id="987")))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(False))

    def test_is_message_in_relay_or_triggered_channel_in_relay_channel_v1(self):
        context = self.mocked_context(message=mocked_message(channel=self.relay_channel()))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_relay_or_triggered_channel_in_triggered_channels_v1(self):
        context = self.mocked_context(message=mocked_message(channel=self.triggered_channel()))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_relay_or_triggered_channel_not_in_any_channels_v1(self):
        context = self.mocked_context(message=mocked_message(channel=self.uninteresting_channel()))

        is_message_in_interesting_channel = self.discord.is_message_in_relay_or_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(False))

    @async_test
    async def test_status_during_game(self):
        setup_game_in_progress()
        connected_players()

        context = self.mocked_context()

        await self.discord.trigger_status(context)

        verify(context).send(matches("Match in progress.*"))

    @async_test
    async def test_status_no_game(self):
        setup_no_game()
        connected_players()

        context = self.mocked_context()

        await self.discord.trigger_status(context)

        verify(context).send("Currently no game running.")

    def test_is_message_in_triggered_channel_in_triggered_channels_v0_16(self):
        context = self.mocked_context(message=mocked_message(channel=mocked_channel(id="456")))

        is_message_in_interesting_channel = self.discord.is_message_in_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_triggered_channel_not_in_any_channels_v0_16(self):
        context = self.mocked_context(message=mocked_message(channel=mocked_channel(id="987")))

        is_message_in_interesting_channel = self.discord.is_message_in_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(False))

    def test_is_message_in_triggered_channel_in_triggered_channels_v1(self):
        context = self.mocked_context(message=mocked_message(channel=self.triggered_channel()))

        is_message_in_interesting_channel = self.discord.is_message_in_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(True))

    def test_is_message_in_triggered_channel_not_in_any_interesting_channels_v1(self):
        context = self.mocked_context(message=mocked_message(channel=self.relay_channel()))

        is_message_in_interesting_channel = self.discord.is_message_in_triggered_channel(context)

        assert_that(is_message_in_interesting_channel, is_(False))

    @async_test
    async def test_triggered_chat(self):
        message = mocked_message(content="%trigger message from discord to minqlx",
                                 user=mocked_user(id=456, name="Sender"),
                                 channel=self.triggered_channel())
        context = self.mocked_context(message=message, invoked_with="trigger")

        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.triggered_chat(context, "message from discord to minqlx")

        verify(minqlx.CHAT_CHANNEL).reply("[DISCORD] ^5#triggered-channel ^6Sender^7:^2 message from discord to minqlx")

    @async_test
    async def test_on_ready(self):
        self.setup_v1_discord_library()

        await self.discord.on_ready()

        verify(self.discord_client).change_presence(game=discord.Game(name="Quake Live"))

    @async_test
    async def test_on_message_is_relayed(self):
        message = mocked_message(content="some chat message",
                                 user=mocked_user(name="Sender"),
                                 channel=self.relay_channel())

        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL).reply("[DISCORD] ^6Sender^7:^2 some chat message")

    @async_test
    async def test_on_message_in_wrong_channel(self):
        message = mocked_message(content="some chat message",
                                 channel=self.triggered_channel())

        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @async_test
    async def test_on_message_too_short_message(self):
        message = mocked_message(content="",
                                 channel=self.relay_channel())

        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @async_test
    async def test_on_message_from_bot(self):
        message = mocked_message(content="",
                                 user=self.discord_client.user,
                                 channel=self.relay_channel())

        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @async_test
    async def test_on_message_without_message(self):
        patch(minqlx.CHAT_CHANNEL, "reply", lambda msg: None)
        when2(minqlx.CHAT_CHANNEL.reply, any).thenReturn(None)

        await self.discord.on_message(None)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    def test_update_topics_v0_16(self):
        self.setup_v0_16_discord_library()
        setup_game_in_progress()
        connected_players()

        relay_channel = mocked_channel(id="1234", topic=" players. kept suffix")
        when(self.discord_client).get_channel(relay_channel.id).thenReturn(relay_channel)

        trigger_channel1 = mocked_channel(id="456", topic=None)
        when(self.discord_client).get_channel(trigger_channel1.id).thenReturn(trigger_channel1)

        trigger_channel2 = mocked_channel(id="789", topic="overwritten suffix")
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        when(self.discord_client).edit_channel(any, topic=any).thenReturn(mocked_coro())

        self.discord.update_topics()

        verify(self.discord_client).edit_channel(relay_channel,
                                                 topic=matches("Match in progress.*? players. kept suffix"))
        verify(self.discord_client).edit_channel(trigger_channel1, topic=matches("Match in progress.*? players."))
        verify(self.discord_client).edit_channel(trigger_channel2, topic=matches("Match in progress.*? players."))

    def test_update_topics_v1(self):
        setup_game_in_progress()
        connected_players()

        when(self.discord_client).is_ready().thenReturn(True)

        relay_channel = self.relay_channel()
        relay_channel.topic = " players. kept suffix"

        trigger_channel1 = self.triggered_channel()

        trigger_channel2 = mocked_channel(id=789, topic="overwritten suffix")
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        self.discord.update_topics()

        verify(relay_channel).edit(topic=matches("Match in progress.*? players. kept suffix"))
        verify(trigger_channel1).edit(topic=matches("Match in progress.*? players."))
        verify(trigger_channel2).edit(topic=matches("Match in progress.*? players."))

    def test_update_topics_discord_client_not_ready(self):
        setup_game_in_progress()
        connected_players()

        when(self.discord_client).is_ready().thenReturn(False)

        relay_channel = self.relay_channel()
        relay_channel.topic = " players. kept suffix"

        trigger_channel1 = self.triggered_channel()

        trigger_channel2 = mocked_channel(id=789, topic="some topic")
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        self.discord.update_topics()

        verify(relay_channel, times=0).edit(topic=any)
        verify(trigger_channel1, times=0).edit(topic=any)
        verify(trigger_channel2, times=0).edit(topic=any)

    def test_update_topics_not_initialized_discord_client(self):
        setup_game_in_progress()
        connected_players()

        self.discord.discord = None

        self.discord.update_topics()

        verifyZeroInteractions(self.discord_client)

    def test_update_topics_no_update_on_triggered_channels_configured(self):
        setup_game_in_progress()
        connected_players()

        when2(Plugin.get_cvar, "qlx_discordUpdateTopicOnTriggeredChannels", bool).thenReturn(False)
        when2(Plugin.get_cvar, "qlx_discordKeepTopicSuffixChannelIds", set).thenReturn(set())
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        when(self.discord_client).is_ready().thenReturn(True)

        relay_channel = self.relay_channel()
        relay_channel.topic = " players. not kept suffix"

        trigger_channel1 = self.triggered_channel()

        trigger_channel2 = mocked_channel(id=789, topic="some topic")
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        self.discord.update_topics()

        verify(relay_channel).edit(topic=matches("Match in progress.*? players. "))
        verify(trigger_channel1, times=0).edit(topic=any)
        verify(trigger_channel2, times=0).edit(topic=any)

    def test_update_topics_non_existing_channel(self):
        setup_game_in_progress()
        connected_players()

        when(self.discord_client).is_ready().thenReturn(True)

        trigger_channel2 = mocked_channel(id=789, topic="overwritten suffix")
        when(trigger_channel2).edit(topic=any).thenReturn(mocked_coro())

        when(self.discord_client).edit_channel(any, topic=any).thenReturn(mocked_coro())

        self.discord.update_topics()

        verify(trigger_channel2, times=0).edit(topic=matches("Match in progress.*? players."))

    def test_update_topics_all_channel_keep_suffix(self):
        setup_game_in_progress()
        connected_players()

        when2(Plugin.get_cvar, "qlx_discordKeepTopicSuffixChannelIds", set).thenReturn({"1234", "456", "789"})
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        when(self.discord_client).is_ready().thenReturn(True)

        relay_channel = self.relay_channel()
        relay_channel.topic = " players. kept suffix"

        trigger_channel1 = self.triggered_channel()

        trigger_channel2 = mocked_channel(id=789, topic="some topic")
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        self.discord.update_topics()

        verify(relay_channel).edit(topic=matches("Match in progress.*? players. kept suffix"))
        verify(trigger_channel1).edit(topic=matches("Match in progress.*? players."))
        verify(trigger_channel2).edit(topic=matches("Match in progress.*? players. some topic"))

    def test_stop_discord_client(self):
        when(self.discord_client).change_presence(status="offline").thenReturn(mocked_coro())
        when(self.discord_client).logout().thenReturn(mocked_coro())

        self.discord.stop()

        verify(self.discord_client).change_presence(status="offline")
        verify(self.discord_client).logout()

    def test_stop_discord_client_discord_not_initialized(self):
        self.discord.discord = None

        self.discord.stop()

        verify(self.discord_client, times=0).change_presence(status="offline")
        verify(self.discord_client, times=0).logout()

    def test_relay_message_v0_16(self):
        self.setup_v0_16_discord_library()

        relay_channel = mocked_channel(id="1234")
        when(self.discord_client).get_channel(relay_channel.id).thenReturn(relay_channel)

        self.discord.relay_message("awesome relayed message")

        verify(self.discord_client).send_message(relay_channel, "awesome relayed message")

    def test_relay_message_v1(self):
        relay_channel = self.relay_channel()

        self.discord.relay_message("awesome relayed message")

        verify(relay_channel).send("awesome relayed message")

    def test_relay_message_with_not_connected_client(self):
        when(self.discord_client).is_ready().thenReturn(False)

        relay_channel = self.relay_channel()

        self.discord.relay_message("awesome relayed message")

        verify(relay_channel, times=0).send(any)

    def test_send_to_discord_channels_with_no_channel_ids(self):
        self.setup_v0_16_discord_library()

        self.discord.send_to_discord_channels(set(), "awesome relayed message")

        verifyZeroInteractions(self.discord_client)

    def test_send_to_discord_channels_for_non_existing_channel(self):
        self.setup_v0_16_discord_library()

        self.discord.send_to_discord_channels({"6789"}, "awesome relayed message")

        verify(self.discord_client, times=0).send_message(any, any)

    def test_relay_chat_message_simple_message(self):
        relay_channel = self.relay_channel()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great!")

        verify(relay_channel).send("**Chatting player**: QL is great!")

    def test_relay_chat_message_with_asterisks_in_playername(self):
        relay_channel = self.relay_channel()

        player = fake_player(steam_id=1, name="*Chatting* player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great!")

        verify(relay_channel).send("**\*Chatting\* player**: QL is great!")

    def test_relay_chat_message_replace_user_mention(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForRelayedMessages", bool).thenReturn(True)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        relay_channel = self.relay_channel()

        mentioned_user = mocked_user(id=123, name="chatter")
        self.setup_discord_members(mentioned_user)
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great, @chatter !")

        verify(relay_channel).send("**Chatting player**: QL is great, {} !".format(mentioned_user.mention))

    def test_relay_chat_message_mentioned_member_not_found(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForRelayedMessages", bool).thenReturn(True)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        relay_channel = self.relay_channel()

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great, @chatter !")

        verify(relay_channel).send("**Chatting player**: QL is great, @chatter !")

    def test_relay_chat_message_replace_channel_mention(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForRelayedMessages", bool).thenReturn(True)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v0_16_discord_library()

        relay_channel = self.relay_channel()

        mentioned_channel = mocked_channel(id=456, name="mentioned-channel")
        self.setup_discord_members()
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great, #mention !")

        verify(self.discord_client).send_message(relay_channel, "**Chatting player**: QL is great, {} !"
                                                 .format(mentioned_channel.mention))

    def test_relay_chat_message_mentioned_channel_not_found(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForRelayedMessages", bool).thenReturn(True)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        relay_channel = self.relay_channel()

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great, #mention !")

        verify(relay_channel).send("**Chatting player**: QL is great, #mention !")

    def test_relay_chat_message_discord_not_logged_in(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForRelayedMessages", bool).thenReturn(True)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v1_discord_library()

        when(self.discord_client).is_ready().thenReturn(False)

        relay_channel = self.relay_channel()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great, @member #mention !")

        verify(relay_channel, times=0).send(any)

    def test_find_user_match_exact_match(self):
        exact_matching_user = mocked_user(name="user")
        other_user = mocked_user(name="non-exact-match-User")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("user", [exact_matching_user, other_user])

        assert_that(matched_user, is_(exact_matching_user))

    def test_find_user_match_case_insensitive_match(self):
        case_insensitive_matching_user = mocked_user(name="uSeR")
        other_user = mocked_user(name="non-matched user")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("user", [case_insensitive_matching_user, other_user])

        assert_that(matched_user, is_(case_insensitive_matching_user))

    def test_find_user_match_exact_nick_match(self):
        exact_matching_user = mocked_user(name="non-matching name", nick="user")
        other_user = mocked_user(name="non-exact-match-User")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("user", [exact_matching_user, other_user])

        assert_that(matched_user, is_(exact_matching_user))

    def test_find_user_match_case_insensitive_nick_match(self):
        exact_matching_user = mocked_user(name="non-matching name", nick="UseR")
        other_user = mocked_user(name="non-matched user", nick="non-matched nick")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("user", [exact_matching_user, other_user])

        assert_that(matched_user, is_(exact_matching_user))

    def test_find_user_match_fuzzy_match_on_name(self):
        fuzzy_matching_user = mocked_user(name="matching-GeneRal-user")
        other_user = mocked_user(name="non-matched channel")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("UsEr", [fuzzy_matching_user, other_user])

        assert_that(matched_user, is_(fuzzy_matching_user))

    def test_find_user_match_fuzzy_match_on_nick(self):
        fuzzy_matching_user = mocked_user(name="non-matchin-usr", nick="matching-General-uSeR")
        other_user = mocked_user(name="non-matched channel")

        matched_user = SimpleAsyncDiscord.find_user_that_matches("UsEr", [fuzzy_matching_user, other_user])

        assert_that(matched_user, is_(fuzzy_matching_user))

    def test_find_user_match_no_match_found(self):
        matched_user = SimpleAsyncDiscord.find_user_that_matches("awesome",
                                                                 [mocked_user(name="no_match-user"),
                                                                  mocked_user(name="non-matched user")])

        assert_that(matched_user, is_(None))

    def test_find_user_match_more_than_one_user_found(self):
        matched_user = SimpleAsyncDiscord.find_user_that_matches("user",
                                                                 [mocked_user(name="matched_user"),
                                                                  mocked_user(name="another-matched-uSEr")])

        assert_that(matched_user, is_(None))

    def test_find_user_match_more_than_one_user_found_and_player_informed(self):
        sending_player = fake_player(steam_id=1, name="Player")
        matched_user = SimpleAsyncDiscord.find_user_that_matches("user",
                                                                 [mocked_user(name="matched_user"),
                                                                  mocked_user(name="another-matched-uSEr")],
                                                                 sending_player)

        verify(sending_player).tell("Found ^62^7 matching discord users for @user:")
        verify(sending_player).tell("@matched_user @another-matched-uSEr ")
        assert_that(matched_user, is_(None))

    def test_find_channel_match_exact_match(self):
        exact_matching_channel = mocked_channel(name="general")
        other_channel = mocked_channel(name="General")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [exact_matching_channel, other_channel])

        assert_that(matched_channel, is_(exact_matching_channel))

    def test_find_channel_match_case_insensitive_match(self):
        case_insensitive_matching_channel = mocked_channel(name="GeNeRaL")
        other_channel = mocked_channel(name="non-matched General")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [case_insensitive_matching_channel,
                                                                        other_channel])

        assert_that(matched_channel, is_(case_insensitive_matching_channel))

    def test_find_channel_match_fuzzy_match(self):
        fuzzy_matching_channel = mocked_channel(name="matching-GeneRal-channel")
        other_channel = mocked_channel(name="non-matched channel")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [fuzzy_matching_channel, other_channel])

        assert_that(matched_channel, is_(fuzzy_matching_channel))

    def test_find_channel_match_no_match_found(self):
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [mocked_channel(name="no_match-channel"),
                                                                        mocked_channel(name="non-matched channel")])

        assert_that(matched_channel, is_(None))

    def test_find_channel_match_more_than_one_channel_found(self):
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [mocked_channel(name="matched_general"),
                                                                        mocked_channel(name="another-matched-general")])

        assert_that(matched_channel, is_(None))

    def test_find_channel_match_more_than_one_channel_found_and_player_informed(self):
        sending_player = fake_player(steam_id=1, name="Player")
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches("general",
                                                                       [mocked_channel(name="matched_general"),
                                                                        mocked_channel(name="another-matched-general")],
                                                                       sending_player)

        verify(sending_player).tell("Found ^62^7 matching discord channels for #general:")
        verify(sending_player).tell("#matched_general #another-matched-general ")
        assert_that(matched_channel, is_(None))

    def test_triggered_message(self):
        trigger_channel1 = self.triggered_channel()

        trigger_channel2 = mocked_channel(id=789)
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(trigger_channel2)

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great!")

        verify(trigger_channel1).send("**Chatting player**: QL is great!")
        verify(trigger_channel2).send("**Chatting player**: QL is great!")

    def test_triggered_message_replaces_mentions(self):
        self.setup_v0_16_discord_library()

        trigger_channel1 = self.triggered_channel()

        mentioned_user = mocked_user(id=123, name="chatter")
        mentioned_channel = mocked_channel(id=456, name="mentioned-channel")
        self.setup_discord_members(mentioned_user)
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @chatter #mention !")

        verify(self.discord_client).send_message(trigger_channel1,
                                                 "**Chatting player**: QL is great, {} {} !"
                                                 .format(mentioned_user.mention, mentioned_channel.mention))

    def test_triggered_message_no_triggered_channels_configured(self):
        when2(Plugin.get_cvar, "qlx_discordTriggeredChannelIds", set).thenReturn(set())
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v0_16_discord_library()

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @member #mention !")

        verify(self.discord_client, times=0).send_message(any, any)

    def test_triggered_message_no_replacement_configured(self):
        when2(Plugin.get_cvar, "qlx_discordReplaceMentionsForTriggeredMessages", bool).thenReturn(False)
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_v0_16_discord_library()

        trigger_channel1 = self.triggered_channel()

        mentioned_channel = mocked_channel(id=456, name="mentioned-channel")
        self.setup_discord_members()
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @member #mention !")

        verify(self.discord_client).send_message(trigger_channel1,
                                                 "**Chatting player**: QL is great, @member #mention !")
