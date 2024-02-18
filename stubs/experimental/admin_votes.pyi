from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import Player

# noinspection PyPep8Naming
class admin_votes(Plugin):
    mods_admins_voted: list[int]
    def __init__(self) -> None: ...
    def process_vote(self, player: Player, vote_yes_no: bool) -> int: ...
    def handle_vote_started(
        self, _player: Player, admin_votes: str, _args: str
    ) -> None: ...
