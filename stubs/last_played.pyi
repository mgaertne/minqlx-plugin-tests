from typing import TYPE_CHECKING
from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import StatsData, GameEndData, PlayerStatsEntry, AbstractChannel, Player
    from minqlx.database import Redis

TIMESTAMP_FORMAT: str

# noinspection PyPep8Naming
class last_played(Plugin):
    database = Redis
    long_map_names_lookup: dict[str, str]
    def __init__(self) -> None: ...
    def handle_stats(self, data: StatsData) -> None: ...
    def log_played_map(self, data: GameEndData) -> None: ...
    def log_player_map(self, data: PlayerStatsEntry) -> None: ...
    def cmd_last_played(
        self, player: Player, msg: str, channel: AbstractChannel
    ) -> None: ...
