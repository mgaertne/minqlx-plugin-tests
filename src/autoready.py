from datetime import datetime, timedelta
from functools import partial

import random
import time

from threading import RLock, Thread

import minqlx
from minqlx import Plugin

THIRTY_SECOND_WARNINGS = [
    "sound/vo/30_second_warning.ogg",
    "sound/vo_female/30_second_warning.ogg",
    "sound/vo_evil/30_second_warning.ogg"
]


# noinspection PyPep8Naming
class autoready(Plugin):
    def __init__(self) -> None:
        super().__init__()

        self.set_cvar_once("qlx_autoready_min_players", "10")
        self.set_cvar_once("qlx_autoready_autostart_delay", "180")
        self.set_cvar_once("qlx_autoready_min_seconds", "30")
        self.set_cvar_once("qlx_autoready_timer_visible", "60")
        self.set_cvar_once("qlx_autoready_disable_manual_readyup", "0")

        self.min_players = self.get_cvar("qlx_autoready_min_players", int) or 10
        self.autostart_delay = self.get_cvar("qlx_autoready_autostart_delay", int) or 180
        self.min_counter = self.get_cvar("qlx_autoready_min_seconds", int) or 30
        self.timer_visible = self.get_cvar("qlx_autoready_timer_visible", int) or 60
        self.disable_player_ready = self.get_cvar("qlx_autoready_disable_manual_readyup", bool) or False

        self.timer = None
        self.current_timer = -1
        self.timer_lock = RLock()

        self.announcer = RandomIterator(THIRTY_SECOND_WARNINGS)

        self.add_hook("client_command", self.handle_client_command)
        self.add_hook("map", self.handle_map_change)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_start", self.handle_game_start)
        self.add_hook("player_disconnect", self.handle_player_disconnect)

    def handle_client_command(self, _player, command):
        if len(self.players()) < self.min_players:
            return True

        if self.disable_player_ready and command == "readyup":
            return False

        return True

    def handle_map_change(self, _mapname, _factory):
        if self.timer is None or not self.timer.is_alive():
            self.current_timer = -1
            return

        self.timer.stop()
        self.current_timer = self.timer.seconds_left

    def handle_team_switch(self, _player, _old_team, new_team):
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

        self.timer = CountdownThread(self.current_timer, timed_actions=self.timed_actions())  # type: ignore
        self.timer.start()  # type: ignore

    def timed_actions(self):
        return {
            self.timer_visible: lambda _: None,
            31: display_countdown,
            30: partial(warning_blink, announcer_sound=next(self.announcer)),
            11: blink,
            10: shuffle_double_blink,
            9: double_blink,
            1: wear_off_double_blink,
            0: allready
        }

    def handle_game_countdown(self):
        if self.game is None:
            return

        if self.timer is None:
            return

        with self.timer_lock:
            self.timer.stop()
            self.current_timer = self.timer.seconds_left

        self.make_sure_game_really_starts(self.game.map)

    @minqlx.thread
    def make_sure_game_really_starts(self, mapname):
        while self.timer is not None:
            time.sleep(1)
            if self.timer is None:
                return

            if not self.game or self.game.map != mapname:
                return

            if self.game and self.game.state == "warmup":
                self.shuffle()
                time.sleep(2)
                self.allready()

    def handle_game_start(self, _data):
        if self.timer is None:
            return

        with self.timer_lock:
            self.timer.stop()
            self.current_timer = -1
            self.timer = None

    def handle_player_disconnect(self, _player, _reason):
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
    def __init__(self, duration: int, *, timed_actions):
        super().__init__()
        self.duration = duration
        self._target_time = None
        self._remaining = -1
        self._lock = RLock()
        self.timed_actions = {
            duration: timed_actions[duration] for duration in sorted(timed_actions.keys(), reverse=True)
        }
        self._now = None

    @property
    def seconds_left(self):
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

        remaining_function = self.determine_timed_action_for_remaining_seconds(remaining)
        remaining_function(remaining)

        sleep_delay = self._target_time - timedelta(seconds=remaining) - self._determine_now()
        if sleep_delay < timedelta(seconds=0.0):
            return

        time.sleep(sleep_delay.total_seconds())

    def _determine_now(self):
        if self._now is not None:
            return self._now
        return datetime.now()

    def calculate_target_time(self):
        return self._determine_now() + timedelta(seconds=self.duration)

    def determine_timed_action_for_remaining_seconds(self, remaining):
        for duration, action in self.timed_actions.items():
            if remaining >= duration:
                return action
        return lambda _: None


def display_countdown(remaining):
    time_color_format = "^1" if remaining <= 30 else "^3"
    remaining_minutes, remaining_seconds = divmod(remaining, 60)
    Plugin.center_print(f"Match will ^2auto-start^7 in\n"
                        f"{time_color_format}{int(remaining_minutes):01}^7:"
                        f"{time_color_format}{int(remaining_seconds):02}")


def blink(remaining, *, sleep=0.4):
    Plugin.center_print("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
    time.sleep(sleep)
    display_countdown(remaining)


def warning_blink(remaining, announcer_sound, *, sleep=0.4):
    Plugin.play_sound(announcer_sound)
    blink(remaining, sleep=sleep)


def double_blink(remaining, *, sleep=0.2, _delay=0.3):
    blink(remaining, sleep=sleep)
    time.sleep(_delay)
    blink(remaining, sleep=sleep)


def shuffle_double_blink(remaining, *, sleep=0.2, delay=0.3):
    teams = Plugin.teams()
    if abs(len(teams["red"]) - len(teams["blue"])) > 1:
        Plugin.shuffle()
    double_blink(remaining, sleep=sleep, _delay=delay)


def wear_off_double_blink(remaining, *, sleep=0.2, delay=0.3):
    Plugin.play_sound("sound/items/wearoff.ogg")
    double_blink(remaining, sleep=sleep, _delay=delay)


def allready(_remaining) -> None:
    Plugin.center_print("Match will ^2auto-start^7 in\n^20^7:^200")
    Plugin.allready()


class RandomIterator:
    def __init__(self, seq):
        self.seq = seq
        self.random_seq = random.sample(self.seq, len(self.seq))
        self.iterator = iter(self.random_seq)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            self.random_seq = random.sample(self.seq, len(self.seq))
            self.iterator = iter(self.random_seq)
            return next(self.iterator)
