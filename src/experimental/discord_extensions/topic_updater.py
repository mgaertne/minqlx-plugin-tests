import threading
import asyncio
from ast import literal_eval
from typing import Optional, Set, Dict

# noinspection PyPackageRequirements
from discord import TextChannel

# noinspection PyPackageRequirements
from discord.ext.commands import Cog, Bot

import minqlx
from minqlx import Plugin


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
    if (
        game.roundlimit in [game.blue_score, game.red_score]
        or game.red_score < 0
        or game.blue_score < 0
    ):
        return f"Match ended: **{game.red_score}** - **{game.blue_score}**"
    if game.state == "in_progress":
        return f"Match in progress: **{game.red_score}** - **{game.blue_score}**"

    return "Warmup"


def game_status_information(game: minqlx.Game) -> str:
    """
    Generate the text for the topic set on discord channels.

    :param: game: the game to derive the status information from

    :return: the topic that represents the current game state.
    """
    ginfo = get_game_info(game)

    num_players = len(Plugin.players())
    max_players = game.maxclients

    maptitle = game.map_title if game.map_title else game.map
    gametype = game.type_short.upper()

    # CAUTION: if you change anything on the next line, you may need to change the topic_ending logic in
    #          :func:`TopicUpdater.update_topic_on_triggered_channels(self, topic)` to keep the right portion
    #          of the triggered relay channels' topics!
    return (
        f"{ginfo} on **{Plugin.clean_text(maptitle)}** ({gametype}) "
        f"with **{num_players}/{max_players}** players. "
    )


def int_set(string_set: Optional[Set[str]]) -> Set[int]:
    returned: Set[int] = set()

    if string_set is None:
        return returned

    for item in string_set:
        if item == "":
            continue
        value = int(item)
        returned.add(value)

    return returned


class TopicUpdater(Cog):
    """
    Uses:
    * qlx_discordUpdateTopicOnTriggeredChannels (default: "1") Boolean flag to indicate whether to update the topic with
    the current game state on triggered relay channels. Your bot needs edit_channel permission for these channels.
    * qlx_discordKeepTopicSuffixChannelIds (default: "") Comma separated list of channel ids where the topic suffix
    will be kept upon updating.
    * qlx_discordUpdateTopicInterval (default: 305) Amount of seconds between automatic topic updates
    * qlx_discordKeptTopicSuffixes (default: {}) A dictionary of channel_ids for kept topic suffixes and the related
    suffixes. Make sure to use single quotes for the suffixes.
    """

    def __init__(self, bot: Bot):
        self.bot = bot

        Plugin.set_cvar_once("qlx_discordUpdateTopicOnTriggeredChannels", "1")
        Plugin.set_cvar_once("qlx_discordKeepTopicSuffixChannelIds", "")
        Plugin.set_cvar_once("qlx_discordUpdateTopicInterval", "305")
        Plugin.set_cvar_once("qlx_discordKeptTopicSuffixes", "{}")

        self.discord_relay_channel_ids: Set[int] = int_set(
            Plugin.get_cvar("qlx_discordRelayChannelIds", set)
        )
        self.discord_triggered_channel_ids: Set[int] = int_set(
            Plugin.get_cvar("qlx_discordTriggeredChannelIds", set)
        )

        self.discord_update_triggered_channels_topic: bool = (
            Plugin.get_cvar("qlx_discordUpdateTopicOnTriggeredChannels", bool) or True
        )
        self.discord_topic_update_interval: int = (
            Plugin.get_cvar("qlx_discordUpdateTopicInterval", int) or 305
        )
        self.discord_keep_topic_suffix_channel_ids: Set[int] = int_set(
            Plugin.get_cvar("qlx_discordKeepTopicSuffixChannelIds", set)
        )
        self.discord_kept_topic_suffixes: Dict[int, str] = literal_eval(
            Plugin.get_cvar("qlx_discordKeptTopicSuffixes", str) or "{}"
        )

        super().__init__()

    async def cog_load(self):
        self._topic_updater()

    def _topic_updater(self) -> None:
        try:
            game = minqlx.Game()
            topic = game_status_information(game)
            self.update_topics_on_relay_and_triggered_channels(topic)
        except minqlx.NonexistentGameError:
            pass
        finally:
            threading.Timer(
                self.discord_topic_update_interval, self._topic_updater
            ).start()

    def update_topics_on_relay_and_triggered_channels(self, topic: str) -> None:
        """
        Helper function to update the topics on all the relay and all the triggered channels

        :param: topic: the topic to set on all the channels
        """
        if not self.is_discord_logged_in():
            return

        if self.discord_update_triggered_channels_topic:
            topic_channel_ids = (
                self.discord_relay_channel_ids | self.discord_triggered_channel_ids
            )
        else:
            topic_channel_ids = self.discord_relay_channel_ids

        # directly set the topic on channels with no topic suffix
        self.set_topic_on_discord_channels(
            topic_channel_ids - self.discord_keep_topic_suffix_channel_ids, topic
        )
        # keep the topic suffix on the channels that are configured accordingly
        self.update_topic_on_channels_and_keep_channel_suffix(
            topic_channel_ids & self.discord_keep_topic_suffix_channel_ids, topic
        )

    def set_topic_on_discord_channels(self, channel_ids: Set[int], topic: str) -> None:
        """
        Set the topic on a set of channel_ids on discord provided.

        :param: channel_ids: the ids of the channels the topic should be set upon.
        :param: topic: the new topic that should be set.
        """
        # if we were not provided any channel_ids, do nothing.
        if not channel_ids or len(channel_ids) == 0:
            return

        # set the topic in its own thread to avoid blocking of the server
        for channel_id in channel_ids:
            channel: Optional[TextChannel] = self.bot.get_channel(channel_id)  # type: ignore

            if channel is None:
                continue

            asyncio.run_coroutine_threadsafe(
                channel.edit(topic=topic), loop=self.bot.loop
            )

    def is_discord_logged_in(self) -> bool:
        if self.bot is None:
            return False

        return not self.bot.is_closed() and self.bot.is_ready()

    def update_topic_on_channels_and_keep_channel_suffix(
        self, channel_ids: Set[int], topic: str
    ) -> None:
        """
        Updates the topic on the given channels and keeps the topic suffix intact on the configured channels

        :param: channel_ids: the set of channels to update the topic on
        :param: topic: the topic to set on the given channels
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
            topic_suffix = (
                previous_topic[position + len(topic_ending) :]
                if position != -1
                else previous_topic
            )

            if channel_id in self.discord_kept_topic_suffixes:
                topic_suffix = self.discord_kept_topic_suffixes[channel_id]

            # update the topic on the triggered channels
            self.set_topic_on_discord_channels({channel_id}, f"{topic}{topic_suffix}")

    def get_channel_topic(self, channel_id: int) -> Optional[str]:
        """
        get the topic of the provided channel id

        :param: channel_id: the id of the channel to get the topic from

        :return: the topic of the channel
        """
        channel: Optional[TextChannel] = self.bot.get_channel(channel_id)  # type: ignore

        if channel is None:
            return None

        return channel.topic


async def setup(bot: Bot):
    await bot.add_cog(TopicUpdater(bot))
