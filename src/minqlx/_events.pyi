from re import Pattern
from typing import Any, Type, Callable, ClassVar

import minqlx

_re_vote: Pattern


class EventDispatcher:
    name: str
    plugins: dict[minqlx.Plugin, tuple[list, list, list, list, list]]
    args: Any
    kwargs: Any
    return_value: str | bool | None
    no_debug: tuple[str, ...]
    need_zmq_stats_enabled: bool

    def __init__(self) -> None: ...

    def dispatch(self, *args, **kwargs): ...
    def handle_return(self, handler: Callable, value: int | str | None) -> Any: ...
    def add_hook(self, plugin: minqlx.Plugin | str, handler: Callable, priority: int = ...) -> None: ...
    def remove_hook(self, plugin: minqlx.Plugin | str, handler: Callable, priority: int = ...) -> None: ...


class EventDispatcherManager:
    _dispatchers: dict[str, EventDispatcher]

    def __init__(self) -> None: ...
    def __getitem__(self, key: str) -> EventDispatcher: ...
    def __contains__(self, key: str) -> bool: ...

    def add_dispatcher(self, dispatcher: Type[EventDispatcher]) -> None: ...
    def remove_dispatcher(self, dispatcher: Type[EventDispatcher]) -> None: ...
    def remove_dispatcher_by_name(self, event_name: str) -> None: ...


class ConsolePrintDispatcher(EventDispatcher):
    def dispatch(self, text: str) -> None: ...
    def handle_return(self, handler, value): ...


class CommandDispatcher(EventDispatcher):
    def dispatch(self, caller, command, args): ...


class ClientCommandDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, cmd: str): ...
    def handle_return(self, handler, value): ...


class ServerCommandDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, cmd: str): ...
    def handle_return(self, handler, value): ...


class FrameEventDispatcher(EventDispatcher):
    def dispatch(self): ...


class SetConfigstringDispatcher(EventDispatcher):
    def dispatch(self, index: int, value: str): ...
    def handle_return(self, handler, value): ...


class ChatEventDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel): ...


class UnloadDispatcher(EventDispatcher):
    def dispatch(self, plugin: minqlx.Plugin): ...


class PlayerConnectDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...
    def handle_return(self, handler, value): ...


class PlayerLoadedDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...


class PlayerDisonnectDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, reason: str | None): ...


class PlayerSpawnDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...


class StatsDispatcher(EventDispatcher):
    def dispatch(self, stats): ...


class VoteCalledDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, vote: str, args: str | None): ...


class VoteStartedDispatcher(EventDispatcher):
    _caller: minqlx.Player | None

    def __init__(self) -> None: ...

    def dispatch(self, vote: str, args: str | None): ...
    def caller(self, player: minqlx.Player) -> None: ...


class VoteEndedDispatcher(EventDispatcher):
    def dispatch(self, passed: bool): ...


class VoteDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, yes: bool): ...


class GameCountdownDispatcher(EventDispatcher):
    def dispatch(self): ...


class GameStartDispatcher(EventDispatcher):
    def dispatch(self, data): ...


class GameEndDispatcher(EventDispatcher):
    def dispatch(self, data): ...


class RoundCountdownDispatcher(EventDispatcher):
    def dispatch(self, round_number: int): ...


class RoundStartDispatcher(EventDispatcher):
    def dispatch(self, round_number: int): ...


class RoundEndDispatcher(EventDispatcher):
    def dispatch(self, data): ...


class TeamSwitchDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, old_team: str, new_team: str): ...


class TeamSwitchAttemptDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, old_team: str, new_team: str): ...


class MapDispatcher(EventDispatcher):
    def dispatch(self, mapname: str, factory: str): ...


class NewGameDispatcher(EventDispatcher):
    def dispatch(self): ...


class KillDispatcher(EventDispatcher):
    def dispatch(self, victim: minqlx.Player, killer: minqlx.Player | None, data): ...


class DeathDispatcher(EventDispatcher):
    def dispatch(self, victim: minqlx.Player, killer: minqlx.Player | None, data): ...


class UserinfoDispatcher(EventDispatcher):
    def dispatch(self, playe: minqlx.Player, changed): ...
    def handle_return(self, handler, value): ...


class KamikazeUseDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...


class KamikazeExplodeDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player, is_used_on_demand: bool): ...


class PlayerInactivityKickDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...


class PlayerInactivityKickWarningDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...


class PlayerItemsTossDispatcher(EventDispatcher):
    def dispatch(self, player: minqlx.Player): ...
    def handle_return(self, handler, value): ...


EVENT_DISPATCHERS: EventDispatcherManager
