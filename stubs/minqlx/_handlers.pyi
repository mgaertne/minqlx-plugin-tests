from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Pattern, Type
    from collections import deque
    from sched import scheduler
    from types import TracebackType

    from minqlx import AbstractChannel

_re_say: Pattern
_re_say_team: Pattern
_re_callvote: Pattern
_re_vote: Pattern
_re_team: Pattern
_re_vote_ended: Pattern
_re_userinfo: Pattern

frame_tasks: scheduler
next_frame_tasks: deque

_zmq_warning_issued: bool
_first_game: bool
_ad_round_number: int

_print_redirection: AbstractChannel | None
_print_buffer: str

def handle_rcon(cmd: str) -> bool | None: ...
def handle_client_command(client_id: int, cmd: str) -> bool | str: ...
def handle_server_command(client_id: int, cmd: str) -> bool | str: ...
def handle_frame() -> bool | None: ...
def handle_new_game(is_restart: bool) -> bool | None: ...
def handle_set_configstring(index: int, value: str) -> bool | None: ...
def handle_player_connect(client_id: int, _is_bot: bool) -> bool | None: ...
def handle_player_loaded(client_id: int) -> bool | None: ...
def handle_player_disconnect(client_id: int, reason: str | None) -> bool | None: ...
def handle_player_spawn(client_id: int) -> bool | None: ...
def handle_kamikaze_use(client_id: int) -> bool | None: ...
def handle_kamikaze_explode(client_id: int, is_used_on_demand: bool) -> bool | None: ...
def handle_damage(
    target_id: int, attacker_id: int | None, damage: int, dflags: int, mod: int
) -> bool | None: ...
def handle_console_print(text: str | None) -> bool | str | None: ...
def redirect_print(channel: AbstractChannel) -> PrintRedirector: ...
def register_handlers() -> None: ...

class PrintRedirector:
    channel: AbstractChannel
    def __init__(self, _channel: AbstractChannel) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None: ...
    def flush(self) -> None: ...
