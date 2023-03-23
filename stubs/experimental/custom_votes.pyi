from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import Player, CancellableEventReturn

# noinspection PyPep8Naming
class custom_votes(Plugin):
    def __init__(self) -> None: ...
    def handle_vote_called(
        self, caller: Player, vote: str, args: str | None
    ) -> CancellableEventReturn: ...
    def find_target_player_or_list_alternatives(
        self, player: Player, target: str
    ) -> Player | None: ...
