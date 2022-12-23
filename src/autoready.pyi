from datetime import datetime
from threading import RLock, Thread

from typing import Callable, Iterator, Sequence, TypeVar, Generic, Iterable, Optional

from minqlx import Plugin, Player

THIRTY_SECOND_WARNINGS: Sequence[str]


T = TypeVar('T')
class RandomIterator(Generic[T]):
    seq: Sequence[T]
    random_seq: Sequence[T]
    iterator: Iterator[T]

    def __init__(self, seq: Sequence[T]) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def __next__(self) -> T: ...


class CountdownThread(Thread):
    duration: int
    _target_time: datetime | None
    _remaining: int
    _lock: RLock
    timed_actions: dict[int, Callable[[int], None]]
    _now: datetime | None

    def __init__(self, duration: int, *, timed_actions: dict[int, Callable[[int], None]]): ...
    @property
    def seconds_left(self) -> int: ...
    def stop(self) -> None: ...
    def run(self) -> None: ...
    def run_loop_step(self) -> None: ...
    def _determine_now(self) -> datetime: ...
    def calculate_target_time(self) -> datetime: ...
    def determine_timed_action_for_remaining_seconds(self, remaining: int) -> Callable[[int], None]: ...


# noinspection PyPep8Naming
class autoready(Plugin):
    min_players: int
    autostart_delay: int
    min_counter: int
    timer_visible: int
    disable_player_ready: bool
    timer: CountdownThread | None
    current_timer: int
    timer_lock: RLock
    announcer: RandomIterator[str]

    def __init__(self) -> None: ...
    def handle_client_command(self, _player: Player, command: str) -> bool: ...
    def handle_map_change(self, _mapname: str, _factory: str) -> None: ...
    def handle_team_switch(self, _player: Player, _old_team: str, new_team: str) -> None: ...
    def timed_actions(self) -> dict[int, Callable[[int], None]]: ...
    def handle_game_countdown(self) -> None: ...
    def make_sure_game_really_starts(self, mapname: str) -> None: ...
    def handle_game_start(self, _data: dict) -> None: ...
    def handle_player_disconnect(self, _player: Player, _reason: str) -> None: ...


def display_countdown(remaining: int) -> None: ...
def blink(remaining: int, *, sleep: float = ...) -> None: ...
def warning_blink(remaining: int, announcer_sound: str, *, sleep: float = ...) -> None: ...
def double_blink(remaining: int, *, sleep: float = ..., _delay: float = ...) -> None: ...
def shuffle_double_blink(remaining: int, *, sleep: float = ..., _delay: float = ...) -> None: ...
def wear_off_double_blink(remaining: int, *, sleep: float = ..., _delay: float = ...) -> None: ...
def allready(_remaining: int) -> None: ...
