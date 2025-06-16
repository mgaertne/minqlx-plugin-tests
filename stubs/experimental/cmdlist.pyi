from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import Player, AbstractChannel

# noinspection PyPep8Naming
class cmdlist(Plugin):
    def __init__(self) -> None: ...
    def cmd_cmdlist(self, player: Player, _msg: list[str], _channel: AbstractChannel) -> None: ...
    def thread_reply(self, player: Player) -> None: ...
