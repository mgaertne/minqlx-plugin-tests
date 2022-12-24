from minqlx import Plugin, AbstractChannel, Player

game_settings: dict[str, dict[str, str]]

# noinspection PyPep8Naming
class custom_modes_vote(Plugin):
    default_mode: str
    mode: str

    def __init__(self) -> None: ...
    def available_modes(self) -> set[str]: ...
    def handle_map_change(self, _mapname: str, _factory: str) -> None: ...
    def handle_vote_called(self, caller: Player, vote: str, args: str) -> int: ...
    def handle_vote_ended(
        self, _votes: tuple[int, int], vote: str, args: str, passed: bool
    ) -> None: ...
    def cmd_switch_mode(
        self, _player: Player, msg: str, _channel: AbstractChannel
    ) -> int: ...
    def switch_mode(self, mode: str) -> None: ...