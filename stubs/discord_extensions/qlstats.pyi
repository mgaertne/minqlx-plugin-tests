from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from discord import Interaction, Member, User

    # noinspection PyPackageRequirements
    from discord.ext.commands import Bot

async def qlstats(interaction: Interaction, _item: Member | User) -> None: ...
async def _qlstats(interaction: Interaction) -> None: ...
async def setup(bot: Bot) -> None: ...
