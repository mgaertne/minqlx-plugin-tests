"""
This is a plugin created by ShiN0
Copyright (c) 2017 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one, except for the version command related code.

The basic ideas for this plugin came from Gelenkbusfahrer and roast
<https://github.com/roasticle/minqlx-plugins/blob/master/discordbot.py> and have been mainly discussed on the
fragstealers_inc discord tech channel of the Bus Station server(s).
"""
import re
import asyncio
import requests
import json

import minqlx
from minqlx import Plugin

import discord
from discord.ext import commands

# a regular expression that matches the format of the :func:`DiscordBot.generate_topic(self)` function.
# This regular expression is used to keep a static suffix on the idling channels upon changing the topic with the
# current state of the server.
#
# If you change the behavior :func:`DiscordBot.generate_topic()` function, you may need to change this
# regular expression, too!
re_topic = re.compile(r".*players. (.*)$")


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
    * qlx_discordIdleChannelIds (default: "") Comma separated list of channels for triggered relay.
    * qlx_discordUpdateTopicOnIdleChannels (default: "1") Boolean flag to indicate whether to update the topic with the
    current game state on triggered relay channels. Your bot needs edit_channel permission for these channels.
    * qlx_discordTriggerIdleChannelChat (default: "!quakelive") Message prefix for the trigger on triggered relay
    channels.
    * qlx_discordTriggerStatus (default: "!status") Trigger for having the bot send the current status of the game
    server.
    """

    def __init__(self):
        super().__init__()

        # maybe initialize plugin cvars
        self.set_cvar_once("qlx_discordBotToken", "")
        self.set_cvar_once("qlx_discordRelayChannelIds", "")
        self.set_cvar_once("qlx_discordTriggeredChannelIds", "")
        self.set_cvar_once("qlx_discordUpdateTopicOnTriggeredChannels", "1")
        self.set_cvar_once("qlx_discordTriggerTriggeredChannelChat", "!quakelive")
        self.set_cvar_once("qlx_discordTriggerStatus", "!status")

        # get the actual cvar values from the server
        self.discord_bot_token = self.get_cvar("qlx_discordBotToken")
        self.discord_relay_channel_ids = self.get_cvar("qlx_discordRelayChannelIds", set)
        self.discord_triggered_channel_ids = self.get_cvar("qlx_discordTriggeredChannelIds", set)
        self.discord_update_triggered_channels_topic = self.get_cvar("qlx_discordUpdateTopicOnTriggeredChannels", bool)
        self.discord_trigger_triggered_channel_chat = self.get_cvar("qlx_discordTriggerTriggeredChannelChat")
        self.discord_trigger_status = self.get_cvar("qlx_discordTriggerStatus")

        # adding general plugin hooks
        self.add_hook("unload", self.handle_plugin_unload)
        self.add_hook("chat", self.handle_ql_chat, priority=minqlx.PRI_LOWEST)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_LOWEST)
        self.add_hook("player_disconnect", self.handle_player_disconnect, priority=minqlx.PRI_LOWEST)
        self.add_hook("map", self.handle_map)
        self.add_hook("vote_started", self.handle_vote_started)
        self.add_hook("vote_ended", self.handle_vote_ended)
        self.add_hook("game_countdown", self.handle_game_countdown, priority=minqlx.PRI_LOWEST)
        # Update topic on these hooks
        for hook in ["round_end", "game_start", "game_end", "map"]:
            self.add_hook(hook, self.update_topics, priority=minqlx.PRI_LOW)

        self.add_command("discord", self.cmd_discord, usage="<message>")

        # initialize the discord bot and its interactions on the discord server
        self.discord = None
        self.init_bot()

    @minqlx.thread
    def init_bot(self):
        """
        Init the discord bot, and initialize bot behavior from the discord side of this plugin.

        This method runs in its own thread to not block the overall game server during loading of the plugin.
        """
        # the discord bot runs in an asyncio event_loop. For proper unloading and closing of the connection, we need
        # to initialize the event_loop the bot runs in.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # init the bot, and init the main discord interactions
        self.discord = commands.Bot(command_prefix='!')

        @self.discord.event
        async def on_ready():
            """
            Function called once the bot connected. Mainly displays status update from the bot in the game console
            and server logfile, and sets the bot to playing Quake Live on discord.
            """
            self.logger.info("Logged in to discord as: {} ({})".format(self.discord.user.name, self.discord.user.id))
            Plugin.msg("Connected to discord")
            await self.discord.change_presence(game=discord.Game(name="Quake Live"))

        @self.discord.event
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

            # if the message wasn't sent to a channel we're interested in, do nothing.
            if message.channel.id not in self.discord_relay_channel_ids | self.discord_triggered_channel_ids:
                return

            # someone requested the current game state to be sent back to the channel.
            if message.content == self.discord_trigger_status:
                await self.discord.send_message(message.channel,
                                                "{}\n{}".format(self.generate_topic(), self.player_data()))

            # relay all messages from the relay channels back to Quake Live.
            if message.channel.id in self.discord_relay_channel_ids:
                minqlx.CHAT_CHANNEL.reply(mydiscordbot._format_discord_message(message))

            # relay all messages that have the trigger as prefix from the triggered channels.
            if message.channel.id in self.discord_triggered_channel_ids:
                if message.content.startswith(self.discord_trigger_triggered_channel_chat + " "):
                    content = message.clean_content[(len(self.discord_trigger_triggered_channel_chat) + 1):]
                    minqlx.CHAT_CHANNEL.reply(
                        self._format_message_to_quake(message.channel.name, message.author.name, content))

        # connect the now configured bot to discord in the event_loop
        self.logger.info("Connecting to Discord...")
        loop.run_until_complete(self.discord.start(self.discord_bot_token))

    @staticmethod
    def _format_discord_message(message: discord.Message):
        """
        Format a message from discord so that it will be displayed nicely in the Quake Live chat console.

        :param message: the message to format for Quake Live
        :return: the formatted message that may be sent back to Quake Live.
        """
        return mydiscordbot._format_message_to_quake(message.channel.name, message.author.name, message.clean_content)

    @staticmethod
    def _format_message_to_quake(channel, author, content):
        """
        Format the channel, author, and content of a message so that it will be displayed nicely in the Quake Live
        console.

        :param channel: the channel, the message came from.
        :param author: the author of the original message.
        :param content: the message itself, ideally taken from message.clean_content to avoid ids of mentioned users
        and channels on the discord server.
        :return: the formatted message that may be sent back to Quake Live.
        """
        return "[DISCORD] ^5#{} ^6{}^7:^2 {}".format(channel, author, content)

    def handle_plugin_unload(self, plugin):
        """
        Handler when a plugin is unloaded to make sure, that the connection to discord is properly closed when this
        plugin is unloaded.

        :param plugin: the plugin that was unloaded.
        """
        if plugin == self.__class__.__name__ and self.discord:
            async def shutdown_discord():
                await self.discord.wait_until_ready()
                await self.discord.logout()

            self.discord.loop.create_task(shutdown_discord())

    def update_topics(self, *args, **kwargs):
        """
        Update the current topic on the general relay channels, and the triggered relay channels. The latter will only
        happen when cvar qlx_discordUpdateTopicOnIdleChannels is set to "1".
        """
        topic = self.generate_topic()

        players = self.get_players()
        top5_players = self.player_data() if len(players) > 0 else ""

        self.set_topic_on_discord_channels(self.discord_relay_channel_ids, "{}{}".format(topic, top5_players))
        self.update_topic_on_triggered_channels(topic)

    def generate_topic(self):
        """
        Generate the text for the topic set on discord channels.

        :return: the topic that represents the current game state.
        """
        game = self.game
        players = self.get_players()
        ginfo = self.get_game_info()

        # CAUTION: if you change anything on the next line, you may need to redefine the regular expression re_topic to
        #          keep the right portion of the triggered relay channels' topics!
        topic = "{} on {} ({}) with {}/{} players. ".format(ginfo,
                                                            Plugin.clean_text(game.map_title),
                                                            game.type_short.upper(),
                                                            len(players),
                                                            self.get_cvar("sv_maxClients"))
        return topic

    def get_players(self):
        """
        Get all currently connected players.

        :return: a list of all players currently connected to the server.
        """
        teams = self.teams()
        return teams["free"] + teams["red"] + teams["blue"] + teams["spectator"]

    def get_game_info(self):
        """
        Helper to format the current game.state that may be used in status messages and setting of channel topics.

        :return: the current text representation of the game state
        """
        game = self.game
        if game.state == "in_progress":
            return "Match in progress: {} - {}".format(game.red_score, game.blue_score)
        elif game.state == "countdown":
            return "Match starting"
        else:
            return "Warmup"

    def player_data(self, *args, **kwargs):
        """
        Formats the top 5 scorers connected to the server in a string. The return value may be used for status messages
        and used in topics to indicate reveal more data about the server and its current game.

        :return: string of the current top5 scorers with the scores and connection time to the server
        """
        player_data = ""
        teams = self.teams()
        player_data += "**R:** {}\n".format(self.team_data(teams['red'], limit=5))
        player_data += "**B:** {}".format(self.team_data(teams['blue'], limit=5))

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

        team_data = ""
        if limit:
            players_by_score = sorted(player_list, key=lambda k: k.score, reverse=True)[:limit]
        else:
            players_by_score = sorted(player_list, key=lambda k: k.score, reverse=True)

        counter = 0
        previous_score = players_by_score[0].score + 1  # initialize the score to the maximum score + 1

        for player in players_by_score:
            if player.score < previous_score:
                counter += 1
                previous_score = player.score
            team_data += "{}. **{}**({}) ".format(counter, Plugin.clean_text(player.name), player.score)

        return team_data

    def handle_ql_chat(self, player, msg, channel):
        """
        Handler function for all chat messages on the server. This function will forward and messages on the Quake Live
        server to discord.

        :param player: the player that sent the message
        :param msg: the message that was sent
        :param channel: the chnannel the message was sent to
        """
        handled_channels = {"chat": "",
                            "red_team_chat": "*(to red team)*",
                            "blue_team_chat": "*(to blue team)*",
                            "spectator_chat": "*(to spacs)*"}
        if not self.discord or not self.discord_relay_channel_ids or channel.name not in handled_channels:
            return

        content = "**{}**{}: {}".format(Plugin.clean_text(player.name),
                                        handled_channels[channel.name],
                                        Plugin.clean_text(msg))

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

    @minqlx.delay(3)
    def handle_player_connect(self, player):
        """
        Handler called when a player connects. The method sends a corresponding message to the discord relay channels,
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        """
        content = "*{} connected.*".format(Plugin.clean_text(player.name))
        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

        self.update_topics()

    @minqlx.delay(3)
    def handle_player_disconnect(self, player, reason):
        """
        Handler called when a player disconnects. The method sends a corresponding message to the discord relay
        channels, and updates the relay channel topic as well as the trigger channels, when configured.

        :param player: the player that connected
        :param reason: the reason why the player left
        """
        if reason and reason[-1] not in ("?", "!", "."):
            reason = reason + "."
        content = "*{} {}*".format(Plugin.clean_text(player.name),
                                   Plugin.clean_text(reason))
        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

        self.update_topics()

    def handle_map(self, map, factory):
        """
        Handler called when a map is changed. The method sends a corresponding message to the discord relay channels.
        and updates the relay channel topic as well as the trigger channels, when configured.

        :param map: the new map
        """
        content = "*Changing map to {}...*".format(map)
        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

        self.update_topics()

    def handle_vote_started(self, caller, vote, args):
        """
        Handler called when a vote was started. The method sends a corresponding message to the discord relay channels.

        :param caller: the player that initiated the vote
        :param vote: the vote itself, i.e. map change, kick player, etc.
        :param args: any arguments of the vote, i.e. map name, which player to kick, etc.
        """
        caller = Plugin.clean_text(caller.name) if caller else "The server"
        content = "*{} called a vote: {} {}*".format(Plugin.clean_text(caller),
                                                     vote,
                                                     Plugin.clean_text(args))

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

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

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

    @minqlx.delay(1)
    def handle_game_countdown(self):
        """
        Handler called when the game is in countdown. This function mainly updates the topics of the relay channels and
        the triggered channels (when configured), and sends a message to all relay channels.
        """
        topic = self.generate_topic()
        top5_players = self.player_data()

        self.send_to_discord_channels(self.discord_relay_channel_ids, "{}\n{}".format(topic, top5_players))

        self.update_topics()

    def cmd_discord(self, player, msg, channel):
        """
        Handler of the !discord command. Forwards any messages after !discord to the discord triggered relay channels.

        :param player: the player that send to the trigger
        :param msg: the message the player sent (includes the trigger)
        :param channel: the channel the message came through, i.e. team chat, general chat, etc.
        """
        # when the message did not include anything to forward, show the usage help text.
        if len(msg) < 2:
            return minqlx.RET_USAGE

        if self.discord_triggered_channel_ids:
            content = "**{}**: {}".format(Plugin.clean_text(player.name),
                                          " ".join(Plugin.clean_text(msg[1:])))
            self.send_to_discord_channels(self.discord_triggered_channel_ids, content)
            self.msg("Message to Discord chat cast!")

    def update_topic_on_triggered_channels(self, topic):
        """
        Set the channel topic on all triggered relay channels, if and only if configured to do so.

        :param topic: the topic to set on the triggered relay channels
        """
        # if we should not update the triggered relay channels topics, then we shouldn't do so.
        if not self.discord_update_triggered_channels_topic:
            return

        # if the bot is not running or not connected, do nothing.
        if not self.discord or not self.discord.is_logged_in:
            return

        # if there are not triggered relay channels configured, do nothing.
        if not self.discord_triggered_channel_ids or len(self.discord_triggered_channel_ids) == 0:
            return

        for channel_id in self.discord_triggered_channel_ids:
            # we need to get the channel from the discord server first.
            channel = self.discord.get_channel(channel_id)

            # preserve the original channel's topic.
            topic_suffix = ""
            if channel and channel.topic:
                match = re_topic.match(channel.topic)
                topic_suffix = match.group(1) if match else channel.topic

            # update the topic on the triggered channels
            self.set_topic_on_discord_channels(self.discord_triggered_channel_ids, "{} {}".format(topic, topic_suffix))

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
            requests.post(mydiscordbot._discord_api_channel_url(channel_id) + "/messages",
                          data=json.dumps({'content': content}),
                          headers=mydiscordbot._discord_api_request_headers(self.discord_bot_token))

    @staticmethod
    def _discord_api_channel_url(channel_id):
        """
        Generates the basis for the discord api's channel url from the given channel_id.

        :param channel_id: the id of the channel for direct http/json requests
        :return: the channel url of the provided channel_id for direct interaction with the discord api
        """
        return "https://discordapp.com/api/channels/{}".format(channel_id)

    @staticmethod
    def _discord_api_request_headers(bot_token):
        """
        Generates the discord api headers for direct discord api interactions from the provided token's bot.

        :param bot_token: the token of the bot the headers should be generated for
        :return: the request headers for the provided token's bot
        """
        return {'Content-type': 'application/json', 'Authorization': "Bot {}".format(bot_token)}

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
            requests.patch(mydiscordbot._discord_api_channel_url(channel_id),
                           data=json.dumps({'topic': topic}),
                           headers=mydiscordbot._discord_api_request_headers(self.discord_bot_token))
