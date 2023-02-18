from threading import RLock

from minqlx import Plugin, Player, AbstractChannel
from minqlx.database import Redis

DATETIMEFORMAT: str
CHAT_BOT_LOG: str

def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel: ...

# noinspection PyPep8Naming
class openai_bot(Plugin):
    database: Redis
    queue_lock: RLock
    bot_api_key: str
    bot_name: str
    bot_clanprefix: str
    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    prompt_template: str
    chat_history_minutes: int
    chat_history_length: int
    def __init__(self) -> None: ...
    def handle_chat(self, player: Player, msg: str, channel: AbstractChannel) -> None: ...
    def contextualized_query(self, request: str) -> str: ...
    def cmd_list_models(self, player: Player, _msg: str, _channel: AbstractChannel) -> None: ...
    def list_models_in_thread(self, player: Player) -> None: ...
    def cmd_switch_model(self, player: Player, msg: str, _channel: AbstractChannel) -> int: ...
    def switch_model_in_thread(self, player: Player, model: str) -> None: ...
