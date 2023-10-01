from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import AbstractChannel, Player, CancellableEventReturn

game_settings: dict[str, dict[str, str]]

# noinspection PyPep8Naming
class custom_modes_vote(Plugin):
    default_mode: str
    mode: str

    def __init__(self) -> None: ...
    def available_modes(self) -> set[str]: ...
    def handle_map_change(self, _mapname: str, _factory: str) -> None: ...
    def handle_vote_called(
        self, caller: Player, vote: str, args: str
    ) -> CancellableEventReturn: ...
    def handle_vote_ended(
        self, _votes: tuple[int, int], vote: str, args: str, passed: bool
    ) -> None: ...
    def cmd_switch_mode(
        self, _player: Player, msg: list[str], _channel: AbstractChannel
    ) -> int: ...
    def switch_mode(self, mode: str) -> None: ...
