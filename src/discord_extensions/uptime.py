import datetime
import os
import platform
from typing import Union

import distro
import humanize
import psutil

# noinspection PyPackageRequirements
from discord import Member, User, Embed, Color

# noinspection PyPackageRequirements
from discord import app_commands

import minqlx
from minqlx import Plugin


@app_commands.context_menu(name="uptime")
@app_commands.guild_only()
async def uptime(interaction, _item: Union[Member, User]):
    await _uptime(interaction)


async def _uptime(interaction):
    now = datetime.datetime.now()
    lsb_info = distro.lsb_release_info()
    os_boottime = datetime.datetime.fromtimestamp(psutil.boot_time())
    os_uptime = humanize.precisedelta(
        now - os_boottime, minimum_unit="minutes", format="%d"
    )

    myself_process = psutil.Process(os.getpid())
    qlserver_starttime = datetime.datetime.fromtimestamp(myself_process.create_time())
    qlserver_uptime = humanize.precisedelta(
        now - qlserver_starttime, minimum_unit="minutes", format="%d"
    )

    minqlx_version = str(minqlx.__version__)[1:-1]

    embed = Embed(color=Color.blurple())
    title = Plugin.get_cvar("sv_hostname")
    embed.title = title
    embed.description = (
        f"Operating system: {lsb_info['description']}, uptime: {os_uptime}\n"
        f"Quake Live server running with minqlx {minqlx_version} (Python {platform.python_version()}) "
        f"uptime: {qlserver_uptime}"
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    bot.tree.add_command(uptime)
