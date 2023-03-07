import pytest
from hamcrest import assert_that, equal_to

from minqlx_plugin_test import setup_cvars
from discord_extensions import qlstats


class TestQLStats:
    @pytest.mark.asyncio
    async def test_qlstats(self, interaction):
        setup_cvars({"qlx_discord_ext_qlstats_url": "https://qlstats.net/asdf"})

        await qlstats._qlstats(interaction)

        interaction.response.send_message.assert_awaited_once()
        assert_that(
            interaction.response.send_message.await_args.kwargs["ephemeral"],
            equal_to(True),
        )
        embed_kwarg = interaction.response.send_message.await_args.kwargs["embed"]
        assert_that(embed_kwarg.title, equal_to("QL stats page"))
        assert_that(embed_kwarg.url, equal_to("https://qlstats.net/asdf"))
        assert_that(
            interaction.response.send_message.await_args.kwargs["ephemeral"],
            equal_to(True),
        )

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await qlstats.setup(bot)

        bot.tree.add_command.assert_called_once_with(qlstats.qlstats)
