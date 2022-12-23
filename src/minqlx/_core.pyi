from types import TracebackType, ModuleType
from typing import Type, Callable

import datetime
import logging

import minqlx

class PluginLoadError(Exception): ...


class PluginUnloadError(Exception): ...


TEAMS: dict[int, str]
GAMETYPES: dict[int, str]
GAMETYPES_SHORT : dict[int, str]
CONNECTION_STATES: dict[int, str]
WEAPONS: dict[int, str]
DEFAULT_PLUGINS: tuple[str, ...]

_init_time: datetime.datetime
_stats: minqlx.StatsListener
_thread_count: int
_thread_name: str
_modules: dict[str, ModuleType]


def parse_variables(varstr: str, ordered: bool = False) -> dict[str, str]: ...
def get_logger(plugin: minqlx.Plugin | str | None = ...) -> logging.Logger: ...
def _configure_logger() -> None: ...
def log_exception(plugin: minqlx.Plugin | str | None = ...) -> None: ...
def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None) \
        -> None: ...
def threading_excepthook(args) -> None: ...
def uptime() -> datetime.timedelta: ...
def owner() -> int | None: ...
def stats_listener() -> minqlx.StatsListener: ...
def set_cvar_once(name: str, value: str, flags: int = ...) -> bool: ...
def set_cvar_limit_once(name: str, value: int | float, minimum: int | float, maximum: int | float, flags: int = ...) \
        -> bool: ...
def set_plugins_version(path: str) -> None: ...
def set_map_subtitles() -> None: ...
def next_frame(func: Callable) -> Callable: ...
def delay(time: float) -> Callable: ...
def thread(func: Callable, force: bool = ...) -> Callable: ...
def load_preset_plugins() -> None: ...
def load_plugin(plugin: str) -> None: ...
def unload_plugin(plugin: str) -> None: ...
def reload_plugin(plugin: str) -> None: ...
def initialize_cvars() -> None: ...
def initialize() -> None: ...
def late_init() -> None: ...