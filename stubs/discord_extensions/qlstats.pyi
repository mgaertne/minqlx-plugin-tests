# noinspection PyPackageRequirements
from discord import Interaction as Interaction, Member as Member, User as User

# noinspection PyPackageRequirements
from discord.ext.commands import Bot as Bot

async def qlstats(interaction: Interaction, _item: Member | User) -> None: ...
async def setup(bot: Bot): ...
