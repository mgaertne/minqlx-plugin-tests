from typing import TYPE_CHECKING
from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import AbstractChannel, Player

# noinspection PyPep8Naming
class uptime(Plugin):
    def __init__(self) -> None: ...
    def cmd_uptime(
        self, _player: Player, _msg: list[str], _channel: AbstractChannel
    ) -> None: ...
