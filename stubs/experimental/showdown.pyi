from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from typing import Iterator, Callable, Generic, TypeVar, Sequence

    from minqlx import Player, AbstractChannel

SteamId = int

LAST_STANDING_LOG: str

# noinspection PyPep8Naming
class showdown(Plugin):
    vote_showdown: bool
    vote_showdown_teamsize: int
    min_opp: int
    max_opp: int
    showdown_random_weapons: list[str]
    random_weapons_iter: Iterator[str]
    showdown_overwrite_permission_level: int
    between_rounds: bool
    last_standing_steam_id: SteamId | None
    last_standing_time: float | None
    showdown_skipped_this_round: bool
    showdown_activated: bool
    showdown_weapon: Weapon | None
    weapons_taken: int | None
    showdown_is_counting_down: bool
    music_started: bool
    showdown_votes: dict[str, list[SteamId]] | None

    def __init__(self) -> None: ...
    def handle_switch(self, _player: Player, _old: str, _new: str) -> None: ...
    def detect(self) -> None: ...
    def handle_automatic_showdown(
        self, alive_r: list[Player], alive_b: list[Player]
    ) -> None: ...
    def callvote_showdown(self) -> None: ...
    def should_allow_automatic_showdown(self) -> bool: ...
    def alive_players(self, players: list[Player]) -> list[Player]: ...
    def should_reactivate_normal_game(
        self, alive_r: list[Player], alive_b: list[Player]
    ) -> bool: ...
    def reactivate_normal_game(self) -> None: ...
    def blink(
        self,
        messages: list[str],
        interval: float = ...,
        sound: str | None = ...,
        callback: Callable[[], None] | None = ...,
    ) -> None: ...
    def restore_original_weapons(self) -> None: ...
    def should_activate_gauntlet_showdown(
        self, alive_r: list[Player], alive_b: list[Player]
    ) -> bool: ...
    def should_skip_automatic_showdown_this_round(
        self, alive_r: list[Player], alive_b: list[Player]
    ) -> int: ...
    def activate_showdown(
        self, alive_r: list[Player], alive_b: list[Player], showdown_weapon: str = ...
    ) -> None: ...
    def start_showdown(self) -> None: ...
    def allow_music(self) -> bool: ...
    def announce_player_died(
        self, alive_r: list[Player], alive_b: list[Player]
    ) -> None: ...
    def other_team(self, team: str) -> str: ...
    def handle_death(
        self, _victim: Player, _killer: Player | None, _data: dict
    ) -> None: ...
    def handle_round_start(self, _round_number: int) -> None: ...
    def handle_round_end(self, _data: dict) -> None: ...
    def cmd_showdown(
        self, player: Player, msg: str, _channel: AbstractChannel
    ) -> None: ...
    def is_player_eligible_to_trigger_showdown(self, player: Player) -> bool: ...
    def is_showdown_trigger_attempt(self, player: Player, msg: str) -> bool: ...
    def punish_last_standing_player(self) -> None: ...
    def weapon_showdown(self, preselected_weapon: str | None = ...) -> None: ...
    def showdown_vote_text_for(self, voted_showdown: str) -> str | None: ...
    def evaluate_votes(self) -> None: ...

T = TypeVar("T")

# noinspection PyPep8Naming
class random_iterator(Generic[T]):
    seq: Sequence[T]
    random_seq: Sequence[T]
    iterator: Iterator[T]
    def __init__(self, seq: Sequence[T]) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def __next__(self) -> T: ...

class Weapon:
    ql_id: int
    shortname: str
    longname: str
    aliases: list[str]
    countdown_announcement: str
    start_announcement: str
    def __init__(
        self,
        ql_id: int,
        shortname: str,
        longname: str,
        aliases: list[str],
        countdown_announcement: str,
        start_announcement: str,
    ) -> None: ...
    def is_identified_by(self, text: str) -> bool: ...

ALL_WEAPONS: list[Weapon]
