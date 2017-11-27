import re
import asyncio

import minqlx
from minqlx import Plugin

import discord
from discord.ext import commands

re_topic = re.compile(r".*players. (.*)$")


class discordbot(minqlx.Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_discordBotToken", "")
        self.set_cvar_once("qlx_discordRelayChannelIds", "")
        self.set_cvar_once("qlx_discordIdleChannelIds", "")
        self.set_cvar_once("qlx_discordUpdateTopicOnIdleChannels", "1")
        self.set_cvar_once("qlx_discordTriggerIdleChannelChat", "!quakelive")
        self.set_cvar_once("qlx_discordTriggerStatus", "!status")

        self.discord_bot_token = self.get_cvar("qlx_discordBotToken")
        self.discord_relay_channel_ids = self.get_cvar("qlx_discordRelayChannelIds", set)
        self.discord_idle_channel_ids = self.get_cvar("qlx_discordIdleChannelIds", set)
        self.discord_update_idle_channels_topic = self.get_cvar("qlx_discordUpdateTopicOnIdleChannels", bool)
        self.discord_trigger_idle_channel_chat = self.get_cvar("qlx_discordTriggerIdleChannelChat")
        self.discord_trigger_status = self.get_cvar("qlx_discordTriggerStatus")

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

        self.discord = None
        self.init_bot()

    @minqlx.thread
    def init_bot(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.discord = commands.Bot(command_prefix='!')

        @self.discord.event
        async def on_ready():
            self.logger.info("Logged in to discord as: {} ({})".format(self.discord.user.name, self.discord.user.id))
            Plugin.msg("Connected to discord")
            await self.discord.change_presence(game=discord.Game(name="Quake Live"))

        @self.discord.event
        async def on_message(message: discord.Message):
            if not message:
                return

            if message.author == self.discord.user:
                return

            if message.channel.id not in self.discord_relay_channel_ids | self.discord_idle_channel_ids:
                return

            if message.content == self.discord_trigger_status:
                await self.discord.send_message(message.channel,
                                                "{}\n{}".format(self.generate_topic(), self.player_data()))

            if message.channel.id in self.discord_relay_channel_ids:

                minqlx.CHAT_CHANNEL.reply(discordbot.format_discord_message(message))

            if message.channel.id in self.discord_idle_channel_ids:
                if message.content.startswith(self.discord_trigger_idle_channel_chat + " "):
                    content = message.clean_content[(len(self.discord_trigger_idle_channel_chat) + 1):]
                    minqlx.CHAT_CHANNEL.reply(
                        self.format_message_to_quake(message.channel.name, message.author.name, content))

        self.logger.info("Connecting to Discord...")
        loop.run_until_complete(self.discord.start(self.discord_bot_token))

    @staticmethod
    def format_discord_message(message: discord.Message):
        return discordbot.format_message_to_quake(message.channel.name, message.author.name, message.clean_content)

    @staticmethod
    def format_message_to_quake(channel, author, content):
        return "[DISCORD] ^5#{} ^6{}^7:^2 {}".format(channel, author, content)

    def handle_plugin_unload(self, plugin):
        if plugin == self.__class__.__name__ and self.discord:
            async def shutdown_discord():
                await self.discord.wait_until_ready()
                await self.discord.logout()

            self.discord.loop.create_task(shutdown_discord())

    def update_topics(self, *args, **kwargs):
        topic = self.generate_topic()

        players = self.get_players()
        top5_players = self.player_data() if len(players) > 0 else ""

        self.set_topic_on_discord_channels(self.discord_relay_channel_ids, "{}{}".format(topic, top5_players))
        self.update_topic_on_idle_channels(topic)

    def generate_topic(self):
        game = self.game
        players = self.get_players()
        ginfo = self.get_game_info()
        topic = "{} on {} ({}) with {}/{} players. ".format(ginfo,
                                                            self.clean_text(game.map_title),
                                                            game.type_short.upper(),
                                                            len(players),
                                                            self.get_cvar("sv_maxClients"))
        return topic

    def player_data(self, *args, **kwargs):
        player_data = ""
        players_by_score = sorted(self.teams()['spectator'] + self.teams()['blue'] + self.teams()['red'],
                                  key=lambda k: k.score, reverse=True)[:5]  # get top 5 players list!

        for player in players_by_score:
            player_time = 0
            if self.game.state == "in_progress":
                player_time = int(player.stats.time / 60000)
            player_data += "**{}**: {} ({}m)- ".format(self.clean_text(player.name), player.score, player_time)

        return player_data

    def handle_ql_chat(self, player, msg, channel):
        handled_channels = {"chat": "",
                            "red_team_chat": "*(to red team)*",
                            "blue_team_chat": "*(to blue team)*",
                            "spectator_chat": "*(to spacs)*"}
        if not self.discord or not self.discord_relay_channel_ids or channel.name not in handled_channels:
            return

        content = "**{}**{}: {}".format(Plugin.clean_text(player.name), handled_channels[channel.name], msg)

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

    @minqlx.delay(3)
    def handle_player_connect(self, player):
        topic = self.generate_topic()
        content = "*{} connected.*".format(Plugin.clean_text(player.name))

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)
        self.set_topic_on_discord_channels(self.discord_relay_channel_ids, topic)
        self.update_topic_on_idle_channels(topic)

    @minqlx.delay(3)
    def handle_player_disconnect(self, player, reason):
        topic = self.generate_topic()

        if reason and reason[-1] not in ("?", "!", "."):
            reason = reason + "."
        content = "*{} {}*".format(self.clean_text(player.name), reason)

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)
        self.set_topic_on_discord_channels(self.discord_relay_channel_ids, topic)
        self.update_topic_on_idle_channels(topic)

    def handle_map(self, map, factory):
        content = "*Changed map to {}...*".format(map)
        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

    def handle_vote_started(self, caller, vote, args):
        caller = self.clean_text(caller.name) if caller else "The server"
        content = "*{} called a vote: {} {}*".format(self.clean_text(caller), vote, args)

        self.set_topic_on_discord_channels(self.discord_relay_channel_ids, content)

    def handle_vote_ended(self, votes, vote, args, passed):
        if passed:
            content = "*Vote passed ({} - {}).*".format(*votes)
        else:
            content = "*Vote failed.*"

        self.send_to_discord_channels(self.discord_relay_channel_ids, content)

    @minqlx.delay(1)
    def handle_game_countdown(self):
        self.update_topics()

        topic = self.generate_topic()
        top5_players = self.player_data()

        self.send_to_discord_channels(self.discord_relay_channel_ids, "{}\n{}".format(topic, top5_players))

    def cmd_discord(self, player, msg, channel):
        if len(msg) < 2:
            return minqlx.RET_USAGE
        if self.discord_idle_channel_ids:
            content = "**{}**: {}".format(self.clean_text(player.name), " ".join(msg[1:]))
            self.send_to_discord_channels(self.discord_idle_channel_ids, content)
            self.msg("Message to Discord chat cast!")

    def update_topic_on_idle_channels(self, topic):
        if not self.discord_update_idle_channels_topic:
            return

        if not self.discord or not self.discord.is_logged_in:
            return

        if not self.discord_idle_channel_ids or len(self.discord_idle_channel_ids) == 0:
            return

        for channel_id in self.discord_idle_channel_ids:
            channel = self.discord.get_channel(channel_id)
            topic_suffix = ""
            if channel and channel.topic:
                match = re_topic.match(channel.topic)
                topic_suffix = match.group(1) if match else channel.topic
            self.discord.loop.create_task(self._set_topic_on_channels(self.discord_idle_channel_ids,
                                                                      "{} {}".format(topic, topic_suffix)))

    def send_to_discord_channels(self, channel_ids, content):
        if not self.discord or not self.discord.is_logged_in:
            return

        if not channel_ids or len(channel_ids) == 0:
            return

        self.discord.loop.create_task(self._send_to_channels(channel_ids, content))

    async def _send_to_channels(self, channel_ids, content):
        await self.discord.wait_until_ready()
        for channel_id in channel_ids:
            channel = discord.Object(id=channel_id)
            if channel:
                await self.discord.send_message(channel, content)

    def set_topic_on_discord_channels(self, channel_ids, topic):
        if not self.discord or not self.discord.is_logged_in:
            return

        if not channel_ids or len(channel_ids) == 0:
            return

        self.discord.loop.create_task(self._set_topic_on_channels(channel_ids, topic))

    async def _set_topic_on_channels(self, channel_ids, topic):
        await self.discord.wait_until_ready()
        for channel_id in channel_ids:
            channel = self.discord.get_channel(channel_id)
            if channel:
                await self.discord.edit_channel(channel, topic=topic)

    def get_players(self):
        teams = self.teams()
        return teams["free"] + teams["red"] + teams["blue"] + teams["spectator"]

    def get_game_info(self):
        game = self.game
        if game.state == "in_progress":
            return "Match in progress: {} - {}".format(game.red_score, game.blue_score)
        elif game.state == "countdown":
            return "Match starting"
        else:
            return "Warmup"
