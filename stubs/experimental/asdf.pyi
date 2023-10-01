from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import (
        AbstractChannel,
        Player,
        RoundEndData,
        StatsData,
        PlayerStatsStats,
    )

SteamId = int

WEAPON_STATS_KEY: str

def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel: ...

# noinspection PyPep8Naming
class asdf(Plugin):
    stats_snapshot: dict[SteamId, int]
    red_overall_damage: int
    blue_overall_damage: int
    min_ammo_rate: float
    def __init__(self) -> None: ...
    def handle_player_spawn(self, player: Player) -> None: ...
    def adjust_ammo_for_player(self, player: Player) -> None: ...
    def handle_stats(self, stats: StatsData) -> None: ...
    def store_weapon_stats(self, stats: PlayerStatsStats) -> None: ...
    def handle_game_countdown(self) -> None: ...
    def handle_round_start(self, _round_number: int) -> None: ...
    def handle_round_end(self, _data: RoundEndData) -> None: ...
    def calculate_team_round_damages(self) -> None: ...
    def calculate_damage_deltas(self) -> dict[SteamId, int]: ...
    def cmd_weaponstats(
        self, player: Player, msg: list[str], channel: AbstractChannel
    ) -> None: ...
    def weapon_stats_for(self, steam_id: SteamId) -> dict[str, WeaponStatsEntry]: ...
    def identify_target(
        self, player: Player, target: SteamId | str | Player
    ) -> tuple[str | None, SteamId | None]: ...
    def resolve_player_name(self, item: SteamId | str) -> str: ...
    def find_target_player_or_list_alternatives(
        self, player: Player, target: int | str
    ) -> Player | None: ...

class Weapon:
    name: str
    def __init__(self, name: str) -> None: ...
    def weapon_name(self) -> str: ...
    def ammo_type(self) -> str: ...

class WeaponStatsEntry:
    weapon: Weapon
    kills: int
    deaths: int
    damage_dealt: int
    damage_received: int
    shots: int
    hits: int
    pickups: int
    time: int
    def __init__(
        self,
        weapon: Weapon,
        kills: int,
        deaths: int,
        damage_dealt: int,
        damage_received: int,
        shots: int,
        hits: int,
        pickups: int,
        time: int,
    ) -> None: ...
    def accuracy(self) -> float: ...
    @property
    def name(self) -> str: ...
