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
import requests
import json
import threading

import minqlx
from minqlx import Plugin

import discord
from discord import ChannelType
from discord.ext import commands

plugin_version = "v1.0.0-theta"


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

    Uses:
    * qlx_discordBotToken (default: "") The token of the discord bot to use to connect to discord.
    * qlx_discordRelayChannelIds (default: "") Comma separated list of channels for full relay.
    * qlx_discordTriggeredChannelIds (default: "") Comma separated list of channels for triggered relay.
    * qlx_discordUpdateTopicOnTriggeredChannels (default: "1") Boolean flag to indicate whether to update the topic with
    the current game state on triggered relay channels. Your bot needs edit_channel permission for these channels.
    * qlx_discordTriggerTriggeredChannelChat (default: "!quakelive") Message prefix for the trigger on triggered relay
    channels.
    * qlx_discordKeepTopicSuffixChannelIds (default: "") Comma separated list of channel ids where the topic suffix
    will be kept upon updating.
    * qlx_discordTriggerStatus (default: "!status") Trigger for having the bot send the current status of the game
    server.
    * qlx_discordMessagePrefix (default: "[DISCORD]") messages from discord to quake live will be prefixed with this
    prefix
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
    * qlx_discordAuthCommand (default: ".auth") command for authenticating a discord user to the plugin via private
    message
    * qlx_discordExecPrefix (default: ".qlx") command for authenticated users to execute server commands from discord
    """

    def __init__(self):
        super().__init__()

        # maybe initialize plugin cvars
        self.set_cvar_once("qlx_discordBotToken", "")
        self.set_cvar_once("qlx_discordRelayChannelIds", "")
        self.set_cvar_once("qlx_discordTriggeredChannelIds", "")
        self.set_cvar_once("qlx_discordUpdateTopicOnTriggeredChannels", "1")
        self.set_cvar_once("qlx_discordKeepTopicSuffixChannelIds", "")
        self.set_cvar_once("qlx_discordTriggerTriggeredChannelChat", "!quakelive")
        self.set_cvar_once("qlx_discordTriggerStatus", "!status")
        self.set_cvar_once("qlx_discordMessagePrefix", "[DISCORD]")
        self.set_cvar_once("qlx_displayChannelForDiscordRelayChannels", "1")
        self.set_cvar_once("qlx_discordQuakeRelayMessageFilters", "^\!s$, ^\!p$")
        self.set_cvar_once("qlx_discordReplaceMentionsForRelayedMessages", "1")
        self.set_cvar_once("qlx_discordReplaceMentionsForTriggeredMessages", "1")
        self.set_cvar_once("qlx_discordAdminPassword", "supersecret")
        self.set_cvar_once("qlx_discordAuthCommand", ".auth")
        self.set_cvar_once("qlx_discordExecPrefix", ".qlx")

        # get the actual cvar values from the server
        self.discord_message_filters = self.get_cvar("qlx_discordQuakeRelayMessageFilters", set)

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

        self.authed_discord_ids = set()
        self.auth_attempts = {}

        # initialize the discord bot and its interactions on the discord server
        self.discord = SimpleAsyncDiscord(self.version_information())
        self.logger.info("Connecting to Discord...")
        self.discord.start()
        self.logger.info(self.version_information())
        Plugin.msg(self.version_information())

    def version_information(self):
        return "{} Version: {}".format(self.name, plugin_version)

    def handle_plugin_unload(self, plugin: minqlx.Plugin):
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
        if game.roundlimit in [game.blue_score, game.red_score]:
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
            player_data += "**R:** {}\n".format(mydiscordbot.team_data(teams['red']))
        if len(teams['blue']) > 0:
            player_data += "**B:** {}".format(mydiscordbot.team_data(teams['blue']))

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
            team_data += "**{0.clean_name}**({0.score}) ".format(player)

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
                            "spectator_chat": " *(to spacs)*"}
        if channel.name not in handled_channels:
            return

        if self.is_filtered_message(msg):
            return

        self.discord.relay_chat_message(player.clean_name, handled_channels[channel.name], Plugin.clean_text(msg))

    @minqlx.delay(3)
    def handle_player_connect(self, player: minqlx.Player):
        """
        Handler called when a player connects. The method sends a corresponding message to the discord relay channels,
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        """
        content = "*{} connected.*".format(player.clean_name)
        self.discord.relay_message(content)

        self.discord.update_topics()

    @minqlx.delay(3)
    def handle_player_disconnect(self, player: minqlx.Player, reason):
        """
        Handler called when a player disconnects. The method sends a corresponding message to the discord relay
        channels, and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        :param reason: the reason why the player left
        """
        if reason in ["disconnected", "timed out", "was kicked"]:
            reason_str = "{}.".format(reason)
        else:
            reason_str = "was kicked ({}).".format(Plugin.clean_text(reason))
        content = "*{} {}*".format(player.clean_name,
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
        content = "*Changing map to {}...*".format(mapname)
        self.discord.relay_message(content)

        self.discord.update_topics()

    def handle_vote_started(self, caller, vote, args):
        """
        Handler called when a vote was started. The method sends a corresponding message to the discord relay channels.

        :param caller: the player that initiated the vote
        :param vote: the vote itself, i.e. map change, kick player, etc.
        :param args: any arguments of the vote, i.e. map name, which player to kick, etc.
        """
        caller = caller.clean_name if caller else "The server"
        content = "*{} called a vote: {} {}*".format(caller,
                                                     vote,
                                                     Plugin.clean_text(args))

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

        self.discord.relay_message("{}\n{}".format(topic, top5_players))

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
    def __init__(self, version_information):
        super().__init__()
        self.version_information = version_information
        self.logger = minqlx.get_logger("discord")
        self.discord = None

        self.authed_discord_ids = set()
        self.auth_attempts = {}

        self.discord_bot_token = Plugin.get_cvar("qlx_discordBotToken")
        self.discord_relay_channel_ids = Plugin.get_cvar("qlx_discordRelayChannelIds", set)
        self.discord_triggered_channel_ids = Plugin.get_cvar("qlx_discordTriggeredChannelIds", set)
        self.discord_update_triggered_channels_topic = \
            Plugin.get_cvar("qlx_discordUpdateTopicOnTriggeredChannels", bool)
        self.discord_keep_topic_suffix_channel_ids = Plugin.get_cvar("qlx_discordKeepTopicSuffixChannelIds", set)
        self.discord_trigger_triggered_channel_chat = Plugin.get_cvar("qlx_discordTriggerTriggeredChannelChat")
        self.discord_trigger_status = Plugin.get_cvar("qlx_discordTriggerStatus")
        self.discord_message_prefix = Plugin.get_cvar("qlx_discordMessagePrefix")
        self.discord_show_relay_channel_names = Plugin.get_cvar("qlx_displayChannelForDiscordRelayChannels", bool)
        self.discord_message_filters = Plugin.get_cvar("qlx_discordQuakeRelayMessageFilters", set)
        self.discord_replace_relayed_mentions = Plugin.get_cvar("qlx_discordReplaceMentionsForRelayedMessages", bool)
        self.discord_replace_triggered_mentions = \
            Plugin.get_cvar("qlx_discordReplaceMentionsForTriggeredMessages", bool)
        self.discord_admin_password = Plugin.get_cvar("qlx_discordAdminPassword")
        self.discord_auth_command = Plugin.get_cvar("qlx_discordAuthCommand")
        self.discord_exec_prefix = Plugin.get_cvar("qlx_discordExecPrefix")

    def run(self):
        # the discord bot runs in an asyncio event_loop. For proper unloading and closing of the connection, we need
        # to initialize the event_loop the bot runs in.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # init the bot, and init the main discord interactions
        self.discord = commands.Bot(command_prefix='!')

        @self.discord.async_event
        async def on_ready():
            """
            Function called once the bot connected. Mainly displays status update from the bot in the game console
            and server logfile, and sets the bot to playing Quake Live on discord.
            """
            self.logger.info("Logged in to discord as: {} ({})".format(self.discord.user.name, self.discord.user.id))
            Plugin.msg("Connected to discord")
            await self.discord.change_presence(game=discord.Game(name="Quake Live"))
            self.update_topics()

        def handle_auth(message: discord.Message):
            """
            handles the authentification to the bot via private message

            :param message: the original message sent for authentification
            """
            if message.author.id in self.authed_discord_ids:
                self.send_to_discord_channels({message.channel.id}, "You are already authenticated.")
            elif message.content[len(self.discord_auth_command) + 1:] == self.discord_admin_password:
                self.authed_discord_ids.add(message.author.id)
                self.send_to_discord_channels({message.channel.id},
                                              "You have been successfully authenticated. You can now use "
                                              "{} to execute commands.".format(self.discord_exec_prefix))
            else:
                # Allow up to 3 attempts for the user's IP to authenticate.
                if message.author.id not in self.auth_attempts:
                    self.auth_attempts[message.author.id] = 3
                self.auth_attempts[message.author.id] -= 1
                if self.auth_attempts[message.author.id] > 0:
                    self.send_to_discord_channels({message.channel.id},
                                                  "Wrong password. You have {} attempts left."
                                                  .format(self.auth_attempts[message.author.id]))

        def handle_exec(message: discord.Message):
            """
            handles exec messages from discord via private message to the bot

            :param message: the original message
            """
            @minqlx.next_frame
            def f():
                try:
                    minqlx.COMMANDS.handle_input(
                        DiscordDummyPlayer(self, message.author, message.channel),
                        message.content[len(self.discord_exec_prefix) + 1:],
                        DiscordChannel(self, message.author, message.channel))
                except Exception as e:
                    self.send_to_discord_channels({message.channel.id}, "{}: {}".format(e.__class__.__name__, e))
                    minqlx.log_exception()

            f()

        def is_auth_attempt(message: discord.Message):
            """
            checks whether a discord message is a private auth attempt

            :param message: the original message sent by the user
            :return: boolean indicating whether the message sent was an attempt for authentification
            """
            return len(message.content) > len(self.discord_auth_command) \
                and message.content[0:len(self.discord_auth_command)].lower() == self.discord_auth_command \
                and self.discord_admin_password

        def is_exec_attempt(message: discord.Message):
            """
            checks whether a discord message is a private message attempt to execute a minqlx command

            :param message: the original message sent by the user
            :return: boolean indicating whether the message sent was an attempt for authentification
            """
            return len(message.content) > len(self.discord_exec_prefix) \
                and message.author.id in self.authed_discord_ids \
                and message.content[0:len(self.discord_exec_prefix)].lower() == self.discord_exec_prefix

        def handle_private_message(message: discord.Message):
            """
            handles private messages sent to the bot

            :param message: the original message
            """
            if is_auth_attempt(message):
                handle_auth(message)
                return

            if is_exec_attempt(message):
                handle_exec(message)

        def reply_for_help_request(message: discord.Message):
            """
            Generates a reply for !help requests that may be sent back to the user.

            :param message: the original message
            :return: the content help message to be sent back to the user
            """
            if message.channel.id in self.discord_triggered_channel_ids:
                return "Commands I react to in <#{0}>\n" \
                       "**!help**: display this help message\n" \
                       "**!version**: display the plugin's version information\n" \
                       "**{1}**: display current game status information\n" \
                       "**{2}** *<message>*: send *<message>* to the Quake Live server"\
                    .format(message.channel.id,
                            self.discord_trigger_status,
                            self.discord_trigger_triggered_channel_chat)

            if message.channel.id in self.discord_relay_channel_ids:
                return "Commands I react to in <#{0}>\n" \
                       "**!help**: display this help message\n" \
                       "**!version**: display the plugin's version information\n" \
                       "**{1}**: display current game status information\n\n" \
                       "Every other message from <#{0}> is relayed to the server."\
                    .format(message.channel.id, self.discord_trigger_status)
            return None

        def handle_help(message: discord.Message):
            """
            Handles help requests for the bot by sending back usage information.

            :param message: the original help request message
            """
            reply = reply_for_help_request(message)
            if not reply:
                return

            self.send_to_discord_channels({message.channel.id}, reply)

        @self.discord.async_event
        async def on_message(message: discord.Message):
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

            if message.content.startswith("!help"):
                handle_help(message)
                return

            if message.content == "!version":
                reply = self.version_information
                self.send_to_discord_channels({message.channel.id}, reply)
                return

            if message.channel.is_private:
                handle_private_message(message)
                return

            # if the message wasn't sent to a channel we're interested in, do nothing.
            if message.channel.id not in self.discord_relay_channel_ids | self.discord_triggered_channel_ids:
                return

            # someone requested the current game state to be sent back to the channel.
            if message.content == self.discord_trigger_status:
                try:
                    game = minqlx.Game()
                    reply = "{}\n{}".format(
                        mydiscordbot.game_status_information(game),
                        mydiscordbot.player_data())
                except minqlx.NonexistentGameError:
                    reply = "Currently no game running."
                self.send_to_discord_channels({message.channel.id}, reply)

            # relay all messages from the relay channels back to Quake Live.
            if message.channel.id in self.discord_relay_channel_ids:
                minqlx.CHAT_CHANNEL.reply(
                    self._format_message_to_quake(message.channel, message.author, message.clean_content))

            # relay all messages that have the trigger as prefix from the triggered channels.
            if message.channel.id in self.discord_triggered_channel_ids:
                if message.content.startswith(self.discord_trigger_triggered_channel_chat + " "):
                    content = message.clean_content[(len(self.discord_trigger_triggered_channel_chat) + 1):]
                    minqlx.CHAT_CHANNEL.reply(
                        self._format_message_to_quake(message.channel, message.author, content))

        # connect the now configured bot to discord in the event_loop
        loop.run_until_complete(self.discord.start(self.discord_bot_token))

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
        if self.discord_update_triggered_channels_topic:
            topic_channel_ids = self.discord_relay_channel_ids | self.discord_triggered_channel_ids
        else:
            topic_channel_ids = self.discord_relay_channel_ids

        # directly set the topic on channels with no topic suffix
        self.set_topic_on_discord_channels(topic_channel_ids - self.discord_keep_topic_suffix_channel_ids, topic)
        # keep the topic suffix on the channels that are configured accordingly
        self.update_topic_on_channels_and_keep_channel_suffix(
            topic_channel_ids & self.discord_keep_topic_suffix_channel_ids, topic)

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
                continue

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
        if self.discord is None or not self.discord.is_logged_in:
            return None

        channel = self.discord.get_channel(channel_id)

        if channel is None:
            return None

        return channel.topic

    @staticmethod
    def _discord_api_channel_url(channel_id):
        """
        Generates the basis for the discord api's channel url from the given channel_id.

        :param channel_id: the id of the channel for direct http/json requests
        :return: the channel url of the provided channel_id for direct interaction with the discord api
        """
        return "https://discordapp.com/api/channels/{}".format(channel_id)

    def _discord_api_request_headers(self):
        """
        Generates the discord api headers for direct discord api interactions from the provided token's bot.

        :return: the request headers for the provided token's bot
        """
        return {'Content-type': 'application/json', 'Authorization': "Bot {}".format(self.discord_bot_token)}

    @minqlx.thread
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
            # we use the raw request method here since it leads to fewer lag between minqlx and discord
            requests.patch(SimpleAsyncDiscord._discord_api_channel_url(channel_id),
                           data=json.dumps({'topic': topic}),
                           headers=self._discord_api_request_headers())

    @minqlx.thread
    def send_to_discord_channels(self, channel_ids, content):
        """
        Send a message to a set of channel_ids on discord provided.

        :param channel_ids: the ids of the channels the message should be sent to.
        :param content: the content of the message to send to the discord channels
        """
        # if we were not provided any channel_ids, do nothing.
        if not channel_ids or len(channel_ids) == 0:
            return

        # send the message in its own thread to avoid blocking of the server
        for channel_id in channel_ids:
            # we use the raw request method here since it leads to fewer lag between minqlx and discord
            requests.post(SimpleAsyncDiscord._discord_api_channel_url(channel_id) + "/messages",
                          data=json.dumps({'content': content}),
                          headers=self._discord_api_request_headers())

    def stop(self):
        """
        stops the discord client
        """
        if self.discord is None:
            return

        self.discord.loop.create_task(self.discord.change_presence(status="offline"))
        self.discord.loop.create_task(self.discord.logout())

    def relay_message(self, msg):
        """
        relay a message to the configured relay_channels

        :param msg: the message to send to the relay channel
        """
        self.send_to_discord_channels(self.discord_relay_channel_ids, msg)

    def relay_chat_message(self, player, channel, message):
        """
        relay a message to the given channel

        :param player: the player that originally sent the message
        :param channel: the channel the original message came through
        :param message: the content of the message
        """
        if self.discord_replace_relayed_mentions:
            message = self.replace_user_mentions(message)
            message = self.replace_channel_mentions(message)

        content = "**{}**{}: {}".format(player, channel, message)

        self.relay_message(content)

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

        content = "**{}**: {}".format(Plugin.clean_text(player.name), message)
        self.send_to_discord_channels(self.discord_triggered_channel_ids, content)

    def replace_user_mentions(self, message, player=None):
        """
        replaces a mentioned discord user (indicated by @user-hint with a real mention

        :param message: the message to replace the user mentions in
        :param player: (default: None) when several alternatives are found for the mentions used, this player is told
        what the alternatives are. No replacements for the ambiguous substitutions will happen.

        :return: the original message replaced by properly formatted user mentions
        """
        if self.discord is None or not self.discord.is_logged_in:
            return message

        returned_message = message
        # this regular expression will make sure that the "@user" has at least three characters, and is either
        # prefixed by a space or at the beginning of the string
        matcher = re.compile("(?:^| )@([^ ]{3,})")

        member_list = [user for user in self.discord.get_all_members()]
        matches = matcher.findall(returned_message)

        for match in sorted(matches, key=lambda user_match: len(user_match), reverse=True):
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
        member = set(user for user in member_list if user.name.lower().find(match.lower()) != -1 or
                     (user.nick is not None and user.nick.lower().find(match.lower()) != -1))
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
        if self.discord is None or not self.discord.is_logged_in:
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

    def _format_message_to_quake(self, channel: discord.Channel, author: discord.User, content):
        """
        Format the channel, author, and content of a message so that it will be displayed nicely in the Quake Live
        console.

        :param channel: the channel, the message came from.
        :param author: the author of the original message.
        :param content: the message itself, ideally taken from message.clean_content to avoid ids of mentioned users
        and channels on the discord server.
        :return: the formatted message that may be sent back to Quake Live.
        """
        if not self.discord_show_relay_channel_names and channel.id in self.discord_relay_channel_ids:
            return "{0} ^6{1.name}^7:^2 {2}".format(self.discord_message_prefix, author, content)
        return "{0} ^5#{1.name} ^6{2.name}^7:^2 {3}".format(self.discord_message_prefix, channel, author, content)
