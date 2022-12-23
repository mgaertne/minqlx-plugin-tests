from logging import Logger
from typing import Any

import redis

import minqlx


class AbstractDatabase:
    _counter: int
    plugin: minqlx.Plugin


    def __init__(self, plugin: minqlx.Plugin):
        ...

    def __del__(self):
        ...

    @property
    def logger(self) -> Logger:
        ...

    def set_permission(self, player: minqlx.Player, level: int) -> None:
        ...

    def get_permission(self, player: minqlx.Player) -> int:
        ...

    def has_permission(self, player: minqlx.Player, level: int = ...) -> bool:
        ...

    def set_flag(self, player: minqlx.Player, flag: str, value: bool = ...) -> None:
        ...

    def clear_flag(self, player: minqlx.Player, flag: str) -> None:
        ...

    def get_flag(self, player: minqlx.Player, flag: str, default: bool = ...) -> bool:
        ...

    def connect(self) -> Any:
        ...

    def close(self) -> None:
        ...


class Redis(AbstractDatabase):
    _conn: [redis.Redis | None]
    _pool: [redis.ConnectionPool | None]
    _pass: str

    def __del__(self) -> None:
        ...

    def __contains__(self, key: str) -> bool:
        ...

    def __getitem__(self, key: str) -> Any:
        ...

    def __setitem__(self, key: str, item: Any) -> None:
        ...

    def __delitem__(self, key: str) -> None:
        ...

    def __getattr__(self, attr: Any) -> Any:
        ...

    @property
    def r(self) -> Any:
        ...

    def set_permission(self, player: minqlx.Player, level: int) -> None:
        ...

    def get_permission(self, player: minqlx.Player) -> int:
        ...

    def has_permission(self, player: minqlx.Player, level: int = ...) -> bool:
        ...

    def set_flag(self, player: minqlx.Player, flag: str, value: bool = ...) -> None:
        ...

    def get_flag(self, player, flag: str, default: bool = False) -> bool:
        ...

    def connect(self, host: [str | None] = ..., database: int = ..., unix_socket: bool = ...,
                password: [str | None] = ...) -> [redis.Redis | None]:
        ...

    def close(self) -> None:
        ...
