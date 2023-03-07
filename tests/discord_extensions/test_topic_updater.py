import threading
from unittest.mock import AsyncMock

import pytest

# noinspection PyPackageRequirements
from discord.abc import GuildChannel
from hamcrest import assert_that, equal_to, matches_regexp

# noinspection PyProtectedMember
from mockito import when, mock, unstub, verify, when2, spy2, any_

from minqlx_plugin_test import setup_cvars, connected_players, fake_player

from discord_extensions import topic_updater
from discord_extensions.topic_updater import TopicUpdater


class TestTopicUpdater:
    @pytest.fixture(autouse=True)
    def relay_channel(self, bot):
        channel = mock(spec=GuildChannel)
        channel.name = "DiscordRelayChannel"

        channel.id = 1234
        channel.edit = AsyncMock()
        when(bot).get_channel(channel.id).thenReturn(channel)
        yield channel
        unstub(channel)

    @pytest.fixture(autouse=True)
    def triggered_channel(self, bot):
        channel = mock(spec=GuildChannel)
        channel.id = 5678
        channel.topic = "dummy text | kept suffix"
        channel.edit = AsyncMock()
        when(bot).get_channel(channel.id).thenReturn(channel)
        yield channel
        unstub(channel)

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discordRelayChannelIds": "1234",
                "qlx_discordTriggeredChannelIds": "5678",
                "qlx_discordUpdateTopicOnTriggeredChannels": "1",
                "qlx_discordUpdateTopicInterval": "305",
                "qlx_discordKeptTopicSuffixes": "{5678: ' | kept suffix'}",
            }
        )

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_get_game_info_in_warmup(self, game_in_warmup):
        game_info = topic_updater.get_game_info(game_in_warmup)

        assert_that(game_info, equal_to("Warmup"))

    def test_get_game_info_in_countdown(self, game_in_countdown):
        game_info = topic_updater.get_game_info(game_in_countdown)

        assert_that(game_info, equal_to("Match starting"))

    def test_get_game_info_in_progress(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 1
        game_in_progress.blue_score = 2

        game_info = topic_updater.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match in progress: **1** - **2**"))

    def test_get_game_info_red_hit_roundlimit(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 8
        game_in_progress.blue_score = 2

        game_info = topic_updater.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **8** - **2**"))

    def test_get_game_info_blue_hit_roundlimit(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 8

        game_info = topic_updater.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **8**"))

    def test_get_game_info_red_player_dropped_out(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = -999
        game_in_progress.blue_score = 3

        game_info = topic_updater.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **-999** - **3**"))

    def test_get_game_info_blue_player_dropped_out(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = -999

        game_info = topic_updater.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **-999**"))

    def test_get_game_info_unknown_game_state(self, minqlx_game):
        minqlx_game.state = "unknown"
        minqlx_game.roundlimit = 8
        minqlx_game.red_score = 3
        minqlx_game.blue_score = 2

        game_info = topic_updater.get_game_info(minqlx_game)

        assert_that(game_info, equal_to("Warmup"))

    def test_game_status_information(self, game_in_progress):
        connected_players(
            fake_player(1, "RedPlayer1", team="red"),
            fake_player(2, "RedPlayer2", team="red"),
            fake_player(3, "BluePlayer1", team="blue"),
            fake_player(4, "BluePlayer2", team="blue"),
            fake_player(5, "SpecPlayer", team="spectator"),
        )
        game_in_progress.maxclients = 16
        game_in_progress.map_title = "Campgrounds"
        game_in_progress.type_short = "ca"
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 3

        game_status = topic_updater.game_status_information(game_in_progress)

        assert_that(
            game_status,
            matches_regexp(
                r"Match in progress: .*5.* - .*3.* on .*Campgrounds.* \(CA\) with .*5/16.* players\. "
            ),
        )

    @pytest.mark.asyncio
    async def test_timer_is_started_on_cog_load(self, bot, game_in_warmup):
        timer_mock = mock(spec=threading.Timer)
        timer_mock.start = mock()
        spy2(threading.Timer)
        when2(threading.Timer, any_, any_).thenReturn(timer_mock)

        game_in_warmup.maxclients = 16
        game_in_warmup.map_title = None
        connected_players()

        extension = TopicUpdater(bot)

        await extension.cog_load()

        verify(threading).Timer(305, extension._topic_updater)
        verify(timer_mock.start).__call__()

    @pytest.mark.asyncio
    async def test_timer_is_started_on_cog_load_no_game_running(
        self, bot, no_minqlx_game
    ):
        timer_mock = mock(spec=threading.Timer)
        timer_mock.start = mock()
        spy2(threading.Timer)
        when2(threading.Timer, any_, any_).thenReturn(timer_mock)

        extension = TopicUpdater(bot)

        await extension.cog_load()

        verify(threading).Timer(305, extension._topic_updater)
        verify(timer_mock.start).__call__()

    def test_when_bot_is_none_discord_is_not_logged_in(self, bot):
        extension = TopicUpdater(bot)
        extension.bot = None

        assert_that(extension.is_discord_logged_in(), equal_to(False))

    @pytest.mark.asyncio
    async def test_update_topics_on_relay_and_triggered_channels_discord_not_logged_in(
        self, bot, relay_channel
    ):
        when(bot).is_ready().thenReturn(False)

        extension = TopicUpdater(bot)

        extension.update_topics_on_relay_and_triggered_channels("new topic")

        relay_channel.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_topics_on_relay_and_triggered_channels_on_relay_channel_no_configured_suffix(
        self, bot, relay_channel
    ):
        when(bot).is_ready().thenReturn(True)
        when(bot).is_closed().thenReturn(False)

        extension = TopicUpdater(bot)

        extension.update_topics_on_relay_and_triggered_channels("new topic")

        relay_channel.edit.assert_called_once_with(topic="new topic")

    @pytest.mark.asyncio
    async def test_update_topics_on_relay_and_triggered_channels_on_triggered_channel_suffix_kept(
        self, bot, triggered_channel
    ):
        when(bot).is_ready().thenReturn(True)
        when(bot).is_closed().thenReturn(False)

        extension = TopicUpdater(bot)

        extension.update_topics_on_relay_and_triggered_channels("new topic")

        triggered_channel.edit.assert_called_once_with(topic="new topic | kept suffix")

    @pytest.mark.asyncio
    async def test_update_topics_on_relay_channels_but_not_on_triggered_channel(
        self, bot, relay_channel, triggered_channel
    ):
        setup_cvars({"qlx_discordUpdateTopicOnTriggeredChannels": "0"})
        when(bot).is_ready().thenReturn(True)
        when(bot).is_closed().thenReturn(False)

        extension = TopicUpdater(bot)
        extension.discord_update_triggered_channels_topic = False

        extension.update_topics_on_relay_and_triggered_channels("new topic")

        relay_channel.edit.assert_called_once_with(topic="new topic")
        triggered_channel.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await topic_updater.setup(bot)

        bot.add_cog.assert_awaited_once()
        assert_that(
            isinstance(bot.add_cog.call_args.args[0], TopicUpdater), equal_to(True)
        )
