from typing import TYPE_CHECKING

from minqlx import Plugin, Player, AbstractChannel

if TYPE_CHECKING:
    from threading import RLock

    from openai import ChatCompletion
    from minqlx.database import Redis

DATETIMEFORMAT: str
CHAT_BOT_LOG: str

def num_tokens_from_messages(
    messages: list[dict[str, str]], *, model: str = ...
) -> int: ...

# noinspection PyPep8Naming
class openai_bot(Plugin):
    database: Redis
    queue_lock: RLock
    bot_api_key: str
    bot_name: str
    bot_clanprefix: str
    bot_triggers: list[str]
    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    system_context: str
    bot_mood: str
    max_chat_history_tokens: int
    greet_joiners: bool
    greeting_delay: int
    recently_connected_steam_ids: set[int]
    map_authors_cache: dict[str, str]
    def __init__(self) -> None: ...
    def cache_map_authors_from_db(self) -> None: ...
    def summarize_game_end_stats(self, announcements: str) -> None: ...
    def _gather_completion(
        self, chat_history: str | list[dict[str, str]]
    ) -> str | None: ...
    def _pick_choice_and_cleanup(self, completion: ChatCompletion) -> str | None: ...
    def _record_chat_line(self, message: str, *, lock: RLock) -> None: ...
    def _send_message(
        self, communication_channel: AbstractChannel, message: str
    ) -> None: ...
    def _ql_cleaned_up(self, message: str) -> str: ...
    def handle_chat(
        self, player: Player, msg: str, channel: AbstractChannel
    ) -> None: ...
    def contextualized_chat_history(
        self, request: str
    ) -> str | list[dict[str, str]]: ...
    def current_game_state(self) -> str: ...
    def team_status(self) -> str: ...
    def handle_player_connect(self, player: Player) -> None: ...
    def _remove_recently_connected(self, steam_id: int) -> None: ...
    def handle_game_countdown(self) -> None: ...
    def handle_round_end(self, _data: dict[str, str]) -> None: ...
    def handle_game_end(self, _data: dict[str, str]) -> None: ...
    def cmd_list_models(
        self, player: Player, _msg: str, _channel: AbstractChannel
    ) -> None: ...
    def _list_models_in_thread(self, player: Player) -> None: ...
    def cmd_switch_model(
        self, player: Player, msg: str, _channel: AbstractChannel
    ) -> int: ...
    def _switch_model_in_thread(self, player: Player, model: str) -> None: ...
