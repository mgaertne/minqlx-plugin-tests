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
import re
import asyncio
import threading

import logging
import os
from logging.handlers import RotatingFileHandler

import minqlx
from minqlx import Plugin

import discord
from discord import ChannelType, AllowedMentions
from discord.ext.commands import Bot, Command, DefaultHelpCommand
import discord.ext.tasks

plugin_version = "v1.5"


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
    * qlx_discordUpdateTopicOnTriggeredChannels (default: "1") Boolean flag to indicate whether to update the topic with
    the current game state on triggered relay channels. Your bot needs edit_channel permission for these channels.
    * qlx_discordKeepTopicSuffixChannelIds (default: "") Comma separated list of channel ids where the topic suffix
    will be kept upon updating.
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
    * qlx_discordQuakeRelayMessageFilters (default: "^\!s$, ^\!p$") comma separated list of regular expressions for
    messages that should not be sent from quake live to discord
    * qlx_discordReplaceMentionsForRelayedMessages (default: "1") replace mentions (@user and #channel) for messages
    sent towards relay channels
    * qlx_discordReplaceMentionsForTriggeredMessages (default: "1") replace mentions (@user and #channel) for triggered
    messages sent towards the triggered channels
    * qlx_discordAdminPassword (default "supersecret") passwort for remote admin of the server via discord private
    messages to the discord bot.
    * qlx_discordAuthCommand (default: "auth") command for authenticating a discord user to the plugin via private
    message
    * qlx_discordExecPrefix (default: "qlx") command for authenticated users to execute server commands from discord
    * qlx_discordLogToSeparateLogfile (default: "0") enables extended logging for the discord library (logs to
    minqlx_discord.log in the homepath)
    """

    def __init__(self, discord_client=None):
        super().__init__()

        # maybe initialize plugin cvars
        Plugin.set_cvar_once("qlx_discordBotToken", "")
        Plugin.set_cvar_once("qlx_discordRelayChannelIds", "")
        Plugin.set_cvar_once("qlx_discordRelayTeamchatChannelIds", "")
        Plugin.set_cvar_once("qlx_discordTriggeredChannelIds", "")
        Plugin.set_cvar_once("qlx_discordTriggeredChatMessagePrefix", "")
        Plugin.set_cvar_once("qlx_discordUpdateTopicOnTriggeredChannels", "1")
        Plugin.set_cvar_once("qlx_discordKeepTopicSuffixChannelIds", "")
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
        Plugin.set_cvar_once("qlx_discordAdminPassword", "supersecret")
        Plugin.set_cvar_once("qlx_discordAuthCommand", "auth")
        Plugin.set_cvar_once("qlx_discordExecPrefix", "qlx")
        Plugin.set_cvar_once("qlx_discordLogToSeparateLogfile", "0")

        # get the actual cvar values from the server
        self.discord_message_filters = Plugin.get_cvar("qlx_discordQuakeRelayMessageFilters", set)

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
        # Update topic on these hooks
        for hook in ["round_end", "game_start"]:
            self.add_hook(hook, self.update_topics, priority=minqlx.PRI_LOW)

        self.add_command("discord", self.cmd_discord, usage="<message>")
        self.add_command("discordbot", self.cmd_discordbot, permission=1,
                         usage="[status]|connect|disconnect|reconnect")

        # initialize the discord bot and its interactions on the discord server
        if discord_client is None:
            self.discord = SimpleAsyncDiscord(self.version_information(), self.logger)
        else:
            self.discord = discord_client
        self.logger.info("Connecting to Discord...")
        self.discord.start()
        self.logger.info(self.version_information())
        Plugin.msg(self.version_information())

    def version_information(self):
        return "{} Version: {}".format(self.name, plugin_version)

    def handle_plugin_unload(self, plugin):
        """
        Handler when a plugin is unloaded to make sure, that the connection to discord is properly closed when this
        plugin is unloaded.

        :param plugin: the plugin that was unloaded.
        """
        if plugin == self.__class__.__name__:
            self.discord.stop()

    def update_topics(self, *args, **kwargs):
        """
        Update the current topic on the general relay channels, and the triggered relay channels. The latter will only
        happen when cvar qlx_discordUpdateTopicOnIdleChannels is set to "1".
        """
        self.discord.update_topics()

    @staticmethod
    def game_status_information(game: minqlx.Game):
        """
        Generate the text for the topic set on discord channels.

        :param game: the game to derive the status information from

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
        return "{0} on **{1}** ({2}) with **{3}/{4}** players. ".format(ginfo,
                                                                        Plugin.clean_text(maptitle),
                                                                        gametype,
                                                                        num_players,
                                                                        max_players)

    @staticmethod
    def get_game_info(game):
        """
        Helper to format the current game.state that may be used in status messages and setting of channel topics.

        :param game: the game object to derive the information from

        :return: the current text representation of the game state
        """
        if game.state == "warmup":
            return "Warmup"
        if game.state == "countdown":
            return "Match starting"
        if game.roundlimit in [game.blue_score, game.red_score] or game.red_score < 0 or game.blue_score < 0:
            return "Match ended: **{}** - **{}**".format(game.red_score, game.blue_score)
        if game.state == "in_progress":
            return "Match in progress: **{}** - **{}**".format(game.red_score, game.blue_score)

        return "Warmup"

    @staticmethod
    def player_data():
        """
        Formats the top 5 scorers connected to the server in a string. The return value may be used for status messages
        and used in topics to indicate reveal more data about the server and its current game.

        :return: string of the current top5 scorers with the scores and connection time to the server
        """
        player_data = ""
        teams = Plugin.teams()
        if len(teams['red']) > 0:
            player_data += "\n**R:** {}".format(mydiscordbot.team_data(teams['red']))
        if len(teams['blue']) > 0:
            player_data += "\n**B:** {}".format(mydiscordbot.team_data(teams['blue']))

        return player_data

    @staticmethod
    def team_data(player_list, limit=None):
        """
        generates a sorted output of the team's player by their score

        :param player_list: the list of players to generate the team output for
        :param limit: (default: None) just list the top players up to the given limit
        :return: a discord ready text representation of the player's of that team by their score
        """
        if len(player_list) == 0:
            return ""

        players_by_score = sorted(player_list, key=lambda k: k.score, reverse=True)
        if limit:
            players_by_score = players_by_score[:limit]

        team_data = ""
        for player in players_by_score:
            team_data += "**{}**({}) ".format(mydiscordbot.escape_text_for_discord(player.clean_name), player.score)

        return team_data

    def is_filtered_message(self, msg):
        """
        Checks whether the given message should be filtered and not be sent to discord.

        :param msg: the message to check whether it should be filtered
        :return whether the message should not be relayed to discord
        """
        for message_filter in self.discord_message_filters:
            matcher = re.compile(message_filter)
            if matcher.match(msg):
                return True

        return False

    def handle_ql_chat(self, player: minqlx.Player, msg, channel: minqlx.AbstractChannel):
        """
        Handler function for all chat messages on the server. This function will forward and messages on the Quake Live
        server to discord.

        :param player: the player that sent the message
        :param msg: the message that was sent
        :param channel: the chnannel the message was sent to
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
    def handle_player_connect(self, player: minqlx.Player):
        """
        Handler called when a player connects. The method sends a corresponding message to the discord relay channels,
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        """
        content = "_{} connected._".format(mydiscordbot.escape_text_for_discord(player.clean_name))
        self.discord.relay_message(content)

        self.discord.update_topics()

    @staticmethod
    def escape_text_for_discord(text):
        """
        Escapes the provided player's name for proper formatting to discord (i.e. replace '*' (asterisks) with a
        variant to not interfere with discord's formattings.)

        :param text: the text that shall be escaped for discord chat channels
        """
        escaped_text = text.replace('_', r'\_')
        escaped_text = escaped_text.replace('*', r"\*")
        return escaped_text

    @minqlx.delay(3)
    def handle_player_disconnect(self, player: minqlx.Player, reason):
        """
        Handler called when a player disconnects. The method sends a corresponding message to the discord relay
        channels, and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        :param reason: the reason why the player left
        """
        if reason in ["disconnected", "timed out", "was kicked", "was kicked."]:
            reason_str = "{}.".format(reason)
        else:
            reason_str = "was kicked ({}).".format(mydiscordbot.escape_text_for_discord(Plugin.clean_text(reason)))
        content = "_{} {}_".format(mydiscordbot.escape_text_for_discord(player.clean_name),
                                   reason_str)
        self.discord.relay_message(content)

        self.discord.update_topics()

    def handle_map(self, mapname, factory):
        """
        Handler called when a map is changed. The method sends a corresponding message to the discord relay channels.
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param mapname: the new map
        :param factory: the map factory used
        """
        content = "*Changing map to {}...*".format(mydiscordbot.escape_text_for_discord(mapname))
        self.discord.relay_message(content)

        self.discord.update_topics()

    def handle_vote_started(self, caller, vote, args):
        """
        Handler called when a vote was started. The method sends a corresponding message to the discord relay channels.

        :param caller: the player that initiated the vote
        :param vote: the vote itself, i.e. map change, kick player, etc.
        :param args: any arguments of the vote, i.e. map name, which player to kick, etc.
        """
        caller_name = mydiscordbot.escape_text_for_discord(caller.clean_name) if caller else "The server"
        content = "_{} called a vote: {} {}_".format(caller_name,
                                                     vote,
                                                     mydiscordbot.escape_text_for_discord(Plugin.clean_text(args)))

        self.discord.relay_message(content)

    def handle_vote_ended(self, votes, vote, args, passed):
        """
        Handler called when a vote was passed or failed. The method sends a corresponding message to the discord relay
        channels.

        :param votes: the final votes
        :param vote: the initial vote that passed or failed, i.e. map change, kick player, etc.
        :param args: any arguments of the vote, i.e. map name, which player to kick, etc.
        :param passed: boolean indicating whether the vote passed
        """
        if passed:
            content = "*Vote passed ({} - {}).*".format(*votes)
        else:
            content = "*Vote failed.*"

        self.discord.relay_message(content)

    @minqlx.delay(1)
    def handle_game_countdown_or_end(self, *args, **kwargs):
        """
        Handler called when the game is in countdown, i.e. about to start. This function mainly updates the topics of
        the relay channels and the triggered channels (when configured), and sends a message to all relay channels.
        """
        game = self.game
        if game is None:
            return
        topic = mydiscordbot.game_status_information(game)
        top5_players = mydiscordbot.player_data()

        self.discord.relay_message("{}{}".format(topic, top5_players))

        self.discord.update_topics_on_relay_and_triggered_channels(topic)

    def cmd_discord(self, player: minqlx.Player, msg, channel):
        """
        Handler of the !discord command. Forwards any messages after !discord to the discord triggered relay channels.

        :param player: the player that send to the trigger
        :param msg: the message the player sent (includes the trigger)
        :param channel: the channel the message came through, i.e. team chat, general chat, etc.
        """
        # when the message did not include anything to forward, show the usage help text.
        if len(msg) < 2:
            return minqlx.RET_USAGE

        self.discord.triggered_message(player, Plugin.clean_text(" ".join(msg[1:])))
        self.msg("Message to Discord chat cast!")

    def cmd_discordbot(self, player: minqlx.Player, msg, channel):
        """
        Handler for reconnecting the discord bot to discord in case it gets disconnected.

        :param player: the player that send to the trigger
        :param msg: the original message the player sent (includes the trigger)
        :param channel: the channel the message came through, i.e. team chat, general chat, etc.
        """
        if len(msg) > 2 or (len(msg) == 2 and msg[1] not in ["status", "connect", "disconnect", "reconnect"]):
            return minqlx.RET_USAGE

        if len(msg) == 2 and msg[1] == "connect":
            self.logger.info("Connecting to Discord...")
            channel.reply("Connecting to Discord...")
            self.connect_discord()
            return

        if len(msg) == 2 and msg[1] == "disconnect":
            self.logger.info("Disconnecting from Discord...")
            channel.reply("Disconnecting from Discord...")
            self.disconnect_discord()
            return

        if len(msg) == 2 and msg[1] == "reconnect":
            self.logger.info("Reconnecting to Discord...")
            channel.reply("Reconnecting to Discord...")
            self.disconnect_discord()
            self.connect_discord()
            return

        channel.reply(self.discord.status())
        return

    @minqlx.thread
    def connect_discord(self):
        if self.discord.is_discord_logged_in():
            return
        self.discord.run()

    @minqlx.thread
    def disconnect_discord(self):
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

    def get_ending_note(self):
        """
        Provides the ending_note for the help output.
        """
        command_name = self.context.invoked_with
        return "Type {0}{1} command for more info on a command.".format(self.clean_prefix, command_name)

    async def send_error_message(self, error):
        pass


class DiscordChannel(minqlx.AbstractChannel):
    """
    a minqlx channel class to respond to from within minqlx for interactions with discord
    """
    def __init__(self, client, author, discord_channel):
        super().__init__("discord")
        self.client = client
        self.author = author
        self.discord_channel = discord_channel

    def __repr__(self):
        return "{} {}".format(str(self), self.author.display_name)

    def reply(self, msg):
        """
        overwrites the channel.reply function to relay messages to discord

        :param msg: the message to send to this channel
        """
        self.client.send_to_discord_channels({self.discord_channel.id}, Plugin.clean_text(msg))


class DiscordDummyPlayer(minqlx.AbstractDummyPlayer):
    """
    a minqlx dummy player class to relay messages to discord
    """
    def __init__(self, client, author, discord_channel):
        self.client = client
        self.author = author
        self.discord_channel = discord_channel
        super().__init__(name="Discord-{}".format(author.display_name))

    @property
    def steam_id(self):
        return minqlx.owner()

    @property
    def channel(self):
        return DiscordChannel(self.client, self.author, self.discord_channel)

    def tell(self, msg):
        """
        overwrites the player.tell function to relay messages to discord

        :param msg: the msg to send to this player
        """
        self.client.send_to_discord_channels({self.discord_channel.id}, Plugin.clean_text(msg))


class SimpleAsyncDiscord(threading.Thread):
    """
    SimpleAsyncDiscord client which is used to communicate to discord, and provides certain commands in the relay and
    triggered channels as well as private authentication to the bot to admin the server.
    """

    def __init__(self, version_information, logger):
        """
        Constructor for the SimpleAsyncDiscord client the discord bot runs in.

        :param version_information: the plugin's version_information string
        :param logger: the logger used for logging, usually passed through from the minqlx plugin.
        """
        super().__init__()
        self.version_information = version_information
        self.logger = logger
        self.discord = None

        self.authed_discord_ids = set()
        self.auth_attempts = {}

        self.discord_bot_token = Plugin.get_cvar("qlx_discordBotToken")
        self.discord_relay_channel_ids = SimpleAsyncDiscord.int_set(Plugin.get_cvar("qlx_discordRelayChannelIds", set))
        self.discord_relay_team_chat_channel_ids = SimpleAsyncDiscord.int_set(
            Plugin.get_cvar("qlx_discordRelayTeamchatChannelIds", set))
        self.discord_triggered_channel_ids = SimpleAsyncDiscord.int_set(
            Plugin.get_cvar("qlx_discordTriggeredChannelIds", set))
        self.discord_triggered_channel_message_prefix = Plugin.get_cvar("qlx_discordTriggeredChatMessagePrefix")
        self.discord_update_triggered_channels_topic = \
            Plugin.get_cvar("qlx_discordUpdateTopicOnTriggeredChannels", bool)
        self.discord_keep_topic_suffix_channel_ids = SimpleAsyncDiscord.int_set(
            Plugin.get_cvar("qlx_discordKeepTopicSuffixChannelIds", set))
        self.discord_trigger_triggered_channel_chat = Plugin.get_cvar("qlx_discordTriggerTriggeredChannelChat")
        self.discord_command_prefix = Plugin.get_cvar("qlx_discordCommandPrefix")
        self.discord_help_enabled = Plugin.get_cvar("qlx_discordEnableHelp", bool)
        self.discord_version_enabled = Plugin.get_cvar("qlx_discordEnableVersion", bool)
        self.discord_trigger_status = Plugin.get_cvar("qlx_discordTriggerStatus")
        self.discord_message_prefix = Plugin.get_cvar("qlx_discordMessagePrefix")
        self.discord_show_relay_channel_names = Plugin.get_cvar("qlx_displayChannelForDiscordRelayChannels", bool)
        self.discord_replace_relayed_mentions = Plugin.get_cvar("qlx_discordReplaceMentionsForRelayedMessages", bool)
        self.discord_replace_triggered_mentions = \
            Plugin.get_cvar("qlx_discordReplaceMentionsForTriggeredMessages", bool)
        self.discord_admin_password = Plugin.get_cvar("qlx_discordAdminPassword")
        self.discord_auth_command = Plugin.get_cvar("qlx_discordAuthCommand")
        self.discord_exec_prefix = Plugin.get_cvar("qlx_discordExecPrefix")

        extended_logging_enabled = Plugin.get_cvar("qlx_discordLogToSeparateLogfile", bool)
        if extended_logging_enabled:
            self.setup_extended_logger()

    def setup_extended_logger(self):
        discordLogger = logging.getLogger("discord")
        discordLogger.setLevel(logging.DEBUG)
        # File
        file_path = os.path.join(minqlx.get_cvar("fs_homepath"), "minqlx_discord.log")
        maxlogs = minqlx.Plugin.get_cvar("qlx_logs", int)
        maxlogsize = minqlx.Plugin.get_cvar("qlx_logsSize", int)
        file_fmt = logging.Formatter("(%(asctime)s) [%(levelname)s @ %(name)s.%(funcName)s] %(message)s", "%H:%M:%S")
        file_handler = RotatingFileHandler(file_path, encoding="utf-8", maxBytes=maxlogsize, backupCount=maxlogs)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        discordLogger.addHandler(file_handler)
        # Console
        console_fmt = logging.Formatter("[%(name)s.%(funcName)s] %(levelname)s: %(message)s", "%H:%M:%S")
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_fmt)
        discordLogger.addHandler(console_handler)

    @staticmethod
    def int_set(string_set):
        int_set = set()

        for item in string_set:
            if item == '':
                continue
            value = int(item)
            int_set.add(value)

        return int_set

    def status(self):
        if self.discord is None:
            return "No discord connection set up."

        if self.is_discord_logged_in():
            return "Discord connection up and running."

        return "Discord client not connected."

    def run(self):
        """
        Called when the SimpleAsyncDiscord thread is started. We will set up the bot here with the right commands, and
        run the discord.py bot in a new event_loop until completed.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        members_intent = self.discord_replace_relayed_mentions or self.discord_replace_triggered_mentions
        intents = discord.Intents(members=members_intent, guilds=True, bans=False, emojis=False, integrations=False,
                                  webhooks=False, invites=False, voice_states=False, presences=False, messages=True,
                                  guild_messages=True, dm_messages=True, reactions=False, guild_reactions=False,
                                  dm_reactions=False, typing=False, guild_typing=False, dm_typing=False)

        # init the bot, and init the main discord interactions
        if self.discord_help_enabled:
            self.discord = Bot(command_prefix=self.discord_command_prefix,
                               description="{}".format(self.version_information),
                               help_command=MinqlxHelpCommand(), loop=loop, intents=intents)
        else:
            self.discord = Bot(command_prefix=self.discord_command_prefix,
                               description="{}".format(self.version_information),
                               help_command=None, loop=loop, intents=intents)
        self.initialize_bot(self.discord)

        # connect the now configured bot to discord in the event_loop
        self.discord.loop.run_until_complete(self.discord.start(self.discord_bot_token))

    def initialize_bot(self, discord_bot):
        """
        initializes a discord bot with commands and listeners on this pseudo cog class

        :param discord_bot: the discord_bot to initialize
        """
        discord_bot.add_command(Command(self.auth, name=self.discord_auth_command,
                                        checks=[self.is_private_message, lambda ctx: not self.is_authed(ctx),
                                                lambda ctx: not self.is_barred_from_auth(ctx)],
                                        hidden=True,
                                        pass_context=True,
                                        help="auth with the bot"))
        discord_bot.add_command(Command(self.qlx, name=self.discord_exec_prefix,
                                        checks=[self.is_private_message, self.is_authed],
                                        hidden=True,
                                        pass_context=True,
                                        help="execute minqlx commands on the server"))
        discord_bot.add_command(Command(self.trigger_status, name=self.discord_trigger_status,
                                        checks=[self.is_message_in_relay_or_triggered_channel],
                                        pass_context=True,
                                        ignore_extra=False,
                                        help="display current game status information"))
        discord_bot.add_command(Command(self.triggered_chat, name=self.discord_trigger_triggered_channel_chat,
                                        checks=[self.is_message_in_triggered_channel],
                                        pass_context=True,
                                        help="send [message...] to the Quake Live server"))
        discord_bot.add_listener(self.on_ready)
        discord_bot.add_listener(self.on_message)

        if self.discord_version_enabled:
            discord_bot.add_command(Command(self.version, name="version",
                                            pass_context=True,
                                            ignore_extra=False,
                                            help="display the plugin's version information"))

    def reply_to_context(self, ctx, message):
        return ctx.send(message)

    async def version(self, ctx):
        """
        Triggers the plugin's version information sent to discord

        :param ctx: the context the trigger happened in
        """
        await self.reply_to_context(ctx, "```{}```".format(self.version_information))

    def is_private_message(self, ctx):
        """
        Checks whether a message was sent on a private chat to the bot

        :param ctx: the context the trigger happened in
        """
        return isinstance(ctx.message.channel, discord.DMChannel)

    def is_authed(self, ctx):
        """
        Checks whether a user is authed to the bot

        :param ctx: the context the trigger happened in
        """
        return ctx.message.author.id in self.authed_discord_ids

    def is_barred_from_auth(self, ctx):
        """
        Checks whether an author is currently barred from authentication to the bot

        :param ctx: the context the trigger happened in
        """
        return ctx.message.author.id in self.auth_attempts and self.auth_attempts[ctx.message.author.id] <= 0

    async def auth(self, ctx, password: str):
        """
        Handles the authentication to the bot via private message

        :param ctx: the context of the original message sent for authentication
        :param password: the password to authenticate
        """
        if password == self.discord_admin_password:
            self.authed_discord_ids.add(ctx.message.author.id)
            await self.reply_to_context(ctx, "You have been successfully authenticated. "
                                             "You can now use {}{} to execute commands."
                                        .format(self.discord_command_prefix, self.discord_exec_prefix))
            return
        # Allow up to 3 attempts for the user's discord id to authenticate.
        if ctx.message.author.id not in self.auth_attempts:
            self.auth_attempts[ctx.message.author.id] = 3
        self.auth_attempts[ctx.message.author.id] -= 1
        if self.auth_attempts[ctx.message.author.id] > 0:
            await self.reply_to_context(ctx, "Wrong password. You have {} attempts left."
                                        .format(self.auth_attempts[ctx.message.author.id]))
            return

        # User has reached maximum auth attempts, we will bar her/him from authentication for 5 minutes (300 seconds)
        bar_delay = 300
        await self.reply_to_context(ctx,
                                    "Maximum authentication attempts reached. "
                                    "You will be barred from authentication for {} seconds."
                                    .format(bar_delay))

        def f():
            del self.auth_attempts[ctx.message.author.id]

        threading.Timer(bar_delay, f).start()

    async def qlx(self, ctx, *qlx_command: str):
        """
        Handles exec messages from discord via private message to the bot

        :param ctx: the context the trigger happened in
        :param qlx_command: the command that was sent by the user
        """
        @minqlx.next_frame
        def f():
            try:
                minqlx.COMMANDS.handle_input(
                    DiscordDummyPlayer(self, ctx.message.author, ctx.message.channel),
                    " ".join(qlx_command),
                    DiscordChannel(self, ctx.message.author, ctx.message.channel))
            except Exception as e:
                send_message = ctx.send("{}: {}".format(e.__class__.__name__, e))
                asyncio.run_coroutine_threadsafe(send_message, loop=ctx.bot.loop)
                minqlx.log_exception()

        f()

    def is_message_in_relay_or_triggered_channel(self, ctx):
        """
        Checks whether a message was either sent in a configured relay or triggered channel

        :param ctx: the context the trigger happened in
        """
        return ctx.message.channel.id in self.discord_relay_channel_ids | self.discord_triggered_channel_ids

    async def trigger_status(self, ctx):
        """
        Triggers game status information sent towards the originating channel

        :param ctx: the context the trigger happened in
        """
        try:
            game = minqlx.Game()
            reply = "{}{}".format(
                mydiscordbot.game_status_information(game),
                mydiscordbot.player_data())
        except minqlx.NonexistentGameError:
            reply = "Currently no game running."

        await self.reply_to_context(ctx, reply)

    def is_message_in_triggered_channel(self, ctx):
        """
        Checks whether the message originate in a configured triggered channel

        :param ctx: the context the trigger happened in
        """
        return ctx.message.channel.id in self.discord_triggered_channel_ids

    async def triggered_chat(self, ctx, *message: str):
        """
        Relays a message from the triggered channels to minqlx

        :param ctx: the context the trigger happened in
        :param message: the message to send to minqlx
        """
        prefix_length = len("{}{} ".format(ctx.prefix, ctx.invoked_with))
        minqlx.CHAT_CHANNEL.reply(
            self._format_message_to_quake(ctx.message.channel,
                                          ctx.message.author,
                                          ctx.message.clean_content[prefix_length:]))

    def _format_message_to_quake(self, channel, author, content):
        """
        Format the channel, author, and content of a message so that it will be displayed nicely in the Quake Live
        console.

        :param channel: the channel, the message came from.
        :param author: the author of the original message.
        :param content: the message itself, ideally taken from message.clean_content to avoid ids of mentioned users
        and channels on the discord server.
        :return: the formatted message that may be sent back to Quake Live.
        """
        sender = author.name
        if author.nick is not None:
            sender = author.nick

        if not self.discord_show_relay_channel_names and channel.id in self.discord_relay_channel_ids:
            return "{0} ^6{1}^7:^2 {2}".format(self.discord_message_prefix, sender, content)
        return "{0} ^5#{1.name} ^6{2}^7:^2 {3}".format(self.discord_message_prefix, channel, sender, content)

    async def on_ready(self):
        """
        Function called once the bot connected. Mainly displays status update from the bot in the game console
        and server logfile, and sets the bot to playing Quake Live on discord.
        """
        self.logger.info("Logged in to discord as: {} ({})".format(self.discord.user.name, self.discord.user.id))
        Plugin.msg("Connected to discord")
        await self.discord.change_presence(activity=discord.Game(name="Quake Live"))
        self.update_topics()

    async def on_message(self, message):
        """
        Function called once a message is send through discord. Here the main interaction points either back to
        Quake Live or discord happen.
        :param message: the message that was sent.
        """
        # guard clause to avoid None messages from processing.
        if not message:
            return

        # if the bot sent the message himself, do nothing.
        if message.author == self.discord.user:
            return

        # relay all messages from the relay channels back to Quake Live.
        if message.channel.id in self.discord_relay_channel_ids:
            content = message.clean_content
            if len(content) > 0:
                minqlx.CHAT_CHANNEL.reply(
                    self._format_message_to_quake(message.channel, message.author, content))

    async def on_command_error(self, exception, ctx):
        """
        overrides the default command error handler so that no exception is produced for command errors

        Might be changed in the future to log those problems to the minqlx.logger
        """
        pass

    def update_topics(self):
        """
        Update the current topic on the general relay channels, and the triggered relay channels. The latter will only
        happen when cvar qlx_discordUpdateTopicOnIdleChannels is set to "1".
        """
        try:
            game = minqlx.Game()
        except minqlx.NonexistentGameError:
            return
        topic = mydiscordbot.game_status_information(game)
        self.update_topics_on_relay_and_triggered_channels(topic)

    def update_topics_on_relay_and_triggered_channels(self, topic):
        """
        Helper function to update the topics on all the relay and all the triggered channels

        :param topic: the topic to set on all the channels
        """
        if not self.is_discord_logged_in():
            return

        if self.discord_update_triggered_channels_topic:
            topic_channel_ids = self.discord_relay_channel_ids | self.discord_triggered_channel_ids
        else:
            topic_channel_ids = self.discord_relay_channel_ids

        # directly set the topic on channels with no topic suffix
        self.set_topic_on_discord_channels(topic_channel_ids - self.discord_keep_topic_suffix_channel_ids, topic)
        # keep the topic suffix on the channels that are configured accordingly
        self.update_topic_on_channels_and_keep_channel_suffix(
            topic_channel_ids & self.discord_keep_topic_suffix_channel_ids, topic)

    def set_topic_on_discord_channels(self, channel_ids, topic):
        """
        Set the topic on a set of channel_ids on discord provided.

        :param channel_ids: the ids of the channels the topic should be set upon.
        :param topic: the new topic that should be set.
        """
        # if we were not provided any channel_ids, do nothing.
        if not channel_ids or len(channel_ids) == 0:
            return

        # set the topic in its own thread to avoid blocking of the server
        for channel_id in channel_ids:
            channel = self.discord.get_channel(channel_id)

            if channel is None:
                continue

            asyncio.run_coroutine_threadsafe(channel.edit(topic=topic), loop=self.discord.loop)

    def is_discord_logged_in(self):
        if self.discord is None:
            return False

        return not self.discord.is_closed() and self.discord.is_ready()

    def update_topic_on_channels_and_keep_channel_suffix(self, channel_ids, topic):
        """
        Updates the topic on the given channels and keeps the topic suffix intact on the configured channels

        :param channel_ids: the set of channels to update the topic on
        :param topic: the topic to set on the given channels
        """
        # if there are not triggered relay channels configured, do nothing.
        if not channel_ids or len(channel_ids) == 0:
            return

        # take the final 10 characters from the topic, and search for it in the current topic
        topic_ending = topic[-10:]

        for channel_id in channel_ids:
            previous_topic = self.get_channel_topic(channel_id)

            if previous_topic is None:
                previous_topic = topic

            # preserve the original channel's topic.
            position = previous_topic.find(topic_ending)
            topic_suffix = previous_topic[position + len(topic_ending):] if position != -1 else previous_topic

            # update the topic on the triggered channels
            self.set_topic_on_discord_channels({channel_id}, "{}{}".format(topic, topic_suffix))

    def get_channel_topic(self, channel_id):
        """
        get the topic of the provided channel id

        :param channel_id: the id of the channel to get the topic from

        :return: the topic of the channel
        """
        channel = self.discord.get_channel(channel_id)

        if channel is None:
            return None

        return channel.topic

    def stop(self):
        """
        stops the discord client
        """
        if self.discord is None:
            return

        asyncio.run_coroutine_threadsafe(self.discord.change_presence(status="offline"), loop=self.discord.loop)
        asyncio.run_coroutine_threadsafe(self.discord.logout(), loop=self.discord.loop)

    def relay_message(self, msg):
        """
        relay a message to the configured relay_channels

        :param msg: the message to send to the relay channel
        """
        self.send_to_discord_channels(self.discord_relay_channel_ids, msg)

    def send_to_discord_channels(self, channel_ids, content):
        """
        Send a message to a set of channel_ids on discord provided.

        :param channel_ids: the ids of the channels the message should be sent to.
        :param content: the content of the message to send to the discord channels
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

            asyncio.run_coroutine_threadsafe(channel.send(content,
                                                          allowed_mentions=AllowedMentions(everyone=False,
                                                                                           users=True,
                                                                                           roles=True)),
                                             loop=self.discord.loop)

    def relay_chat_message(self, player, channel, message):
        """
        relay a message to the given channel

        :param player: the player that originally sent the message
        :param channel: the channel the original message came through
        :param message: the content of the message
        """
        if self.discord_replace_relayed_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        content = "**{}**{}: {}".format(mydiscordbot.escape_text_for_discord(player.clean_name), channel, message)

        self.relay_message(content)

    def relay_team_chat_message(self, player, channel, message):
        """
        relay a team_chat message, that might be hidden to the given channel

        :param player: the player that originally sent the message
        :param channel: the channel the original message came through
        :param message: the content of the message
        """
        if self.discord_replace_relayed_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        content = "**{}**{}: {}".format(mydiscordbot.escape_text_for_discord(player.clean_name), channel, message)

        self.send_to_discord_channels(self.discord_relay_team_chat_channel_ids, content)

    def replace_user_mentions(self, message, player=None):
        """
        replaces a mentioned discord user (indicated by @user-hint with a real mention

        :param message: the message to replace the user mentions in
        :param player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. No replacements for the ambiguous substitutions will happen.

        :return: the original message replaced by properly formatted user mentions
        """
        if not self.is_discord_logged_in():
            return message

        returned_message = message
        # this regular expression will make sure that the "@user" has at least three characters, and is either
        # prefixed by a space or at the beginning of the string
        matcher = re.compile("(?:^| )@([^ ]{3,})")

        member_list = [user for user in self.discord.get_all_members()]
        matches = matcher.findall(returned_message)

        for match in sorted(matches, key=lambda user_match: len(user_match), reverse=True):
            if match in ["all", "everyone", "here"]:
                continue
            member = SimpleAsyncDiscord.find_user_that_matches(match, member_list, player)
            if member is not None:
                returned_message = returned_message.replace("@{}".format(match), member.mention)

        return returned_message

    @staticmethod
    def find_user_that_matches(match, member_list, player=None):
        """
        find a user that matches the given match

        :param match: the match to look for in the user name and nick
        :param member_list: the list of members connected to the discord server
        :param player: (default: None) when several alternatives are found for the mentions used, this player is told
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
        member = [user for user in member_list if user.name.lower().find(match.lower()) != -1 or
                  (user.nick is not None and user.nick.lower().find(match.lower()) != -1)]
        if len(member) == 1:
            return list(member)[0]

        # we found more than one matching member, let's tell the player about this.
        if len(member) > 1 and player is not None:
            player.tell("Found ^6{}^7 matching discord users for @{}:".format(len(member), match))
            alternatives = ""
            for alternative_member in member:
                alternatives += "@{} ".format(alternative_member.name)
            player.tell(alternatives)

        return None

    def replace_channel_mentions(self, message, player=None):
        """
        replaces a mentioned discord channel (indicated by #channel-hint with a real mention

        :param message: the message to replace the channel mentions in
        :param player: (default: None) when several alternatives are found for the mentions used, this player is told
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
        matches = matcher.findall(returned_message)

        for match in sorted(matches, key=lambda channel_match: len(channel_match), reverse=True):
            channel = SimpleAsyncDiscord.find_channel_that_matches(match, channel_list, player)
            if channel is not None:
                returned_message = returned_message.replace("#{}".format(match), channel.mention)

        return returned_message

    @staticmethod
    def find_channel_that_matches(match, channel_list, player=None):
        """
        find a channel that matches the given match

        :param match: the match to look for in the channel name
        :param channel_list: the list of channels connected to the discord server
        :param player: (default: None) when several alternatives are found for the mentions used, this player is told
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
            player.tell("Found ^6{}^7 matching discord channels for #{}:".format(len(channel), match))
            alternatives = ""
            for alternative_channel in channel:
                alternatives += "#{} ".format(alternative_channel.name)
            player.tell(alternatives)

        return None

    def triggered_message(self, player, message):
        """
        send a triggered message to the configured triggered_channel

        :param player: the player that originally sent the message
        :param message: the content of the message
        """
        if not self.discord_triggered_channel_ids:
            return

        if self.discord_replace_triggered_mentions:
            message = self.replace_user_mentions(message, player)
            message = self.replace_channel_mentions(message, player)

        if self.discord_triggered_channel_message_prefix is not None and \
                self.discord_triggered_channel_message_prefix != "":
            content = "{} **{}**: {}".format(self.discord_triggered_channel_message_prefix,
                                             mydiscordbot.escape_text_for_discord(player.clean_name), message)
        else:
            content = "**{}**: {}".format(mydiscordbot.escape_text_for_discord(player.clean_name), message)

        self.send_to_discord_channels(self.discord_triggered_channel_ids, content)
