import datetime
import os
import platform

import distro
import psutil
import humanize

from minqlx import Plugin
import minqlx


# noinspection PyPep8Naming
class uptime(Plugin):
    def __init__(self):
        super().__init__()

        self.add_command("uptime", self.cmd_uptime)

    def cmd_uptime(self, _player, _msg, _channel):
        now = datetime.datetime.now()
        lsb_info = distro.lsb_release_info()
        os_boottime = datetime.datetime.fromtimestamp(psutil.boot_time())
        os_uptime = humanize.precisedelta(
            now - os_boottime, minimum_unit="minutes", format="%d"
        )

        myself_process = psutil.Process(os.getpid())
        qlserver_starttime = datetime.datetime.fromtimestamp(
            myself_process.create_time()
        )
        qlserver_uptime = humanize.precisedelta(
            now - qlserver_starttime, minimum_unit="minutes", format="%d"
        )

        minqlx_version = str(minqlx.__version__)[1:-1]

        self.msg(
            f"^6Operating system^7: ^5{lsb_info['description']}^7, ^6uptime^7: ^5{os_uptime}^7"
        )
        self.msg(
            f"^6Quake Live server^7 running with ^5minqlx {minqlx_version}^7 "
            f"(Python {platform.python_version()}) ^6uptime: ^5{qlserver_uptime}^7"
        )
