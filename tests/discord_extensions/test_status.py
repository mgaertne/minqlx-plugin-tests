from unittest.mock import AsyncMock

import pytest

from hamcrest import assert_that, equal_to, matches_regexp

from mockito import when, mock, unstub

# noinspection PyPackageRequirements
from discord import Message

# noinspection PyPackageRequirements
from discord.abc import GuildChannel

from minqlx_plugin_test import setup_cvars, connected_players, fake_player

from discord_extensions.status import Status
from discord_extensions import status


class TestStatus:
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
                "qlx_discordTriggerStatus": "status",
                "qlx_discordTriggeredChatMessagePrefix": "",
                "qlx_discordRelayChannelIds": "1234",
                "qlx_discordTriggeredChannelIds": "5678",
            }
        )

    def test_get_game_info_in_warmup(self, game_in_warmup):
        game_info = status.get_game_info(game_in_warmup)

        assert_that(game_info, equal_to("Warmup"))

    def test_get_game_info_in_countdown(self, game_in_countdown):
        game_info = status.get_game_info(game_in_countdown)

        assert_that(game_info, equal_to("Match starting"))

    def test_get_game_info_in_progress(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 1
        game_in_progress.blue_score = 2

        game_info = status.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match in progress: **1** - **2**"))

    def test_get_game_info_red_hit_roundlimit(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 8
        game_in_progress.blue_score = 2

        game_info = status.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **8** - **2**"))

    def test_get_game_info_blue_hit_roundlimit(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 8

        game_info = status.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **8**"))

    def test_get_game_info_red_player_dropped_out(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = -999
        game_in_progress.blue_score = 3

        game_info = status.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **-999** - **3**"))

    def test_get_game_info_blue_player_dropped_out(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 5
        game_in_progress.blue_score = -999

        game_info = status.get_game_info(game_in_progress)

        assert_that(game_info, equal_to("Match ended: **5** - **-999**"))

    def test_get_game_info_unknown_game_state(self, minqlx_game):
        minqlx_game.state = "unknown"
        minqlx_game.roundlimit = 8
        minqlx_game.red_score = 3
        minqlx_game.blue_score = 2

        game_info = status.get_game_info(minqlx_game)

        assert_that(game_info, equal_to("Warmup"))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_game_status_information_when_no_game_is_running(self):
        game_status = status.game_status_with_teams()

        assert_that(
            game_status,
            equal_to("Currently no game running."),
        )

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

        game_status = status.game_status_with_teams()

        assert_that(
            game_status,
            matches_regexp(
                r"Match in progress: .*5.* - .*3.* on .*Campgrounds.* \(CA\) with .*5/16.* players\. \n"
                r"\*\*R:\*\* \*\*RedPlayer1\*\*\(0\) \*\*RedPlayer2\*\*\(0\) \n"
                r"\*\*B:\*\* \*\*BluePlayer1\*\*\(0\) \*\*BluePlayer2\*\*\(0\) "
            ),
        )

    def test_game_status_information_with_spectators(self, game_in_progress):
        setup_cvars({"qlx_discord_ext_status_show_spectators": "1"})
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

        game_status = status.game_status_with_teams()

        assert_that(
            game_status,
            matches_regexp(
                r"Match in progress: .*5.* - .*3.* on .*Campgrounds.* \(CA\) with .*5/16.* players\. \n"
                r"\*\*R:\*\* \*\*RedPlayer1\*\*\(0\) \*\*RedPlayer2\*\*\(0\) \n"
                r"\*\*B:\*\* \*\*BluePlayer1\*\*\(0\) \*\*BluePlayer2\*\*\(0\) \n"
                r"\*\*S:\*\* \*\*SpecPlayer\*\*\(0\) "
            ),
        )

    def test_game_status_information_with_no_players(self, game_in_progress):
        connected_players()
        game_in_progress.maxclients = 16
        game_in_progress.map_title = "Campgrounds"
        game_in_progress.type_short = "ca"
        game_in_progress.red_score = 5
        game_in_progress.blue_score = 3

        game_status = status.game_status_with_teams()

        assert_that(
            game_status,
            matches_regexp(
                r"Match in progress: .*5.* - .*3.* on .*Campgrounds.* \(CA\) with .*0/16.* players\. "
            ),
        )

    @pytest.mark.parametrize(
        "channel_id,expected", [(1234, True), (5678, True), (42, False)]
    )
    def test_is_message_in_configured_triggered_or_relay_channel(
        self, channel_id, expected, context, bot, guild_channel
    ):
        extension = Status(bot)

        guild_channel.id = channel_id
        context.message = mock(spec=Message)
        context.message.channel = guild_channel

        assert_that(
            extension.is_message_in_relay_or_triggered_channel(context),
            equal_to(expected),
        )

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("no_minqlx_game")
    async def test_trigger_status(self, bot, context, triggered_channel):
        extension = Status(bot)

        context.message = mock(spec=Message)
        context.message.channel = triggered_channel

        await extension.trigger_status(context)

        context.reply.assert_awaited_once_with(" Currently no game running.")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("no_minqlx_game")
    async def test_slash_trigger_status(self, bot, interaction, triggered_channel):
        extension = Status(bot)

        await extension.slash_trigger_status(interaction)

        interaction.response.send_message.assert_awaited_once_with(
            content="Currently no game running."
        )

    @pytest.mark.parametrize("channel_id,expected", [(1234, False), (5678, True)])
    def test_is_message_in_configured_triggered_channel(
        self, channel_id, expected, context, bot, guild_channel
    ):
        extension = Status(bot)

        guild_channel.id = channel_id
        context.message = mock(spec=Message)
        context.message.channel = guild_channel

        assert_that(
            extension.is_message_in_triggered_channel(context), equal_to(expected)
        )

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await status.setup(bot)

        bot.add_cog.assert_awaited_once()
        assert_that(isinstance(bot.add_cog.call_args.args[0], Status), equal_to(True))
