import random

# noinspection PyPackageRequirements
from discord import app_commands, PartialMessageable, Member

from minqlx import Plugin


@app_commands.context_menu(name="slap")
@app_commands.guild_only()
async def slap(interaction, member: Member):
    await _slap(interaction, member)


async def _slap(interaction, member):
    if interaction.client.user is None:
        await send_to_discord_and_quake(interaction, f"_{member.mention} is slapped from the hidden._")
        return

    if member.id == interaction.client.user.id:
        await send_to_discord_and_quake(
            interaction,
            f"_slaps {interaction.user.mention} with a large revenge trout._",
        )
        return

    if member.id == interaction.user.id:
        await send_to_discord_and_quake(
            interaction,
            f"_{interaction.user.mention} slaps himself for his stupidity._",
        )
        return

    slaps = [
        f"_{interaction.user.mention} slaps {member.mention} with a large trout._",
        f"_{interaction.user.mention} slaps a large trout with {member.mention}._",
        f"_a large trout slaps {member.mention} with a {interaction.user.mention}._",
        f"_{member.mention} is trouted by {interaction.user.mention} with a large slap._",
        f"_{interaction.user.mention} gives {member.mention} a high five. In the face. With a chair._",
    ]

    await send_to_discord_and_quake(interaction, random.choice(slaps))


def int_set(string_set):
    returned = set()  # type: ignore

    if string_set is None:
        return returned

    for item in string_set:
        if item == "":
            continue
        value = int(item)
        returned.add(value)

    return returned


async def send_to_discord_and_quake(interaction, message):
    await interaction.response.send_message(message)

    discord_relay_channel_ids = int_set(Plugin.get_cvar("qlx_discordRelayChannelIds", set))

    if interaction.channel_id not in discord_relay_channel_ids:
        return

    interaction_response = await interaction.original_response()
    quake_message = interaction_response.clean_content.lstrip("_").rstrip("_")

    show_channel_name = Plugin.get_cvar("qlx_displayChannelForDiscordRelayChannels", bool) or False
    discord_message_prefix = Plugin.get_cvar("qlx_discordMessagePrefix") or "[DISCORD]"
    if not show_channel_name or interaction.channel is None or isinstance(interaction.channel, PartialMessageable):
        Plugin.msg(f"{discord_message_prefix}^2 {quake_message}")
        return

    Plugin.msg(f"{discord_message_prefix} ^5#{interaction.channel.name}^7:^2 {quake_message}")


async def setup(bot):
    bot.tree.add_command(slap)
