import random

# noinspection PyPackageRequirements
from discord import app_commands, Interaction, Member
# noinspection PyPackageRequirements
from discord.ext.commands import Bot


@app_commands.context_menu(name="slap")
@app_commands.guild_only()
async def slap(interaction: Interaction, member: Member):
    if member.id == interaction.client.user.id:
        await interaction.response.send_message(f"_slaps {interaction.user.mention} with a large revenge trout._")

    if member.id == interaction.user.id:
        await interaction.response.send_message(f"_slaps {interaction.user.mention} slaps himself for his stupidity._")

    slaps = [
        f"_{interaction.user.mention} slaps {member.mention} with a large trout._",
        f"_{interaction.user.mention} slaps a large trout with {member.mention}._",
        f"_a large trout slaps {interaction.user.mention} with a {member.mention}._",
        f"_{interaction.user.mention} is trouted by {member.mention} with a large slap._",
        f"_{interaction.user.mention} gives {member.mention} a high five. In the face. With a chair._",
    ]

    await interaction.response.send_message(random.choice(slaps))


async def setup(bot: Bot):
    bot.tree.add_command(slap)
