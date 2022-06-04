from typing import Union

# noinspection PyPackageRequirements
from discord import Interaction, Member, User, Embed, Color
# noinspection PyPackageRequirements
from discord.ext.commands import Bot
# noinspection PyPackageRequirements
from discord import app_commands

from minqlx import Plugin


@app_commands.context_menu(name="qlstats")
@app_commands.guild_only()
async def qlstats(interaction: Interaction, _item: Union[Member, User]) -> None:
    embed = Embed(color=Color.blurple())
    url = Plugin.get_cvar("qlx_discord_ext_qlstats_url")
    embed.url = url
    embed.title = "QL stats page"
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: Bot):
    bot.tree.add_command(qlstats)
    await bot.tree.sync()
