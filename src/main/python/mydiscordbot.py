"""
This is a plugin created by ShiN0
Copyright (c) 2017 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one, except for the version command related code.

The basic ideas for this plugin came from Gelenkbusfahrer and roast
<https://github.com/roasticle/minqlx-plugins/blob/master/discordbot.py> and have been mainly discussed on the
fragstealers_inc discord tech channel of the Bus Station server(s).

You need to install discord.py in your python installation, i.e. python3 -m pip install -U discord.py
"""
from __future__ import annotations

import re
import asyncio
import threading

import logging
import os
from logging.handlers import RotatingFileHandler

from typing import Optional, Union

import minqlx
from minqlx import Plugin

# noinspection PyPackageRequirements
import discord  # type: ignore
# noinspection PyPackageRequirements
from discord import ChannelType, AllowedMentions  # type: ignore
# noinspection PyPackageRequirements
from discord.ext.commands import Bot, Command, DefaultHelpCommand, Context  # type: ignore
# noinspection PyPackageRequirements
import discord.ext.tasks  # type: ignore

plugin_version = "v2.0.0alpha"


# noinspection PyPep8Naming
class mydiscordbot(minqlx.Plugin):
    """
    The plugin's main purpose is to create a relay chat between the Quake Live chat and configured discord channels.
    There are two basic types of relay in this basic version of a discord plugin:
    * full relay between Quake Live chat and discord, where every text message that is happening is forwarded to the
    other system, and some basic Quake Live status updates are send to discord
    * triggered relay of specific messages between discord and Quake Live chat where a prefix needs to be used for the
    messages to be forwarded.

    These two modes can be combined, i.e. full relay to a broadcast channel, and specific messages from another channel.

    For a description on how to set up a bot for you discord network take a look `here
    <https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token>`.

    As of version 1.5 of the mydiscordbot, you also need to enable the Server Members Intent for the bot in order to be
    able to replace discord user mentions. If you don't need that, i.e. you did configured and of the
    qlx_discordReplaceMentions cvars as '0', you can leave it unchecked. By default, this will be enabled and therefore
    mandatory. Check  <https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents> for a description.

    Uses:
    * qlx_discordBotToken (default: "") The token of the discord bot to use to connect to discord.
    * qlx_discordRelayChannelIds (default: "") Comma separated list of channel ids for full relay.
    * qlx_discordRelayTeamchatChannelIds (default: "") Comma separated list of channel ids for relaying team chat
    messages.
    * qlx_discordTriggeredChannelIds (default: "") Comma separated list of channel ids for triggered relay.
    * qlx_discordTriggeredChatMessagePrefix (default: "") Prefix any triggered message from QL with this text portion.
    Useful when running multiple servers on the same host with the same discord connected to.
    * qlx_discordCommandPrefix (default: "!") Command prefix for all commands from discord
    * qlx_discordTriggerTriggeredChannelChat (default: "quakelive") Message prefix for the trigger on triggered relay
    channels.
    * qlx_discordTriggerStatus (default: "status") Trigger for having the bot send the current status of the game
    server.
    * qlx_discordMessagePrefix (default: "[DISCORD]") messages from discord to quake live will be prefixed with this
    prefix
    * qlx_discordEnableHelp (default: "1") indicates whether the bot will respond to !help or responses are completely
    switched off
    * qlx_discordEnableVersion (default: "1") indicates whether the bot will respond to !version or responses are
    completely switched off
    * qlx_displayChannelForDiscordRelayChannels (default: "1") display the channel name of the discord channel for
    configured relay channels
    * qlx_discordQuakeRelayMessageFilters (default: r"^\\!s$, ^\\!p$") comma separated list of regular expressions for
    messages that should not be sent from quake live to discord
    * qlx_discordReplaceMentionsForRelayedMessages (default: "1") replace mentions (@user and #channel) for messages
    sent towards relay channels
    * qlx_discordReplaceMentionsForTriggeredMessages (default: "1") replace mentions (@user and #channel) for triggered
    messages sent towards the triggered channels
    * qlx_discordLogToSeparateLogfile (default: "0") enables extended logging for the discord library (logs to
    minqlx_discord.log in the homepath)
    * qlx_discord_extensions (default: "") discord extensions to load after initializing
    """
    def __init__(self, discord_client: SimpleAsyncDiscord = None):
        super().__init__()

        # maybe initialize plugin cvars
        Plugin.set_cvar_once("qlx_discordBotToken", "")
        Plugin.set_cvar_once("qlx_discordRelayChannelIds", "")
        Plugin.set_cvar_once("qlx_discordRelayTeamchatChannelIds", "")
        Plugin.set_cvar_once("qlx_discordTriggeredChannelIds", "")
        Plugin.set_cvar_once("qlx_discordTriggeredChatMessagePrefix", "")
        Plugin.set_cvar_once("qlx_discordCommandPrefix", "!")
        Plugin.set_cvar_once("qlx_discordTriggerTriggeredChannelChat", "quakelive")
        Plugin.set_cvar_once("qlx_discordTriggerStatus", "status")
        Plugin.set_cvar_once("qlx_discordMessagePrefix", "[DISCORD]")
        Plugin.set_cvar_once("qlx_discordEnableHelp", "1")
        Plugin.set_cvar_once("qlx_discordEnableVersion", "1")
        Plugin.set_cvar_once("qlx_displayChannelForDiscordRelayChannels", "1")
        Plugin.set_cvar_once("qlx_discordQuakeRelayMessageFilters", r"^\!s$, ^\!p$")
        Plugin.set_cvar_once("qlx_discordReplaceMentionsForRelayedMessages", "1")
        Plugin.set_cvar_once("qlx_discordReplaceMentionsForTriggeredMessages", "1")
        Plugin.set_cvar_once("qlx_discordLogToSeparateLogfile", "0")
        Plugin.set_cvar_once("qlx_discord_extensions", "")

        # get the actual cvar values from the server
        self.discord_message_filters: set[str] = Plugin.get_cvar("qlx_discordQuakeRelayMessageFilters", set)

        # adding general plugin hooks
        self.add_hook("unload", self.handle_plugin_unload)
        self.add_hook("chat", self.handle_ql_chat, priority=minqlx.PRI_LOWEST)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_LOWEST)
        self.add_hook("player_disconnect", self.handle_player_disconnect, priority=minqlx.PRI_LOWEST)
        self.add_hook("map", self.handle_map)
        self.add_hook("vote_started", self.handle_vote_started)
        self.add_hook("vote_ended", self.handle_vote_ended)
        self.add_hook("game_countdown", self.handle_game_countdown_or_end, priority=minqlx.PRI_LOWEST)
        self.add_hook("game_end", self.handle_game_countdown_or_end, priority=minqlx.PRI_LOWEST)

        self.add_command("discord", self.cmd_discord, usage="<message>")
        self.add_command("discordbot", self.cmd_discordbot, permission=1,
                         usage="[status]|connect|disconnect|reconnect")

        # initialize the discord bot and its interactions on the discord server
        if discord_client is None:
            self.discord: SimpleAsyncDiscord = SimpleAsyncDiscord(self.version_information(), self.logger)
        else:
            self.discord = discord_client
        self.logger.info("Connecting to Discord...")
        self.discord.start()
        self.logger.info(self.version_information())
        Plugin.msg(self.version_information())

    def version_information(self) -> str:
        return f"{self.name} Version: {plugin_version}"

    def handle_plugin_unload(self, plugin: str) -> None:
        """
        Handler when a plugin is unloaded to make sure, that the connection to discord is properly closed when this
        plugin is unloaded.

        :param: plugin: the plugin that was unloaded.
        """
        if plugin == self.__class__.__name__:
            self.discord.stop()

    @staticmethod
    def game_status_information(game: minqlx.Game) -> str:
        """
        Generate the text for the topic set on discord channels.

        :param: game: the game to derive the status information from

        :return: the topic that represents the current game state.
        """
        ginfo = mydiscordbot.get_game_info(game)

        num_players = len(Plugin.players())
        max_players = game.maxclients

        maptitle = game.map_title if game.map_title else game.map
        gametype = game.type_short.upper()

        # CAUTION: if you change anything on the next line, you may need to change the topic_ending logic in
        #          :func:`mydiscordbot.update_topic_on_triggered_channels(self, topic)` to keep the right portion
        #          of the triggered relay channels' topics!
        return f"{ginfo} on **{Plugin.clean_text(maptitle)}** ({gametype}) " \
               f"with **{num_players}/{max_players}** players. "

    @staticmethod
    def get_game_info(game: minqlx.Game) -> str:
        """
        Helper to format the current ```game.state``` that may be used in status messages and setting of channel topics.

        :param: game: the game object to derive the information from

        :return: the current text representation of the game state
        """
        if game.state == "warmup":
            return "Warmup"
        if game.state == "countdown":
            return "Match starting"
        if game.roundlimit in [game.blue_score, game.red_score] or game.red_score < 0 or game.blue_score < 0:
            return f"Match ended: **{game.red_score}** - **{game.blue_score}**"
        if game.state == "in_progress":
            return f"Match in progress: **{game.red_score}** - **{game.blue_score}**"

        return "Warmup"

    @staticmethod
    def player_data() -> str:
        """
        Formats the top 5 scorers connected to the server in a string. The return value may be used for status messages
        and used in topics to indicate reveal more data about the server and its current game.

        :return: string of the current top5 scorers with the scores and connection time to the server
        """
        player_data = ""
        teams = Plugin.teams()
        if len(teams['red']) > 0:
            player_data += f"\n**R:** {mydiscordbot.team_data(teams['red'])}"
        if len(teams['blue']) > 0:
            player_data += f"\n**B:** {mydiscordbot.team_data(teams['blue'])}"

        return player_data

    @staticmethod
    def team_data(player_list: list[minqlx.Player], limit: int = None) -> str:
        """
        generates a sorted output of the team's player by their score

        :param: player_list: the list of players to generate the team output for
        :param: limit: (default: None) just list the top players up to the given limit
        :return: a discord ready text representation of the player's of that team by their score
        """
        if len(player_list) == 0:
            return ""

        players_by_score = sorted(player_list, key=lambda k: k.score, reverse=True)
        if limit:
            players_by_score = players_by_score[:limit]

        team_data = ""
        for player in players_by_score:
            team_data += f"**{discord.utils.escape_markdown(player.clean_name)}**({player.score}) "

        return team_data

    def is_filtered_message(self, msg: str) -> bool:
        """
        Checks whether the given message should be filtered and not be sent to discord.

        :param: msg: the message to check whether it should be filtered
        :return: whether the message should not be relayed to discord
        """
        for message_filter in self.discord_message_filters:
            matcher = re.compile(message_filter)
            if matcher.match(msg):
                return True

        return False

    def handle_ql_chat(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel) -> None:
        """
        Handle function for all chat messages on the server. This function will forward and messages on the Quake Live
        server to discord.

        :param: player: the player that sent the message
        :param: msg: the message that was sent
        :param: channel: the chnannel the message was sent to
        """
        handled_channels = {"chat": "",
                            "red_team_chat": " *(to red team)*",
                            "blue_team_chat": " *(to blue team)*",
                            "spectator_chat": " *(to specs)*"}
        if channel.name not in handled_channels:
            return

        if self.is_filtered_message(msg):
            return

        if channel.name in ["red_team_chat", "blue_team_chat"]:
            self.discord.relay_team_chat_message(player, handled_channels[channel.name], Plugin.clean_text(msg))
            return
        self.discord.relay_chat_message(player, handled_channels[channel.name], Plugin.clean_text(msg))

    @minqlx.delay(3)
    def handle_player_connect(self, player: minqlx.Player) -> None:
        """
        Handler called when a player connects. The method sends a corresponding message to the discord relay channels,
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param: player: the player that connected
        """
        content = f"_{discord.utils.escape_markdown(player.clean_name)} connected._"
        self.discord.relay_message(content)

    @minqlx.delay(3)
    def handle_player_disconnect(self, player: minqlx.Player, reason: str) -> None:
        """
        Handler called when a player disconnects. The method sends a corresponding message to the discord relay
        channels, and updates the relay channel topic as well as the trigger channels, when configured.

        :param: player: the player that connected
        :param: reason: the reason why the player left
        """
        if reason in ["disconnected", "timed out", "was kicked", "was kicked."]:
            reason_str = f"{reason}."
        else:
            reason_str = f"was kicked ({discord.utils.escape_markdown(Plugin.clean_text(reason))})."
        content = f"_{discord.utils.escape_markdown(player.clean_name)} {reason_str}_"
        self.discord.relay_message(content)

    def handle_map(self, mapname: str, _factory: str) -> None:
        """
        Handler called when a map is changed. The method sends a corresponding message to the discord relay channels.
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param: mapname: the new map
        :param: _factory: the map factory used
        """
        content = f"*Changing map to {discord.utils.escape_markdown(mapname)}...*"
        self.discord.relay_message(content)

    def handle_vote_started(self, caller: Optional[minqlx.Player], vote: str, args: str) -> None:
        """
        Handler called when a vote was started. The method sends a corresponding message to the discord relay channels.

        :param: caller: the player that initiated the vote
        :param: vote: the vote itself, i.e. map change, kick player, etc.
        :param: args: any arguments of the vote, i.e. map name, which player to kick, etc.
        """
        caller_name = discord.utils.escape_markdown(caller.clean_name) if caller else "The server"
        content = f"_{caller_name} called a vote: {vote} " \
                  f"{discord.utils.escape_markdown(Plugin.clean_text(args))}_"

        self.discord.relay_message(content)

    def handle_vote_ended(self, votes: tuple[int, int], _vote: str, _args: str, passed: bool) -> None:
        """
        Handler called when a vote was passed or failed. The method sends a corresponding message to the discord relay
        channels.

        :param: votes: the final votes
        :param: _vote: the initial vote that passed or failed, i.e. map change, kick player, etc.
        :param: _args: any arguments of the vote, i.e. map name, which player to kick, etc.
        :param: passed: boolean indicating whether the vote passed
        """
        if passed:
            content = f"*Vote passed ({votes[0]} - {votes[1]}).*"
        else:
            content = "*Vote failed.*"

        self.discord.relay_message(content)

    @minqlx.delay(1)
    def handle_game_countdown_or_end(self, *_args, **_kwargs) -> None:
        """
        Handler called when the game is in countdown, i.e. about to start. This function mainly updates the topics of
        the relay channels and the triggered channels (when configured), and sends a message to all relay channels.
        """
        game = self.game
        if game is None:
            return
        topic = mydiscordbot.game_status_information(game)
        top5_players = mydiscordbot.player_data()

        self.discord.relay_message(f"{topic}{top5_players}")

    def cmd_discord(self, player: minqlx.Player, msg: list[str], _channel: minqlx.AbstractChannel) -> int:
        """
        Handler of the !discord command. Forwards any messages after !discord to the discord triggered relay channels.

        :param: player: the player that send to the trigger
        :param: msg: the message the player sent (includes the trigger)
        :param: _channel: the channel the message came through, i.e. team chat, general chat, etc.
        """
        # when the message did not include anything to forward, show the usage help text.
        if len(msg) < 2:
            return minqlx.RET_USAGE

        self.discord.triggered_message(player, Plugin.clean_text(" ".join(msg[1:])))
        self.msg("Message to Discord chat cast!")
        return minqlx.RET_NONE

    def cmd_discordbot(self, _player: minqlx.Player, msg: list[str], channel: minqlx.AbstractChannel) -> int:
        """
        Handler for reconnecting the discord bot to discord in case it gets disconnected.

        :param: _player: the player that send to the trigger
        :param: msg: the original message the player sent (includes the trigger)
        :param: channel: the channel the message came through, i.e. team chat, general chat, etc.
        """
        if len(msg) > 2 or (len(msg) == 2 and msg[1] not in ["status", "connect", "disconnect", "reconnect"]):
            return minqlx.RET_USAGE

        if len(msg) == 2 and msg[1] == "connect":
            self.logger.info("Connecting to Discord...")
            channel.reply("Connecting to Discord...")
            self.connect_discord()
            return minqlx.RET_NONE

        if len(msg) == 2 and msg[1] == "disconnect":
            self.logger.info("Disconnecting from Discord...")
            channel.reply("Disconnecting from Discord...")
            self.disconnect_discord()
            return minqlx.RET_NONE

        if len(msg) == 2 and msg[1] == "reconnect":
            self.logger.info("Reconnecting to Discord...")
            channel.reply("Reconnecting to Discord...")
            self.disconnect_discord()
            self.connect_discord()
            return minqlx.RET_NONE

        channel.reply(self.discord.status())
        return minqlx.RET_NONE

    @minqlx.thread
    def connect_discord(self) -> None:
        if self.discord.is_discord_logged_in():
            return
        self.discord.run()

    @minqlx.thread
    def disconnect_discord(self) -> None:
        if not self.discord.is_discord_logged_in():
            return
        self.discord.stop()


class MinqlxHelpCommand(DefaultHelpCommand):
    """
    A help formatter for the minqlx plugin's bot to provide help information. This is a customized variation of
    discord.py's :class:`DefaultHelpCommand`.
    """
    def __init__(self):
        super().__init__(no_category="minqlx Commands")

    def get_ending_note(self) -> str:
        """
        Provides the ending_note for the help output.
        """
        return f"Type {self.context.prefix}{self.context.invoked_with} command for more info on a command."

    async def send_error_message(self, error: Exception) -> None:
        pass


class SimpleAsyncDiscord(threading.Thread):
    """
    SimpleAsyncDiscord client which is used to communicate to discord, and provides certain commands in the relay and
    triggered channels as well as private authentication to the bot to admin the server.
    """

    def __init__(self, version_information: str, logger: logging.Logger):
        """
        Constructor for the SimpleAsyncDiscord client the discord bot runs in.

        :param: version_information: the plugin's version_information string
        :param: logger: the logger used for logging, usually passed through from the minqlx plugin.
        """
        super().__init__()
        self.version_information: str = version_information
        self.logger: logging.Logger = logger
        self.discord: Optional[Bot] = None

        self.discord_bot_token: str = Plugin.get_cvar("qlx_discordBotToken")
        self.discord_relay_channel_ids: set[int] = \
            SimpleAsyncDiscord.int_set(Plugin.get_cvar("qlx_discordRelayChannelIds", set))
        self.discord_relay_team_chat_channel_ids: set[int] = SimpleAsyncDiscord.int_set(
            Plugin.get_cvar("qlx_discordRelayTeamchatChannelIds", set))
        self.discord_triggered_channel_ids: set[int] = SimpleAsyncDiscord.int_set(
            Plugin.get_cvar("qlx_discordTriggeredChannelIds", set))
        self.discord_triggered_channel_message_prefix: str = Plugin.get_cvar("qlx_discordTriggeredChatMessagePrefix")
        self.discord_trigger_triggered_channel_chat: str = Plugin.get_cvar("qlx_discordTriggerTriggeredChannelChat")
        self.discord_command_prefix: str = Plugin.get_cvar("qlx_discordCommandPrefix")
        self.discord_help_enabled: bool = Plugin.get_cvar("qlx_discordEnableHelp", bool)
        self.discord_version_enabled: bool = Plugin.get_cvar("qlx_discordEnableVersion", bool)
        self.discord_trigger_status: str = Plugin.get_cvar("qlx_discordTriggerStatus")
        self.discord_message_prefix: str = Plugin.get_cvar("qlx_discordMessagePrefix")
        self.discord_show_relay_channel_names: bool = Plugin.get_cvar("qlx_displayChannelForDiscordRelayChannels", bool)
        self.discord_replace_relayed_mentions: bool = \
            Plugin.get_cvar("qlx_discordReplaceMentionsForRelayedMessages", bool)
        self.discord_replace_triggered_mentions: bool = \
            Plugin.get_cvar("qlx_discordReplaceMentionsForTriggeredMessages", bool)

        extended_logging_enabled: bool = Plugin.get_cvar("qlx_discordLogToSeparateLogfile", bool)
        if extended_logging_enabled:
            self.setup_extended_logger()

    @staticmethod
    def setup_extended_logger() -> None:
        discord_logger: logging.Logger = logging.getLogger("discord")
        discord_logger.setLevel(logging.DEBUG)
        # File
        file_path = os.path.join(minqlx.get_cvar("fs_homepath"), "minqlx_discord.log")
        maxlogs: int = minqlx.Plugin.get_cvar("qlx_logs", int)
        maxlogsize: int = minqlx.Plugin.get_cvar("qlx_logsSize", int)
        file_fmt: logging.Formatter = \
            logging.Formatter("(%(asctime)s) [%(levelname)s @ %(name)s.%(funcName)s] %(message)s", "%H:%M:%S")
        file_handler: logging.FileHandler = \
            RotatingFileHandler(file_path, encoding="utf-8", maxBytes=maxlogsize, backupCount=maxlogs)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        discord_logger.addHandler(file_handler)
        # Console
        console_fmt: logging.Formatter = \
            logging.Formatter("[%(name)s.%(funcName)s] %(levelname)s: %(message)s", "%H:%M:%S")
        console_handler: logging.Handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_fmt)
        discord_logger.addHandler(console_handler)

    @staticmethod
    def int_set(string_set: set[str]) -> set[int]:
        int_set = set()

        for item in string_set:
            if item == '':
                continue
            value = int(item)
            int_set.add(value)

        return int_set

    def status(self) -> str:
        if self.discord is None:
            return "No discord connection set up."

        if self.is_discord_logged_in():
            return "Discord connection up and running."

        return "Discord client not connected."

    def run(self) -> None:
        """
        Called when the SimpleAsyncDiscord thread is started. We will set up the bot here with the right commands, and
        run the discord.py bot in a new event_loop until completed.
        """
        loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        members_intent: bool = self.discord_replace_relayed_mentions or self.discord_replace_triggered_mentions
        intents: discord.Intents = \
            discord.Intents(members=members_intent, guilds=True, bans=False, emojis=False, integrations=False,
                            webhooks=False, invites=False, voice_states=False, presences=True, messages=True,
                            guild_messages=True, dm_messages=True, reactions=False, guild_reactions=False,
                            dm_reactions=False, typing=False, guild_typing=False, dm_typing=False, message_content=True,
                            guild_scheduled_events=True)

        # init the bot, and init the main discord interactions
        if self.discord_help_enabled:
            self.discord = Bot(command_prefix=self.discord_command_prefix,
                               description=f"{self.version_information}",
                               help_command=MinqlxHelpCommand(), loop=loop, intents=intents)
        else:
            self.discord = Bot(command_prefix=self.discord_command_prefix,
                               description=f"{self.version_information}",
                               help_command=None, loop=loop, intents=intents)

        self.initialize_bot(self.discord)

        # connect the now configured bot to discord in the event_loop
        loop.run_until_complete(self.discord.start(self.discord_bot_token))

    def initialize_bot(self, discord_bot: discord.ext.commands.Bot) -> None:
        """
        initializes a discord bot with commands and listeners on this pseudo cog class

        :param: discord_bot: the discord_bot to initialize
        """
        discord_bot.add_command(Command(self.trigger_status, name=self.discord_trigger_status,
                                        checks=[self.is_message_in_relay_or_triggered_channel],
                                        pass_context=True,
                                        ignore_extra=False,
                                        help="display current game status information"))
        discord_bot.add_command(Command(self.triggered_chat, name=self.discord_trigger_triggered_channel_chat,
                                        checks=[self.is_message_in_triggered_channel],
                                        pass_context=True,
                                        help="send [message...] to the Quake Live server",
                                        require_var_positional=True))
        discord_bot.add_listener(self.on_ready)
        discord_bot.add_listener(self.on_message)

        if self.discord_version_enabled:
            discord_bot.add_command(Command(self.version, name="version",
                                            pass_context=True,
                                            ignore_extra=False,
                                            help="display the plugin's version information"))

    async def version(self, ctx: Context, *_args, **_kwargs) -> None:
        """
        Triggers the plugin's version information sent to discord

        :param: ctx: the context the trigger happened in
        """
        await ctx.send(f"```{self.version_information}```")

    def is_message_in_relay_or_triggered_channel(self, ctx: Context) -> bool:
        """
        Checks whether a message was either sent in a configured relay or triggered channel

        :param: ctx: the context the trigger happened in
        """
        return ctx.message.channel.id in self.discord_relay_channel_ids | self.discord_triggered_channel_ids

    async def trigger_status(self, ctx: Context, *_args, **_kwargs) -> None:
        """
        Triggers game status information sent towards the originating channel

        :param: ctx: the context the trigger happened in
        """
        try:
            game = minqlx.Game()

            ginfo = mydiscordbot.get_game_info(game)

            num_players = len(Plugin.players())
            max_players = game.maxclients

            maptitle = game.map_title if game.map_title else game.map
            gametype = game.type_short.upper()

            reply = f"{ginfo} on **{Plugin.clean_text(maptitle)}** ({gametype}) " \
                    f"with **{num_players}/{max_players}** players. {mydiscordbot.player_data()}"
        except minqlx.NonexistentGameError:
            reply = "Currently no game running."

        if self.is_message_in_triggered_channel(ctx):
            reply = f"{self.discord_triggered_channel_message_prefix} {reply}"

        await ctx.send(reply)

    def is_message_in_triggered_channel(self, ctx: Context) -> bool:
        """
        Checks whether the message originate in a configured triggered channel

        :param: ctx: the context the trigger happened in
        """
        return ctx.message.channel.id in self.discord_triggered_channel_ids

    async def triggered_chat(self, ctx: Context, *_args, **_kwargs) -> None:
        """
        Relays a message from the triggered channels to minqlx

        :param: ctx: the context the trigger happened in
        :param: _message: the message to send to minqlx
        """
        prefix_length = self.command_length(ctx)
        minqlx.CHAT_CHANNEL.reply(
            self._format_message_to_quake(ctx.message.channel,
                                          ctx.message.author,
                                          ctx.message.clean_content[prefix_length:]))

    @staticmethod
    def command_length(ctx: Context) -> int:
        return len(f"{ctx.prefix}{ctx.invoked_with} ")

    def _format_message_to_quake(self, channel: discord.TextChannel, author: discord.Member, content: str) -> str:
        """
        Format the channel, author, and content of a message so that it will be displayed nicely in the Quake Live
        console.

        :param: channel: the channel, the message came from.
        :param: author: the author of the original message.
        :param: content: the message itself, ideally taken from message.clean_content to avoid ids of mentioned users
        and channels on the discord server.
        :return: the formatted message that may be sent back to Quake Live.
        """
        sender = author.name
        if author.nick is not None:
            sender = author.nick

        if not self.discord_show_relay_channel_names and channel.id in self.discord_relay_channel_ids:
            return f"{self.discord_message_prefix} ^6{sender}^7:^2 {content}"
        return f"{self.discord_message_prefix} ^5#{channel.name} ^6{sender}^7:^2 {content}"

    async def on_ready(self) -> None:
        """
        Function called once the bot connected. Mainly displays status update from the bot in the game console
        and server logfile, and sets the bot to playing Quake Live on discord.
        """
        extensions = Plugin.get_cvar("qlx_discord_extensions", list)
        configured_extensions = []
        for extension in extensions:
            if len(extension.strip()) > 0:
                configured_extensions.append(
                    self.discord.load_extension(f".{extension}", package="minqlx-plugins.discord_extensions"))

        if len(configured_extensions) > 0:
            await asyncio.gather(*configured_extensions)

        self.logger.info(f"Logged in to discord as: {self.discord.user.name} ({self.discord.user.id})")
        Plugin.msg("Connected to discord")
        await self.discord.change_presence(activity=discord.Game(name="Quake Live"))

    async def on_message(self, message) -> None:
        """
        Function called once a message is sent through discord. Here the main interaction points either back to
        Quake Live or discord happen.
        :param: message: the message that was sent.
        """
        # guard clause to avoid None messages from processing.
        if not message:
            return

        # if the bot sent the message himself, do nothing.
        if message.author == self.discord.user:
            return

        # relay all messages from the relay channels back to Quake Live.
        if message.channel.id in self.discord_relay_channel_ids:
            content: str = message.clean_content
            if len(content) > 0:
                minqlx.CHAT_CHANNEL.reply(
                    self._format_message_to_quake(message.channel, message.author, content))

    async def on_command_error(self, exception: Exception, ctx: Context) -> None:
        """
        overrides the default command error handler so that no exception is produced for command errors

        Might be changed in the future to log those problems to the ´´`minqlx.logger```
        """

    def is_discord_logged_in(self) -> bool:
        if self.discord is None:
            return False

        return not self.discord.is_closed() and self.discord.is_ready()

    def stop(self) -> None:
        """
        stops the discord client
        """
        if self.discord is None:
            return

        asyncio.run_coroutine_threadsafe(self.discord.change_presence(
            status=discord.Status.offline), loop=self.discord.loop)
        asyncio.run_coroutine_threadsafe(self.discord.close(), loop=self.discord.loop)

    def relay_message(self, msg: str) -> None:
        """
        relay a message to the configured relay_channels

        :param: msg: the message to send to the relay channel
        """
        self.send_to_discord_channels(self.discord_relay_channel_ids, msg)

    def send_to_discord_channels(self, channel_ids: set[Union[str, int]], content: str) -> None:
        """
        Send a message to a set of channel_ids on discord provided.

        :param: channel_ids: the ids of the channels the message should be sent to.
        :param: content: the content of the message to send to the discord channels
        """
        if not self.is_discord_logged_in():
            return
        # if we were not provided any channel_ids, do nothing.
        if not channel_ids or len(channel_ids) == 0:
            return

        # send the message in its own thread to avoid blocking of the server
        for channel_id in channel_ids:
            channel = self.discord.get_channel(channel_id)

            if channel is None:
                continue

            asyncio.run_coroutine_threadsafe(
                channel.send(content,
                             allowed_mentions=AllowedMentions(everyone=False, users=True, roles=True)),
                loop=self.discord.loop)

    def relay_chat_message(self, player: minqlx.Player, channel: str, message: str) -> None:
        """
        relay a message to the given channel

        :param: player: the player that originally sent the message
        :param: channel: the channel the original message came through
        :param: message: the content of the message
        """
        if self.discord_replace_relayed_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        content = f"**{discord.utils.escape_markdown(player.clean_name)}**{channel}: " \
                  f"{discord.utils.escape_markdown(message)}"

        self.relay_message(content)

    def relay_team_chat_message(self, player: minqlx.Player, channel: str, message: str) -> None:
        """
        relay a team_chat message, that might be hidden to the given channel

        :param: player: the player that originally sent the message
        :param: channel: the channel the original message came through
        :param: message: the content of the message
        """
        if self.discord_replace_relayed_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        content = f"**{discord.utils.escape_markdown(player.clean_name)}**{channel}: " \
                  f"{discord.utils.escape_markdown(message)}"

        self.send_to_discord_channels(self.discord_relay_team_chat_channel_ids, content)

    def replace_user_mentions(self, message: str, player: minqlx.Player = None) -> str:
        """
        replaces a mentioned discord user (indicated by @user-hint with a real mention)

        :param: message: the message to replace the user mentions in
        :param: player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. No replacements for the ambiguous substitutions will happen.

        :return: the original message replaced by properly formatted user mentions
        """
        if not self.is_discord_logged_in():
            return message

        returned_message = message
        # this regular expression will make sure that the "@user" has at least three characters, and is either
        # prefixed by a space or at the beginning of the string
        matcher = re.compile("(?:^| )@([^ ]{3,})")

        member_list = list(self.discord.get_all_members())
        matches: list[re.Match] = matcher.findall(returned_message)

        for match in sorted(matches, key=lambda _match: len(str(_match)), reverse=True):
            if match in ["all", "everyone", "here"]:
                continue
            member = SimpleAsyncDiscord.find_user_that_matches(str(match), member_list, player)
            if member is not None:
                returned_message = returned_message.replace(f"@{match}", member.mention)

        return returned_message

    @staticmethod
    def find_user_that_matches(match: str, member_list: list[discord.Member], player: minqlx.Player = None) \
            -> Optional[discord.Member]:
        """
        find a user that matches the given match

        :param: match: the match to look for in the username and nick
        :param: member_list: the list of members connected to the discord server
        :param: player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. None is returned in that case.

        :return: the matching member, or None if none or more than one are found
        """
        # try a direct match for the whole name first
        member = [user for user in member_list if user.name.lower() == match.lower()]
        if len(member) == 1:
            return member[0]

        # then try a direct match at the user's nickname
        member = [user for user in member_list if user.nick is not None and user.nick.lower() == match.lower()]
        if len(member) == 1:
            return member[0]

        # if direct searches for the match fail, we try to match portions of the name or portions of the nick, if set
        member = [user for user in member_list
                  if user.name.lower().find(match.lower()) != -1 or
                  (user.nick is not None and user.nick.lower().find(match.lower()) != -1)]
        if len(member) == 1:
            return list(member)[0]

        # we found more than one matching member, let's tell the player about this.
        if len(member) > 1 and player is not None:
            player.tell(f"Found ^6{len(member)}^7 matching discord users for @{match}:")
            alternatives = ""
            for alternative_member in member:
                alternatives += f"@{alternative_member.name} "
            player.tell(alternatives)

        return None

    def replace_channel_mentions(self, message: str, player: minqlx.Player = None) -> str:
        """
        replaces a mentioned discord channel (indicated by #channel-hint with a real mention)

        :param: message: the message to replace the channel mentions in
        :param: player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. No replacements for the ambiguous substitutions will happen.

        :return: the original message replaced by properly formatted channel mentions
        """
        if not self.is_discord_logged_in():
            return message

        returned_message = message
        # this regular expression will make sure that the "#channel" has at least three characters, and is either
        # prefixed by a space or at the beginning of the string
        matcher = re.compile("(?:^| )#([^ ]{3,})")

        channel_list = [ch for ch in self.discord.get_all_channels()
                        if ch.type in [ChannelType.text, ChannelType.voice, ChannelType.group]]
        matches: list[re.Match] = matcher.findall(returned_message)

        for match in sorted(matches, key=lambda _match: len(str(_match)), reverse=True):
            channel = SimpleAsyncDiscord.find_channel_that_matches(str(match), channel_list, player)
            if channel is not None:
                returned_message = returned_message.replace(f"#{match}", channel.mention)

        return returned_message

    @staticmethod
    def find_channel_that_matches(match: str, channel_list: list[discord.TextChannel],
                                  player: minqlx.Player = None) -> Optional[discord.TextChannel]:
        """
        find a channel that matches the given match

        :param: match: the match to look for in the channel name
        :param: channel_list: the list of channels connected to the discord server
        :param: player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. None is returned in that case.

        :return: the matching channel, or None if none or more than one are found
        """
        # try a direct channel name match case-sensitive first
        channel = [ch for ch in channel_list if ch.name == match]
        if len(channel) == 1:
            return channel[0]

        # then try a case-insensitive direct match with the channel name
        channel = [ch for ch in channel_list if ch.name.lower() == match.lower()]
        if len(channel) == 1:
            return channel[0]

        # then we try a match with portions of the channel name
        channel = [ch for ch in channel_list if ch.name.lower().find(match.lower()) != -1]
        if len(channel) == 1:
            return channel[0]

        # we found more than one matching channel, let's tell the player about this.
        if len(channel) > 1 and player is not None:
            player.tell(f"Found ^6{len(channel)}^7 matching discord channels for #{match}:")
            alternatives = ""
            for alternative_channel in channel:
                alternatives += f"#{alternative_channel.name} "
            player.tell(alternatives)

        return None

    def triggered_message(self, player: minqlx.Player, message: str) -> None:
        """
        send a triggered message to the configured triggered_channel

        :param: player: the player that originally sent the message
        :param: message: the content of the message
        """
        if not self.discord_triggered_channel_ids:
            return

        if self.discord_replace_triggered_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        if self.discord_triggered_channel_message_prefix is not None and \
                self.discord_triggered_channel_message_prefix != "":
            content = f"{self.discord_triggered_channel_message_prefix} " \
                      f"**{discord.utils.escape_markdown(player.clean_name)}**: " \
                      f"{discord.utils.escape_markdown(message)}"
        else:
            content = f"**{discord.utils.escape_markdown(player.clean_name)}**: " \
                      f"{discord.utils.escape_markdown(message)}"

        self.send_to_discord_channels(self.discord_triggered_channel_ids, content)
