from datetime import datetime

from minqlx import AbstractChannel, Player, Plugin
from typing import Callable, NamedTuple

SteamId = int

class Position(NamedTuple):
    x: int
    y: int
    z: int

def calculate_distance(previous: Position, current: Position) -> float: ...
def format_float(value: float) -> str: ...
def format_int(value: int) -> str: ...
def convert_units_to_meters(units: float) -> float: ...
def determine_means_of_death(means_of_death: str) -> str: ...

class WeaponStats(NamedTuple):
    name: str
    deaths: int
    damage_dealt: int
    damage_taken: int
    hits: int
    kills: int
    pickups: int
    shots: int
    time: int
    @property
    def accuracy(self) -> float: ...
    @property
    def shortname(self) -> str: ...

class Damage(NamedTuple):
    dealt: int
    taken: int

class Medals(NamedTuple):
    accuracy: int
    assists: int
    captures: int
    combokill: int
    defends: int
    excellent: int
    firstfrag: int
    headshot: int
    humiliation: int
    impressive: int
    midair: int
    perfect: int
    perforated: int
    quadgod: int
    rampage: int
    revenge: int

class Pickups(NamedTuple):
    ammo: int
    armor: int
    armor_regen: int
    battlesuit: int
    doubler: int
    flight: int
    green_armor: int
    guard: int
    haste: int
    health: int
    invisibility: int
    invulnerability: int
    kamikaze: int
    medkit: int
    mega_health: int
    other_holdable: int
    other_powerup: int
    portal: int
    quad: int
    red_armor: int
    regeneration: int
    scout: int
    teleporter: int
    yellow_armor: int

class Weapons(NamedTuple):
    machinegun: WeaponStats
    shotgun: WeaponStats
    grenade_launcher: WeaponStats
    rocket_launcher: WeaponStats
    lightninggun: WeaponStats
    railgun: WeaponStats
    plasmagun: WeaponStats
    hmg: WeaponStats
    bfg: WeaponStats
    gauntlet: WeaponStats
    nailgun: WeaponStats
    proximity_mine_launcher: WeaponStats
    chaingun: WeaponStats
    other: WeaponStats

class PlayerStatsEntry:
    stats_data: list[dict]
    def __init__(self, stats_data: dict) -> None: ...
    def _sum_entries(self, entry: str) -> int: ...
    def _sum_weapon(self, weapon_name: str) -> WeaponStats: ...
    @property
    def steam_id(self) -> SteamId: ...
    @property
    def aborted(self) -> bool: ...
    @property
    def blue_flag_pickups(self) -> int: ...
    @property
    def damage(self) -> Damage: ...
    @property
    def deaths(self) -> int: ...
    @property
    def holy_shits(self) -> int: ...
    @property
    def kills(self) -> int: ...
    @property
    def lose(self) -> int: ...
    @property
    def match_guid(self) -> int: ...
    @property
    def max_streak(self) -> int: ...
    @property
    def medals(self) -> Medals: ...
    @property
    def model(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def neutral_flag_pickups(self) -> int: ...
    @property
    def pickups(self) -> Pickups: ...
    @property
    def play_time(self) -> int: ...
    @property
    def quit(self) -> int: ...
    @property
    def red_flag_pickups(self) -> int: ...
    @property
    def score(self) -> int: ...
    @property
    def warmup(self) -> bool: ...
    @property
    def weapons(self) -> Weapons: ...
    @property
    def win(self) -> int: ...
    def combine(self, other: object) -> None: ...

def filter_stats_for_max_value(
    stats: list[PlayerStatsEntry], func: Callable[[PlayerStatsEntry], bool]
) -> list[PlayerStatsEntry]: ...
def most_weapon_hits_announcement(stats: list[PlayerStatsEntry]) -> str | None: ...
def most_accurate_railbitches_announcement(
    stats: list[PlayerStatsEntry],
) -> str | None: ...
def longest_shaftlamers_announcement(stats: list[PlayerStatsEntry]) -> str | None: ...
def most_honorable_haste_pickup_announcement(
    stats: list[PlayerStatsEntry],
) -> str | None: ...
def weird_facts(stats: list[PlayerStatsEntry]) -> str | None: ...
def random_conjunction() -> str: ...
def random_medal_facts(stats: list[PlayerStatsEntry], *, count: int = ...) -> list[str]: ...
def formatted_medal_fact(stats: list[PlayerStatsEntry], medal_stat: str) -> str: ...

WEAPON_FACTS_LOOKUP: dict[str, dict[str, list[str]]]

def format_weapon_fact(weapon_stat: str, player_names: str, weapon_name: str, stats_amount: int) -> str: ...
def random_weapon_stats(stats: list[PlayerStatsEntry], *, count: int = ...) -> list[str]: ...
def formatted_weapon_fact(stats: list[PlayerStatsEntry], weapon: str, weapon_fact: str) -> str: ...

LAST_USED_NAME_KEY: str
PLAYER_TOP_SPEEDS: str
MAP_TOP_SPEEDS: str
MAP_SPEED_LOG: str

# noinspection PyPep8Naming
class weird_stats(Plugin):
    stats_play_time_fraction: float
    stats_top_display: int
    fastestmaps_display_ingame: int
    fastestmaps_display_warmup: int
    game_start_time: datetime | None
    join_times: dict[SteamId, datetime]
    play_times: dict[SteamId, float]
    in_round: bool
    game_ended: bool
    match_end_announced: bool
    means_of_death: dict[SteamId, dict[str, int]]
    round_start_datetime: datetime | None
    fastest_death: tuple[SteamId, float]
    alive_times: dict[SteamId, float]
    previous_positions: dict[SteamId, Position]
    travelled_distances: dict[SteamId, float]
    player_stats: dict[SteamId, PlayerStatsEntry]
    playerstats_announcements: list[Callable[[list[PlayerStatsEntry]], str | None]]

    def __init__(self) -> None: ...
    def handle_team_switch(self, player: Player, old_team: str, new_team: str) -> None: ...
    def handle_player_disconnect(self, player: Player, _reason: str) -> None: ...
    def handle_frame(self) -> None: ...
    def calculate_player_distance(self, player: Player) -> float: ...
    def handle_game_countdown(self) -> None: ...
    def reinitialize_game(self) -> None: ...
    def handle_game_start(self, _data: dict) -> None: ...
    def handle_round_start(self, _round_number: int) -> None: ...
    def handle_death(self, victim: Player, killer: Player, data: dict) -> None: ...
    def record_means_of_death(self, victim: Player, killer: Player, means_of_death: str) -> None: ...
    def record_alive_time(self, *players: Player) -> None: ...
    def handle_round_end(self, _data: dict) -> None: ...
    def handle_game_end(self, _data: dict) -> None: ...
    def handle_stats(self, stats: dict) -> None: ...
    def announce_match_end_stats(self) -> None: ...
    def stats_from_all_players_collected(self) -> bool: ...
    def player_speeds_announcements(
        self, *, top_entries: int = ..., match_end_announcements: bool = ...
    ) -> list[str]: ...
    def determine_current_play_times(self) -> dict[SteamId, float]: ...
    def determine_player_speeds(self) -> dict[SteamId, float]: ...
    def quickest_deaths(self) -> str: ...
    def environmental_deaths(
        self,
        means_of_death: dict[SteamId, dict[str, int]],
        means_of_death_filter: list[str],
    ) -> str: ...
    def record_speeds(self, mapname: str, speeds: dict[SteamId, float]) -> None: ...
    def record_personal_speed(self, mapname: str, steam_id: SteamId, speed: float) -> None: ...
    def cmd_player_speeds(self, _player: Player, _msg: str, _channel: AbstractChannel) -> None: ...
    def cmd_player_top_speeds(self, player: Player, msg: str, channel: AbstractChannel) -> None: ...
    @staticmethod
    def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel: ...
    def identify_target(self, player: Player, target: str | int | Player) -> tuple[str | None, SteamId | None]: ...
    def find_target_player_or_list_alternatives(self, player: Player, target: str | int) -> Player | None: ...
    def resolve_player_name(self, item: int | str) -> str: ...
    def collect_and_report_player_top_speeds(self, channel: AbstractChannel, steam_id: int) -> None: ...
    def db_get_top_speed_for_player(self, steam_id: int) -> list[tuple[str, float]]: ...
    def cmd_map_top_speeds(self, _player: Player, msg: str, channel: AbstractChannel) -> None: ...
    def collect_and_report_map_top_speeds(self, channel: AbstractChannel, mapname: str) -> None: ...
    def cmd_fastest_maps(self, _player: Player, _msg: str, channel: AbstractChannel) -> None: ...
    def collect_and_report_fastest_maps(self, channel: AbstractChannel) -> None: ...
    def map_speed_log(self, mapname: str) -> list[tuple[int, float]]: ...
    def alive_time_of(self, steam_id: SteamId) -> float: ...
