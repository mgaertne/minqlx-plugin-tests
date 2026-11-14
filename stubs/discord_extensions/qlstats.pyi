from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from discord import Interaction

    # noinspection PyPackageRequirements
    from discord.app_commands import ContextMenu

    # noinspection PyPackageRequirements
    from discord.ext.commands import Bot

qlstats: ContextMenu

async def _qlstats(interaction: Interaction) -> None: ...
async def setup(bot: Bot) -> None: ...
