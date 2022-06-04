# noinspection PyPackageRequirements
from discord import app_commands, Interaction, Member
# noinspection PyPackageRequirements
from discord.ext.commands import Bot


@app_commands.context_menu(name="slap")
@app_commands.guild_only()
async def slap(interaction: Interaction, member: Member):
    await interaction.response.send_message(f"_{interaction.user.mention} slaps {member.mention} with a large trout._")


async def setup(bot: Bot):
    bot.tree.add_command(slap)
    await bot.tree.sync()
