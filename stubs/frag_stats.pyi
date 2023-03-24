from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from typing import Sequence, Iterable

    from collections import Counter

    from minqlx import Player, AbstractChannel, DeathData

COLLECTED_SOULZ_KEY: str
REAPERZ_KEY: str
_name_key: str

SPECIAL_KILLERS: Iterable[str]

# noinspection PyPep8Naming
class frag_stats(Plugin):
    toplimit: int
    frag_log: list[tuple[int | str, int | str]]
    def __init__(self) -> None: ...
    def handle_player_disconnect(self, player: Player, _reason: str) -> None: ...
    def handle_game_countdown(self) -> None: ...
    def handle_death(
        self, victim: Player, killer: Player | None, data: DeathData
    ) -> None: ...
    def record_frag(self, recorded_killer: str | int, victim: str | int) -> None: ...
    def determine_killer(
        self, killer: Player | None, means_of_death: str
    ) -> int | str: ...
    def cmd_mapsoulz(
        self, player: Player, msg: list[str], channel: AbstractChannel
    ) -> None: ...
    def identify_target(
        self, player: Player, target: Player | str | int
    ) -> tuple[str | None, int | str | None]: ...
    def mapfrag_statistics_for(
        self, fragger_identifier: int | str | None
    ) -> Counter: ...
    def cmd_mapreaperz(
        self, player: Player, msg: list[str], channel: AbstractChannel
    ) -> None: ...
    def mapfraggers_of(self, fragged_identifier: int | str | None) -> Counter: ...
    def resolve_player_names(self, entries: Sequence[int | str]) -> Sequence[str]: ...
    def resolve_player_name(self, item: int | str) -> str: ...
    def find_target_player_or_list_alternatives(
        self, player: Player, target: str | int
    ) -> Player | None: ...
    def overall_frag_statistics_for(self, fragger_identifier: int | str) -> Counter: ...
    def overall_fraggers_of(self, fragger_identifier: int | str) -> Counter: ...
    def identify_reply_channel(self, channel: AbstractChannel) -> AbstractChannel: ...
    def cmd_soulzbalance(
        self, player: Player, msg: list[str], channel: AbstractChannel
    ) -> None: ...
    def report_top_soulzbalance(
        self, player: Player, channel: AbstractChannel
    ) -> None: ...
    def report_single_soulzbalance(
        self, player: Player, opponent: Player | str, channel: AbstractChannel
    ) -> None: ...
    def color_coded_balance_diff(self, balance_diff: int) -> str: ...
