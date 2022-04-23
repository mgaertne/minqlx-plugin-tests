from datetime import datetime, timedelta
from functools import partial

import random
import time

from threading import RLock, Thread

from typing import Optional, Callable, Iterator, Sequence, TypeVar

from minqlx import Plugin, Player  # type: ignore


THIRTY_SECOND_WARNINGS = [
    "sound/vo/30_second_warning.ogg",
    "sound/vo_female/30_second_warning.ogg",
    "sound/vo_evil/30_second_warning.ogg"
]


# noinspection PyPep8Naming
class autoready(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_autoready_min_players", "10")
        self.set_cvar_once("qlx_autoready_autostart_delay", "180")
        self.set_cvar_once("qlx_autoready_min_seconds", "30")
        self.set_cvar_once("qlx_autoready_timer_visible", "60")
        self.set_cvar_once("qlx_autoready_disable_manual_readyup", "0")

        self.min_players: int = self.get_cvar("qlx_autoready_min_players", int)
        self.autostart_delay: int = self.get_cvar("qlx_autoready_autostart_delay", int)
        self.min_counter: int = self.get_cvar("qlx_autoready_min_seconds", int)
        self.timer_visible: int = self.get_cvar("qlx_autoready_timer_visible", int)
        self.disable_player_ready: bool = self.get_cvar("qlx_autoready_disable_manual_readyup", bool)

        self.timer: Optional[CountdownThread] = None
        self.current_timer: int = -1
        self.timer_lock: RLock = RLock()

        self.announcer: RandomIterator = RandomIterator(THIRTY_SECOND_WARNINGS)

        self.add_hook("client_command", self.handle_client_command)
        self.add_hook("map", self.handle_map_change)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("player_disconnect", self.handle_player_disconnect)

    def handle_client_command(self, _player: Player, command: str) -> bool:
        if len(self.players()) < self.min_players:
            return True

        if self.disable_player_ready and command == "readyup":
            return False

        return True

    def handle_map_change(self, _mapname: str, _factory: str) -> None:
        if self.timer is None or not self.timer.is_alive():
            self.current_timer = -1
            return

        self.timer.stop()
        self.current_timer = self.timer.seconds_left

    def handle_team_switch(self, _player: Player, _old_team: str, new_team: str) -> None:
        if not self.game:
            return

        if self.game.state != "warmup":
            return

        if new_team not in ["red", "blue"]:
            return

        current_player_count = len(self.players())

        if current_player_count < self.min_players:
            return

        if self.timer is not None and self.timer.is_alive():
            return

        if self.current_timer != -1:
            self.current_timer = max(self.current_timer, self.min_counter)
        else:
            self.current_timer = self.autostart_delay

        self.timer = CountdownThread(self.current_timer, timed_actions=self.timed_actions())
        self.timer.start()

    def timed_actions(self) -> dict[int, Callable[[int], None]]:
        return {
            self.timer_visible: lambda _: None,
            31: display_countdown,
            30: partial(warning_blink, announcer_sound=next(self.announcer)),
            11: blink,
            10: shuffle_double_blink,
            6: double_blink,
            1: wear_off_double_blink,
            0: allready
        }

    def handle_game_countdown(self) -> None:
        if self.timer is None:
            return

        with self.timer_lock:
            self.timer.stop()
            self.current_timer = -1
            self.timer = None

    def handle_player_disconnect(self, _player: Player, _reason: str) -> None:
        if not self.game:
            return

        if self.game.state != "warmup":
            return

        if len(self.players()) < self.min_players:
            if self.timer is not None and self.timer.is_alive():
                self.timer.stop()
                self.timer = None
            self.current_timer = -1


class CountdownThread(Thread):
    def __init__(self, duration: int, *, timed_actions: dict[int, Callable[[int], None]]):
        super().__init__()
        self.duration: int = duration
        self._target_time: Optional[datetime] = None
        self._remaining: int = -1
        self._lock: RLock = RLock()
        self.timed_actions: dict[int, Callable[[int], None]] = {
            duration: timed_actions[duration] for duration in sorted(timed_actions.keys(), reverse=True)
        }
        self._now: Optional[datetime] = None

    @property
    def seconds_left(self) -> int:
        if self._remaining != -1:
            return self._remaining

        if self._target_time is None:
            return self.duration

        return int((self._target_time - self._determine_now()).total_seconds())

    def stop(self):
        if not self.is_alive():
            return

        if self._target_time is None:
            return

        with self._lock:
            self._remaining = max(
                int((self._target_time - self._determine_now()).total_seconds()),
                0)

    def run(self):
        self._target_time = self.calculate_target_time()

        while self._remaining == -1 and self._target_time > self._determine_now():
            self.run_loop_step()

    def run_loop_step(self):
        if self._target_time is None:
            return

        remaining = int((self._target_time - self._determine_now()).total_seconds())

        remaining_function: Callable[[int], None] = self.determine_timed_action_for_remaining_seconds(remaining)
        remaining_function(remaining)

        sleep_delay = self._target_time - timedelta(seconds=remaining) - self._determine_now()
        time.sleep(sleep_delay.total_seconds())

    def _determine_now(self) -> datetime:
        if self._now is not None:
            return self._now
        return datetime.now()

    def calculate_target_time(self) -> datetime:
        return self._determine_now() + timedelta(seconds=self.duration)

    def determine_timed_action_for_remaining_seconds(self, remaining: int) -> Callable[[int], None]:
        for duration, action in self.timed_actions.items():
            if remaining >= duration:
                return action
        return lambda _: None


def display_countdown(remaining: int) -> None:
    time_color_format = "^1" if remaining <= 30 else "^3"
    remaining_minutes, remaining_seconds = divmod(remaining, 60)
    Plugin.center_print(f"Match will ^2auto-start^7 in\n"
                        f"{time_color_format}{int(remaining_minutes):01}^7:"
                        f"{time_color_format}{int(remaining_seconds):02}")


def blink(remaining: int, *, sleep: float = 0.4) -> None:
    Plugin.center_print("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
    time.sleep(sleep)
    display_countdown(remaining)


def warning_blink(remaining: int, announcer_sound: str, *, sleep: float = 0.4) -> None:
    Plugin.play_sound(announcer_sound)
    blink(remaining, sleep=sleep)


def double_blink(remaining: int, *, sleep: float = 0.2, _delay: float = 0.3) -> None:
    blink(remaining, sleep=sleep)
    time.sleep(_delay)
    blink(remaining, sleep=sleep)


def shuffle_double_blink(remaining: int, *, sleep: float = 0.2, _delay: float = 0.3) -> None:
    teams = Plugin.teams()
    if abs(len(teams["red"]) - len(teams["blue"])) > 1:
        Plugin.shuffle()
    double_blink(remaining, sleep=sleep, _delay=0.3)


def wear_off_double_blink(remaining: int, *, sleep: float = 0.2, _delay: float = 0.3) -> None:
    Plugin.play_sound("sound/items/wearoff.ogg")
    double_blink(remaining, sleep=sleep, _delay=_delay)


def allready(_remaining: int) -> None:
    Plugin.center_print("Match will ^2auto-start^7 in\n^20^7:^200")
    Plugin.allready()


T = TypeVar('T')


class RandomIterator:
    def __init__(self, seq: Sequence[T]):
        self.seq = seq
        self.random_seq = random.sample(self.seq, len(self.seq))
        self.iterator = iter(self.random_seq)

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        try:
            return next(self.iterator)
        except StopIteration:
            self.random_seq = random.sample(self.seq, len(self.seq))
            self.iterator = iter(self.random_seq)
            return next(self.iterator)
