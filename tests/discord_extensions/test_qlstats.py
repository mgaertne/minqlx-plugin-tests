import pytest

from discord_extensions import qlstats


class TestQLStats:
    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await qlstats.setup(bot)

        bot.tree.add_command.assert_called_once_with(qlstats.qlstats)
