import asyncio
import logging

from typing import Set
from unittest.mock import AsyncMock

import pytest
from mockito import mock, unstub, verify, when  # type: ignore
from mockito.matchers import matches, arg_that  # type: ignore
from hamcrest import assert_that, equal_to

from undecorated import undecorated  # type: ignore

# noinspection PyPackageRequirements
import discord

# noinspection PyPackageRequirements
from discord import ChannelType, User, Message, TextChannel, Status

# noinspection PyPackageRequirements
from discord.ext.commands import Bot

from minqlx_plugin_test import (
    connected_players,
    setup_cvars,
    assert_plugin_sent_to_console,
    fake_player,
    player_that_matches,
    setup_cvar,
)

import minqlx
from mydiscordbot import mydiscordbot, MinqlxHelpCommand, SimpleAsyncDiscord


class TestMyDiscordBotTests:
    def setup_method(self):
        connected_players()
        self.discord = mock(spec=SimpleAsyncDiscord, strict=False)
        setup_cvars({"qlx_discordQuakeRelayMessageFilters": r"^\!s$, ^\!p$"})
        self.plugin = mydiscordbot(discord_client=self.discord)

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    @staticmethod
    def test_constructor():
        assert_plugin_sent_to_console(matches("mydiscordbot Version: "), atleast=1)

    def test_handle_unload_for_plugin(self):
        self.plugin.handle_plugin_unload("mydiscordbot")

        verify(self.discord).stop()

    def test_handle_unload_of_other_plugin(self):
        self.plugin.handle_plugin_unload("otherplugin")

        verify(self.discord, times=0).stop()

    def test_handle_ql_chat_message_relayed(self):
        chatter = fake_player(1, "Chatter")
        self.plugin.handle_ql_chat(
            fake_player(1, "Chatter"), "relayed message", minqlx.ChatChannel()
        )

        verify(self.discord).relay_chat_message(
            player_that_matches(chatter), "", "relayed message"
        )

    def test_handle_ql_teamchat_message_relayed(self):
        chatter = fake_player(1, "Chatter")
        self.plugin.handle_ql_chat(
            fake_player(1, "Chatter"), "relayed message", minqlx.RED_TEAM_CHAT_CHANNEL
        )

        verify(self.discord).relay_team_chat_message(
            player_that_matches(chatter), " *(to red team)*", "relayed message"
        )

    def test_handle_ql_chat_message_on_filtered_out_channel(self):
        self.plugin.handle_ql_chat(
            fake_player(1, "Chatter"), "relayed message", minqlx.ConsoleChannel()
        )

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_ql_chat_message_on_filtered_out_messagel(self):
        self.plugin.handle_ql_chat(
            fake_player(1, "Chatter"), "!s", minqlx.RED_TEAM_CHAT_CHANNEL
        )

        verify(self.discord, times=0).relay_chat_message(any, any, any)

    def test_handle_player_connects(self):
        undecorated(self.plugin.handle_player_connect)(
            self.plugin, fake_player(1, "Connecting Player")
        )

        verify(self.discord).relay_message("_Connecting Player connected._")

    def test_handle_player_with_asterisk_connects(self):
        undecorated(self.plugin.handle_player_connect)(
            self.plugin, fake_player(1, "Connecting*Player")
        )

        verify(self.discord).relay_message(r"_Connecting\*Player connected._")

    def test_handle_player_with_underscore_connects(self):
        undecorated(self.plugin.handle_player_connect)(
            self.plugin, fake_player(1, "Connecting_Player")
        )

        verify(self.discord).relay_message(r"_Connecting\_Player connected._")

    def test_handle_player_disconnects(self):
        undecorated(self.plugin.handle_player_disconnect)(
            self.plugin, fake_player(1, "Disconnecting Player"), "disconnected"
        )

        verify(self.discord).relay_message("_Disconnecting Player disconnected._")

    def test_handle_player_times_out(self):
        undecorated(self.plugin.handle_player_disconnect)(
            self.plugin, fake_player(1, "Disconnecting Player"), "timed out"
        )

        verify(self.discord).relay_message("_Disconnecting Player timed out._")

    def test_handle_player_is_kicked(self):
        undecorated(self.plugin.handle_player_disconnect)(
            self.plugin, fake_player(1, "Disconnecting Player"), "was kicked"
        )

        verify(self.discord).relay_message("_Disconnecting Player was kicked._")

    def test_handle_player_is_kicked_with_reason(self):
        undecorated(self.plugin.handle_player_disconnect)(
            self.plugin, fake_player(1, "Disconnecting Player"), "llamah"
        )

        verify(self.discord).relay_message(
            "_Disconnecting Player was kicked (llamah)._"
        )

    def test_handle_map(self):
        self.plugin.handle_map("Theatre of Pain", "ca")

        verify(self.discord).relay_message("*Changing map to Theatre of Pain...*")

    def test_handle_vote_started_by_player(self):
        self.plugin.handle_vote_started(fake_player(1, "Votecaller"), "kick", "asdf")

        verify(self.discord).relay_message("_Votecaller called a vote: kick asdf_")

    def test_handle_vote_started_by_the_server(self):
        self.plugin.handle_vote_started(None, "map", "campgrounds")

        verify(self.discord).relay_message(
            "_The server called a vote: map campgrounds_"
        )

    def test_handle_vote_with_escaped_characters(self):
        self.plugin.handle_vote_started(
            fake_player(1, "Vote*Caller"), "map", "13house_a1"
        )

        verify(self.discord).relay_message(
            r"_Vote\*Caller called a vote: map 13house\_a1_"
        )

    def test_handle_vote_passed(self):
        votes = (4, 3)
        self.plugin.handle_vote_ended(votes, "map", "campgrounds", True)

        verify(self.discord).relay_message("*Vote passed (4 - 3).*")

    def test_handle_vote_failed(self):
        votes = (1, 8)
        self.plugin.handle_vote_ended(votes, "map", "overkill", False)

        verify(self.discord).relay_message("*Vote failed.*")

    @pytest.mark.parametrize(
        "game_in_warmup",
        ["game_type=ca, map=campgrounds, map_title=Campgrounds, maxclients=16"],
        indirect=True,
    )
    def test_game_countdown(self, game_in_warmup):
        connected_players()
        undecorated(self.plugin.handle_game_countdown_or_end)(self.plugin)

        verify(self.discord).relay_message(
            "Warmup on **Campgrounds** (CA) with **0/16** players. "
        )

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_game_countdown_with_no_game(self):
        undecorated(self.plugin.handle_game_countdown_or_end)(self.plugin)

        verify(self.discord, times=0).relay_message(any)

    def test_cmd_discord_message_too_short(self):
        response = self.plugin.cmd_discord(
            fake_player(1, "Triggering Player"), ["!discord"], minqlx.CHAT_CHANNEL
        )

        assert_that(response, equal_to(minqlx.RET_USAGE))

    def test_cmd_discord_message_triggered(self):
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discord(
            triggering_player, ["!discord", "asdf"], minqlx.CHAT_CHANNEL
        )

        verify(self.discord).triggered_message(triggering_player, "asdf")
        assert_plugin_sent_to_console("Message 'asdf' sent to discord chat!")

    @staticmethod
    def test_get_game_info_in_warmup(game_in_warmup):
        game_info = mydiscordbot.get_game_info(game_in_warmup)

        assert_that(game_info, equal_to("Warmup"))

    @staticmethod
    def test_get_game_info_in_countdown(game_in_countdown):
        game_info = mydiscordbot.get_game_info(game_in_countdown)

        assert_that(game_info, equal_to("Match starting"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress", ["roundlimit=8, red_score=1, blue_score=2"], indirect=True
    )
    def test_get_game_info_in_progress(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match in progress: **1** - **2**"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress", ["roundlimit=8, red_score=8, blue_score=2"], indirect=True
    )
    def test_get_game_info_red_hit_roundlimit(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **8** - **2**"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress", ["roundlimit=8, red_score=5, blue_score=8"], indirect=True
    )
    def test_get_game_info_blue_hit_roundlimit(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **8**"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress",
        ["roundlimit=8, red_score=-999, blue_score=3"],
        indirect=True,
    )
    def test_get_game_info_red_player_dropped_out(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **-999** - **3**"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress",
        ["roundlimit=8, red_score=5, blue_score=-999"],
        indirect=True,
    )
    def test_get_game_info_blue_player_dropped_out(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **-999**"))

    @staticmethod
    @pytest.mark.parametrize(
        "game_in_progress",
        ["state=asdf, roundlimit=8, red_score=1, blue_score=2"],
        indirect=True,
    )
    def test_get_game_info_unknown_game_state(game_in_progress):
        game_info = mydiscordbot.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Warmup"))

    @staticmethod
    def test_player_data_with_players_on_both_teams():
        connected_players(
            fake_player(1, "Player1", "red", score=1),
            fake_player(2, "Player2", "blue", score=3),
            fake_player(3, "Player3", "blue", score=2),
            fake_player(4, "Player4", "red", score=5),
        )

        player_data = mydiscordbot.player_data()

        assert_that(
            player_data,
            equal_to(
                "\n**R:** **Player4**(5) **Player1**(1) \n**B:** **Player2**(3) **Player3**(2) "
            ),
        )

    @staticmethod
    def test_player_data_with_just_red_players():
        connected_players(
            fake_player(1, "Player1", "red"), fake_player(4, "Player4", "red")
        )

        player_data = mydiscordbot.player_data()

        assert_that(player_data, equal_to("\n**R:** **Player1**(0) **Player4**(0) "))

    @staticmethod
    def test_player_data_with_just_blue_players():
        connected_players(
            fake_player(2, "Player2", "blue"), fake_player(3, "Player3", "blue")
        )

        player_data = mydiscordbot.player_data()

        assert_that(player_data, equal_to("\n**B:** **Player2**(0) **Player3**(0) "))

    @staticmethod
    def test_team_data_with_empty_player_list():
        team_data = mydiscordbot.team_data([])

        assert_that(team_data, equal_to(""))

    @staticmethod
    def test_team_data_with_limit():
        player_list = [
            fake_player(1, "Player1", "red", score=1),
            fake_player(2, "Player2", "red", score=52),
            fake_player(3, "Player3", "red", score=55),
            fake_player(4, "Player4", "red", score=2),
            fake_player(5, "Player5", "red", score=35),
            fake_player(6, "Player6", "red", score=5),
            fake_player(7, "Player7", "red", score=7),
        ]
        team_data = mydiscordbot.team_data(player_list, limit=5)
        assert_that(
            team_data,
            equal_to(
                "**Player3**(55) **Player2**(52) **Player5**(35) **Player7**(7) **Player6**(5) "
            ),
        )

    def test_cmd_discordbot_invalid(self):
        triggering_player = fake_player(1, "Triggering Player")
        return_code = self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "asdf"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    def test_cmd_discordbot_too_many_arguments(self):
        triggering_player = fake_player(1, "Triggering Player")
        return_code = self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "status", "asdf"], minqlx.CHAT_CHANNEL
        )

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    def test_cmd_discordbot_status(self, mock_channel):
        when(self.discord).status().thenReturn("Discord status message")
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "status"], mock_channel
        )

        mock_channel.assert_was_replied("Discord status message")

    def test_cmd_discordbot_status2(self, mock_channel):
        when(self.discord).status().thenReturn("Discord status message")
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(triggering_player, ["!discordbot"], mock_channel)

        mock_channel.assert_was_replied("Discord status message")

    def test_cmd_discordbot_connect(self, mock_channel):
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "connect"], mock_channel
        )

        mock_channel.assert_was_replied("Connecting to Discord...")
        verify(self.discord).run()

    def test_cmd_discordbot_connect_when_already_connected(self, mock_channel):
        when(self.discord).is_discord_logged_in().thenReturn(True)
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "connect"], mock_channel
        )

        mock_channel.assert_was_replied("Connecting to Discord...")
        verify(self.discord, times=0).run()

    def test_cmd_discordbot_disconnect(self, mock_channel):
        when(self.discord).is_discord_logged_in().thenReturn(True)
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "disconnect"], mock_channel
        )

        mock_channel.assert_was_replied("Disconnecting from Discord...")
        verify(self.discord).stop()

    def test_cmd_discordbot_disconnect_when_already_disconnected(self, mock_channel):
        when(self.discord).is_discord_logged_in().thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "disconnect"], mock_channel
        )

        mock_channel.assert_was_replied("Disconnecting from Discord...")
        verify(self.discord, times=0).stop()

    def test_cmd_discordbot_reconnect(self, mock_channel):
        when(self.discord).is_discord_logged_in().thenReturn(True).thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "reconnect"], mock_channel
        )

        mock_channel.assert_was_replied("Reconnecting to Discord...")
        verify(self.discord).stop()
        verify(self.discord).run()

    def test_cmd_discordbot_reconnect_when_disconnected(self, mock_channel):
        when(self.discord).is_discord_logged_in().thenReturn(False)
        triggering_player = fake_player(1, "Triggering Player")
        self.plugin.cmd_discordbot(
            triggering_player, ["!discordbot", "reconnect"], mock_channel
        )

        mock_channel.assert_was_replied("Reconnecting to Discord...")
        verify(self.discord, times=0).stop()
        verify(self.discord).run()


def mocked_discord_user(_id=777, name="Some-Discord-User", nick=None):
    user = mock(spec=User)

    user.id = _id
    user.name = name
    user.nick = nick
    user.mention = f"<@{user.id}"

    return user


def mocked_discord_channel(
    _id=666, name="channel-name", channel_type=ChannelType.text, topic=None
):
    channel = mock(spec=TextChannel)

    channel.id = _id
    channel.name = name
    channel._type = str(channel_type)
    channel.type = channel_type
    channel.topic = topic
    channel.mention = f"<#{channel.id}>"

    channel.send = AsyncMock()
    channel.edit = AsyncMock()

    return channel


def mocked_discord_message(
    content="message content",
    user=mocked_discord_user(),
    channel=mocked_discord_channel(),
):
    message = mock(spec=Message)

    message.content = content
    message.clean_content = content
    message.author = user
    message.channel = channel

    return message


class TestMinqlxHelpCommand:
    def setup_method(self):
        self.help_command = MinqlxHelpCommand()
        self.help_command.context = mock({"prefix": "!", "invoked_with": "help"})

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_get_ending_note(self):
        ending_note = self.help_command.get_ending_note()

        assert_that(
            ending_note, equal_to("Type !help command for more info on a command.")
        )


def assert_matching_string_send_to_discord_context(context, matcher):
    context.send.assert_called_once()
    assert_that(context.send.call_args.args[0], matcher)


def assert_text_was_sent_to_discord_channel(channel, matcher):
    channel.send.assert_called_once()
    assert_that(channel.send.call_args.args[0], matcher)


class TestSimpleAsyncDiscord:
    def setup_method(self):
        setup_cvars(
            {
                "qlx_owner": "1234567890",
                "qlx_discordBotToken": "bottoken",
                "qlx_discordRelayChannelIds": "1234",
                "qlx_discordTriggeredChannelIds": "456, 789",
                "qlx_discordUpdateTopicOnTriggeredChannels": "1",
                "qlx_discordKeepTopicSuffixChannelIds": "1234, 456",
                "qlx_discordKeptTopicSuffixes": "{1234: '', 456: ''}",
                "qlx_discordUpdateTopicInterval": "305",
                "qlx_discordTriggerTriggeredChannelChat": "trigger",
                "qlx_discordCommandPrefix": "%",
                "qlx_discordTriggerStatus": "minqlx",
                "qlx_discordMessagePrefix": "[DISCORD]",
                "qlx_discordEnableHelp": "1",
                "qlx_discordEnableVersion": "1",
                "qlx_displayChannelForDiscordRelayChannels": "0",
                "qlx_discordReplaceMentionsForRelayedMessages": "0",
                "qlx_discordReplaceMentionsForTriggeredMessages": "1",
                "qlx_discordAdminPassword": "adminpassword",
                "qlx_discordAuthCommand": "auth",
                "qlx_discordExecPrefix": "exec",
                "qlx_discordLogToSeparateLogfile": "0",
                "qlx_discordTriggeredChatMessagePrefix": "",
                "qlx_discordRelayTeamchatChannelIds": "242",
                "qlx_discord_extensions": "",
            }
        )

        self.logger = mock(spec=logging.Logger, strict=False)
        self.discord = SimpleAsyncDiscord("version information", self.logger)

        self.setup_discord_library()

    @staticmethod
    def teardown_method():
        unstub()

    def setup_discord_client_mock_common(self):
        self.discord_client = mock(spec=Bot, strict=False)

        self.discord_client.change_presence = AsyncMock()
        self.discord_client.tree = mock(
            spec=discord.app_commands.CommandTree, strict=False
        )
        self.discord_client.tree.sync = AsyncMock()

        self.discord_client.user = mock(User, strict=False)
        self.discord_client.user.name = "Bot Name"
        self.discord_client.user.id = 24680

        self.setup_discord_members()
        self.setup_discord_channels()

        self.discord_client.loop = asyncio.new_event_loop()

    def setup_discord_library(self):
        self.setup_discord_client_mock_common()

        when(self.discord_client).is_ready().thenReturn(True)
        when(self.discord_client).is_closed().thenReturn(False)

        self.discord.discord = self.discord_client

    def mocked_context(
        self,
        prefix="%",
        bot=None,
        message=mocked_discord_message(),
        invoked_with="asdf",
    ):
        context = mock({"send": AsyncMock()})
        context.prefix = prefix
        context.bot = self.discord_client
        if bot is not None:
            context.bot = bot
        context.message = message
        context.invoked_with = invoked_with

        return context

    def relay_channel(self):
        channel = mocked_discord_channel(_id=1234, name="relay-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def relay_teamchat_channel(self):
        channel = mocked_discord_channel(_id=242, name="relay-teamchat-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def triggered_channel(self):
        channel = mocked_discord_channel(_id=456, name="triggered-channel")

        when(self.discord_client).get_channel(channel.id).thenReturn(channel)

        return channel

    def setup_discord_members(self, *users):
        when(self.discord_client).get_all_members().thenReturn(list(users))

    def setup_discord_channels(self, *channels):
        when(self.discord_client).get_all_channels().thenReturn(list(channels))

    def verify_added_command(self, name, callback, checks=None):
        if checks is None:
            verify(self.discord_client).add_command(
                arg_that(
                    lambda command: command.name == name
                    and command.callback == callback
                )
            )
        else:
            verify(self.discord_client).add_command(
                arg_that(
                    lambda command: command.name == name
                    and command.callback == callback
                    and command.checks == checks
                )
            )

    def test_status_connected(self):
        status = self.discord.status()

        assert_that(status, equal_to("Discord connection up and running."))

    def test_status_no_client(self):
        self.discord.discord = None

        status = self.discord.status()

        assert_that(status, equal_to("No discord connection set up."))

    def test_status_client_not_connected(self):
        when(self.discord_client).is_ready().thenReturn(False)

        status = self.discord.status()

        assert_that(status, equal_to("Discord client not connected."))

    @pytest.mark.asyncio
    async def test_initialize_bot(self):
        self.discord.initialize_bot(self.discord_client)

        self.verify_added_command(name="version", callback=self.discord.version)
        verify(self.discord_client).add_listener(self.discord.on_ready)
        verify(self.discord_client).add_listener(self.discord.on_message)

    @pytest.mark.asyncio
    async def test_disable_version(self):
        self.discord.discord_version_enabled = False
        self.discord.initialize_bot(self.discord_client)

        verify(self.discord_client, times=0).add_command(
            name="version", callback=self.discord.version
        )

    @pytest.mark.asyncio
    async def test_version(self):
        context = self.mocked_context()

        await self.discord.version(context)

        assert_matching_string_send_to_discord_context(
            context, "```version information```"
        )

    @pytest.mark.asyncio
    async def test_on_ready(self):
        self.setup_discord_library()

        await self.discord.on_ready()

        self.discord_client.change_presence.assert_called_once_with(
            activity=discord.Game(name="Quake Live")
        )

    @pytest.mark.asyncio
    async def test_on_message_is_relayed(self, mock_channel):
        message = mocked_discord_message(
            content="some chat message",
            user=mocked_discord_user(name="Sender"),
            channel=self.relay_channel(),
        )

        minqlx.CHAT_CHANNEL = mock_channel

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL).reply("[DISCORD] ^6Sender^7:^2 some chat message")

    @pytest.mark.asyncio
    async def test_on_message_by_user_with_nickname(self, mock_channel):
        message = mocked_discord_message(
            content="some chat message",
            user=mocked_discord_user(name="Sender", nick="SenderNick"),
            channel=self.relay_channel(),
        )

        minqlx.CHAT_CHANNEL = mock_channel

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^6SenderNick^7:^2 some chat message"
        )

    @pytest.mark.asyncio
    async def test_on_message_in_wrong_channel(self, mock_channel):
        message = mocked_discord_message(
            content="some chat message", channel=self.triggered_channel()
        )

        minqlx.CHAT_CHANNEL = mock_channel

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @pytest.mark.asyncio
    async def test_on_message_too_short_message(self, mock_channel):
        message = mocked_discord_message(content="", channel=self.relay_channel())

        minqlx.CHAT_CHANNEL = mock_channel

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @pytest.mark.asyncio
    async def test_on_message_from_bot(self, mock_channel):
        message = mocked_discord_message(
            content="", user=self.discord_client.user, channel=self.relay_channel()
        )

        minqlx.CHAT_CHANNEL = mock_channel

        await self.discord.on_message(message)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    @pytest.mark.asyncio
    async def test_on_message_without_message(self, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel

        # noinspection PyTypeChecker
        await self.discord.on_message(None)

        verify(minqlx.CHAT_CHANNEL, times=0).reply(any)

    def test_stop_discord_client(self):
        self.discord_client.close = AsyncMock()

        self.discord.stop()

        self.discord_client.change_presence.assert_called_once_with(
            status=Status.offline
        )
        self.discord_client.close.assert_called_once()

    def test_stop_discord_client_discord_not_initialized(self):
        self.discord.discord = None

        self.discord.stop()

        verify(self.discord_client, times=0).change_presence(status="offline")
        verify(self.discord_client, times=0).logout()

    def test_relay_message(self):
        relay_channel = self.relay_channel()

        self.discord.relay_message("awesome relayed message")

        assert_text_was_sent_to_discord_channel(
            relay_channel, "awesome relayed message"
        )

    def test_relay_message_with_not_connected_client(self):
        relay_channel = self.relay_channel()
        when(self.discord_client).is_ready().thenReturn(False)

        self.discord.relay_message("awesome relayed message")

        verify(relay_channel, times=0).send(any)

    def test_send_to_discord_channels_with_no_channel_ids(self):
        string_set: Set[str] = set()
        self.discord.send_to_discord_channels(string_set, "awesome relayed message")

        verify(self.discord_client, times=0)

    def test_send_to_discord_channels_for_non_existing_channel(self):
        self.discord.send_to_discord_channels({"6789"}, "awesome relayed message")

        verify(self.discord_client, times=0).send_message(any, any)

    def test_relay_chat_message_simple_message(self):
        relay_channel = self.relay_channel()
        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            relay_channel, "**Chatting player**: QL is great!"
        )

    def test_relay_chat_message_with_asterisks_in_playername(self):
        relay_channel = self.relay_channel()
        player = fake_player(steam_id=1, name="*Chatting* player")
        minqlx_channel = ""

        self.discord.relay_chat_message(player, minqlx_channel, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            relay_channel, r"**\*Chatting\* player**: QL is great!"
        )

    def test_relay_chat_message_replace_user_mention(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()
        mentioned_user = mocked_discord_user(_id=123, name="chatter")
        self.setup_discord_members(mentioned_user)
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, @chatter !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_channel,
            f"**Chatting player**: QL is great, {mentioned_user.mention} !",
        )

    def test_relay_chat_message_mentioned_member_not_found(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, @chatter !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_channel, "**Chatting player**: QL is great, @chatter !"
        )

    def test_relay_chat_message_does_not_replace_all_everyone_and_here(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()
        unmentioned_user = mocked_discord_user(_id=123, name="chatter")
        self.setup_discord_members(unmentioned_user)
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, @all @everyone @here !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_channel, "**Chatting player**: QL is great, @all @everyone @here !"
        )

    def test_relay_chat_message_replace_channel_mention(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()
        mentioned_channel = mocked_discord_channel(_id=456, name="mentioned-channel")
        self.setup_discord_members()
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, #mention !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_channel,
            f"**Chatting player**: QL is great, {mentioned_channel.mention} !",
        )

    def test_relay_chat_message_mentioned_channel_not_found(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()
        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, #mention !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_channel, "**Chatting player**: QL is great, #mention !"
        )

    def test_relay_chat_message_discord_not_logged_in(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_channel = self.relay_channel()
        when(self.discord_client).is_ready().thenReturn(False)

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_chat_message(
            player, minqlx_channel, "QL is great, @member #mention !"
        )

        verify(relay_channel, times=0).send(any)

    def test_relay_team_chat_message_simple_message(self):
        relay_teamchat_channel = self.relay_teamchat_channel()
        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(player, minqlx_channel, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel, "**Chatting player**: QL is great!"
        )

    def test_relay_team_chat_message_with_asterisks_in_playername(self):
        relay_teamchat_channel = self.relay_teamchat_channel()
        player = fake_player(steam_id=1, name="*Chatting* player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(player, minqlx_channel, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel, r"**\*Chatting\* player**: QL is great!"
        )

    def test_relay_team_chat_message_replace_user_mention(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_teamchat_channel = self.relay_teamchat_channel()
        mentioned_user = mocked_discord_user(_id=123, name="chatter")
        self.setup_discord_members(mentioned_user)
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(
            player, minqlx_channel, "QL is great, @chatter !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel,
            f"**Chatting player**: QL is great, {mentioned_user.mention} !",
        )

    def test_relay_team_chat_message_mentioned_member_not_found(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_teamchat_channel = self.relay_teamchat_channel()
        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(
            player, minqlx_channel, "QL is great, @chatter !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel, "**Chatting player**: QL is great, @chatter !"
        )

    def test_relay_team_chat_message_replace_channel_mention(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_teamchat_channel = self.relay_teamchat_channel()
        mentioned_channel = mocked_discord_channel(_id=456, name="mentioned-channel")
        self.setup_discord_members()
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(
            player, minqlx_channel, "QL is great, #mention !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel,
            f"**Chatting player**: QL is great, {mentioned_channel.mention} !",
        )

    def test_relay_team_chat_message_mentioned_channel_not_found(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_teamchat_channel = self.relay_teamchat_channel()
        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(
            player, minqlx_channel, "QL is great, #mention !"
        )

        assert_text_was_sent_to_discord_channel(
            relay_teamchat_channel, "**Chatting player**: QL is great, #mention !"
        )

    def test_relay_team_chat_message_discord_not_logged_in(self):
        setup_cvar("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        relay_teamchat_channel = self.relay_teamchat_channel()
        when(self.discord_client).is_ready().thenReturn(False)

        player = fake_player(steam_id=1, name="Chatting player")
        minqlx_channel = ""

        self.discord.relay_team_chat_message(
            player, minqlx_channel, "QL is great, @member #mention !"
        )

        verify(relay_teamchat_channel, times=0).send(any)

    @staticmethod
    def test_find_user_match_exact_match():
        exact_matching_user = mocked_discord_user(name="user")
        other_user = mocked_discord_user(name="non-exact-match-User")

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user", [exact_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(exact_matching_user))

    @staticmethod
    def test_find_user_match_case_insensitive_match():
        case_insensitive_matching_user = mocked_discord_user(name="uSeR")
        other_user = mocked_discord_user(name="non-matched user")

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user", [case_insensitive_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(case_insensitive_matching_user))

    @staticmethod
    def test_find_user_match_exact_nick_match():
        exact_matching_user = mocked_discord_user(name="non-matching name", nick="user")
        other_user = mocked_discord_user(name="non-exact-match-User")

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user", [exact_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(exact_matching_user))

    @staticmethod
    def test_find_user_match_case_insensitive_nick_match():
        exact_matching_user = mocked_discord_user(name="non-matching name", nick="UseR")
        other_user = mocked_discord_user(
            name="non-matched user", nick="non-matched nick"
        )

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user", [exact_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(exact_matching_user))

    @staticmethod
    def test_find_user_match_fuzzy_match_on_name():
        fuzzy_matching_user = mocked_discord_user(name="matching-GeneRal-user")
        other_user = mocked_discord_user(name="non-matched channel")

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "UsEr", [fuzzy_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(fuzzy_matching_user))

    @staticmethod
    def test_find_user_match_fuzzy_match_on_nick():
        fuzzy_matching_user = mocked_discord_user(
            name="non-matchin-usr", nick="matching-General-uSeR"
        )
        other_user = mocked_discord_user(name="non-matched channel")

        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "UsEr", [fuzzy_matching_user, other_user]
        )

        assert_that(matched_user, equal_to(fuzzy_matching_user))

    @staticmethod
    def test_find_user_match_no_match_found():
        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "awesome",
            [
                mocked_discord_user(name="no_match-user"),
                mocked_discord_user(name="non-matched user"),
            ],
        )

        assert_that(matched_user, equal_to(None))

    @staticmethod
    def test_find_user_match_more_than_one_user_found():
        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user",
            [
                mocked_discord_user(name="matched_user"),
                mocked_discord_user(name="another-matched-uSEr"),
            ],
        )

        assert_that(matched_user, equal_to(None))

    @staticmethod
    def test_find_user_match_more_than_one_user_found_and_player_informed():
        sending_player = fake_player(steam_id=1, name="Player")
        matched_user = SimpleAsyncDiscord.find_user_that_matches(
            "user",
            [
                mocked_discord_user(name="matched_user"),
                mocked_discord_user(name="another-matched-uSEr"),
            ],
            sending_player,
        )

        verify(sending_player).tell("Found ^62^7 matching discord users for @user:")
        verify(sending_player).tell("@matched_user @another-matched-uSEr ")
        assert_that(matched_user, equal_to(None))

    @staticmethod
    def test_find_channel_match_exact_match():
        exact_matching_channel = mocked_discord_channel(name="general")
        other_channel = mocked_discord_channel(name="General")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general", [exact_matching_channel, other_channel]
        )

        assert_that(matched_channel, equal_to(exact_matching_channel))

    @staticmethod
    def test_find_channel_match_case_insensitive_match():
        case_insensitive_matching_channel = mocked_discord_channel(name="GeNeRaL")
        other_channel = mocked_discord_channel(name="non-matched General")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general", [case_insensitive_matching_channel, other_channel]
        )

        assert_that(matched_channel, equal_to(case_insensitive_matching_channel))

    @staticmethod
    def test_find_channel_match_fuzzy_match():
        fuzzy_matching_channel = mocked_discord_channel(name="matching-GeneRal-channel")
        other_channel = mocked_discord_channel(name="non-matched channel")

        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general", [fuzzy_matching_channel, other_channel]
        )

        assert_that(matched_channel, equal_to(fuzzy_matching_channel))

    @staticmethod
    def test_find_channel_match_no_match_found():
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general",
            [
                mocked_discord_channel(name="no_match-channel"),
                mocked_discord_channel(name="non-matched channel"),
            ],
        )

        assert_that(matched_channel, equal_to(None))

    @staticmethod
    def test_find_channel_match_more_than_one_channel_found():
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general",
            [
                mocked_discord_channel(name="matched_general"),
                mocked_discord_channel(name="another-matched-general"),
            ],
        )

        assert_that(matched_channel, equal_to(None))

    @staticmethod
    def test_find_channel_match_more_than_one_channel_found_and_player_informed():
        sending_player = fake_player(steam_id=1, name="Player")
        matched_channel = SimpleAsyncDiscord.find_channel_that_matches(
            "general",
            [
                mocked_discord_channel(name="matched_general"),
                mocked_discord_channel(name="another-matched-general"),
            ],
            sending_player,
        )

        verify(sending_player).tell(
            "Found ^62^7 matching discord channels for #general:"
        )
        verify(sending_player).tell("#matched_general #another-matched-general ")
        assert_that(matched_channel, equal_to(None))

    def test_triggered_message(self):
        triggered_channel = self.triggered_channel()
        trigger_channel2 = mocked_discord_channel(_id=789)
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(
            trigger_channel2
        )

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            triggered_channel, "**Chatting player**: QL is great!"
        )
        assert_text_was_sent_to_discord_channel(
            trigger_channel2, "**Chatting player**: QL is great!"
        )

    def test_triggered_message_with_escaped_playername(self):
        triggered_channel = self.triggered_channel()
        trigger_channel2 = mocked_discord_channel(_id=789)
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(
            trigger_channel2
        )

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="*Chatting_player*")

        self.discord.triggered_message(player, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            triggered_channel, r"**\*Chatting\_player\***: QL is great!"
        )
        assert_text_was_sent_to_discord_channel(
            trigger_channel2, r"**\*Chatting\_player\***: QL is great!"
        )

    def test_triggered_message_replaces_mentions(self):
        triggered_channel = self.triggered_channel()
        mentioned_user = mocked_discord_user(_id=123, name="chatter")
        mentioned_channel = mocked_discord_channel(_id=456, name="mentioned-channel")
        self.setup_discord_members(mentioned_user)
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @chatter #mention !")

        assert_text_was_sent_to_discord_channel(
            triggered_channel,
            f"**Chatting player**: QL is great, {mentioned_user.mention} {mentioned_channel.mention} !",
        )

    def test_triggered_message_no_triggered_channels_configured(self):
        setup_cvar("qlx_discordTriggeredChannelIds", "")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        triggered_channel = self.triggered_channel()

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @member #mention !")

        verify(triggered_channel, times=0).send(any)

    def test_triggered_message_no_replacement_configured(self):
        setup_cvar("qlx_discordReplaceMentionsForTriggeredMessages", "0")
        self.discord = SimpleAsyncDiscord("version information", self.logger)
        self.setup_discord_library()

        triggered_channel = self.triggered_channel()
        mentioned_channel = mocked_discord_channel(_id=456, name="mentioned-channel")
        self.setup_discord_members()
        self.setup_discord_channels(mentioned_channel)

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great, @member #mention !")

        assert_text_was_sent_to_discord_channel(
            triggered_channel, "**Chatting player**: QL is great, @member #mention !"
        )

    def test_prefixed_triggered_message(self):
        triggered_channel = self.triggered_channel()
        self.discord.discord_triggered_channel_message_prefix = "Server Prefix"

        trigger_channel2 = mocked_discord_channel(_id=789)
        when(self.discord_client).get_channel(trigger_channel2.id).thenReturn(
            trigger_channel2
        )

        self.setup_discord_members()
        self.setup_discord_channels()

        player = fake_player(steam_id=1, name="Chatting player")

        self.discord.triggered_message(player, "QL is great!")

        assert_text_was_sent_to_discord_channel(
            triggered_channel, "Server Prefix **Chatting player**: QL is great!"
        )
        assert_text_was_sent_to_discord_channel(
            trigger_channel2, "Server Prefix **Chatting player**: QL is great!"
        )
