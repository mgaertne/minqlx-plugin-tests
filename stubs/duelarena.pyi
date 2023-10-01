from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from minqlx import (
        Player,
        AbstractChannel,
        Game,
        CancellableEventReturn,
        RoundEndData,
        GameEndData,
    )

MIN_ACTIVE_PLAYERS: int
MAX_ACTIVE_PLAYERS: int

DUELARENA_JOIN_CMD: tuple[str, ...]
DUELARENA_JOIN_MSG: str

# noinspection PyPep8Naming
class duelarena(Plugin):
    duelarena_game: DuelArenaGame
    def __init__(self) -> None: ...
    def handle_map_change(self, _smapname: str, _factory: str) -> None: ...
    def handle_player_loaded(self, player: Player) -> None: ...
    def handle_team_switch_event(
        self, player: Player, _old: str, new: str
    ) -> CancellableEventReturn: ...
    def handle_player_disconnect(self, player: Player, _reason: str) -> None: ...
    def handle_game_countdown(self) -> None: ...
    def handle_round_countdown(self, _round_number: int) -> None: ...
    def ensure_duel_players(self) -> None: ...
    def handle_round_end(self, data: RoundEndData) -> None: ...
    @staticmethod
    def determine_winning_team(data: RoundEndData) -> str: ...
    @staticmethod
    def other_team(team: str) -> str | None: ...
    def handle_game_end(self, data: GameEndData) -> None: ...
    def cmd_join(
        self, player: Player, _msg: list[str], _channel: AbstractChannel
    ) -> None: ...

SteamId = int

class DuelArenaGame:
    duelmode: bool
    initduel: bool
    playerset: list[SteamId]
    queue: list[SteamId]
    player_red: SteamId | None
    player_blue: SteamId | None
    player_spec: list[SteamId]
    scores: dict[SteamId, int]
    print_reset_scores: bool
    duel_to_normal_threshold: int
    normal_to_duel_threshold: int
    duel_to_normal_score_reset: str

    def __init__(self) -> None: ...
    @property
    def game(self) -> Game | None: ...
    def add_player(self, player_sid: SteamId) -> None: ...
    def remove_player(self, player_sid: SteamId) -> None: ...
    def should_emergency_replace_player(self, player_sid: SteamId) -> bool: ...
    def next_player_sid(self) -> SteamId | None: ...
    def is_player(self, steam_id: SteamId) -> bool: ...
    def check_for_activation_or_abortion(self) -> None: ...
    def activate(self) -> None: ...
    def announce_activation(self) -> None: ...
    def should_be_activated(self) -> bool: ...
    def is_activated(self) -> bool: ...
    def deactivate(self) -> None: ...
    def announce_deactivation(self) -> None: ...
    def should_be_aborted(self) -> bool: ...
    def reset(self) -> None: ...
    def init_duel(self, winner_sid: SteamId | None = ...) -> None: ...
    def determine_initial_players(
        self, winner_sid: SteamId | None = ...
    ) -> tuple[SteamId, SteamId]: ...
    def put_players_on_the_right_teams(
        self, red_sid: SteamId, blue_sid: SteamId
    ) -> None: ...
    def put_active_players_on_the_right_teams(
        self, red_sid: SteamId, blue_sid: SteamId
    ) -> None: ...
    def ensure_duelarena_players(self) -> None: ...
    def init_scores(self) -> None: ...
    def is_pending_initialization(self) -> bool: ...
    def validate_players(self) -> None: ...
    @staticmethod
    def player_is_still_with_us(steam_id: SteamId) -> bool: ...
    def record_scores(self, red_score: int, blue_score: int) -> None: ...
    def exchange_player(self, losing_team: str) -> None: ...
    def insert_next_player(self, team: str) -> None: ...
    def announce_next_round(self) -> None: ...
    def should_print_and_reset_scores(self) -> bool: ...
    def print_and_reset_scores(self) -> None: ...
    def print_results(self) -> None: ...
    def reset_duelarena_scores(self) -> None: ...
    def reset_team_scores(self) -> None: ...
