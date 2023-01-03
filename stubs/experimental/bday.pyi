from datetime import datetime

from minqlx import Plugin, AbstractChannel, Player
from minqlx.database import Redis

SteamId = int

BDAY_KEY: str
LONG_MAP_NAMES_KEY: str

# noinspection PyPep8Naming
class bday(Plugin):
    database: Redis
    bmap_steamid: SteamId | None
    bmap_map: str | None
    number_of_bday_maps: int
    pending_bday_confirmations: dict[SteamId, str]
    def __init__(self) -> None: ...
    def cmd_bday(self, player: Player, msg: str, _channel: AbstractChannel) -> int: ...
    def parse_date(self, player: Player, msg: str) -> int: ...
    def delayed_removal_of_pending_registration(self, steam_id: SteamId) -> None: ...
    def cmd_confirmbday(self, player: Player, _msg: str, _channel: AbstractChannel) -> None: ...
    def cmd_bmap(self, player: Player, msg: str, _channel: AbstractChannel) -> int: ...
    def cmd_bdayedit(self, player: Player, msg: str, _channel: AbstractChannel) -> int: ...
    def parse_admin_date(self, admin: Player, msg: str) -> int: ...
    def identify_target(self, player: Player, target: str | int | Player) -> tuple[str | None, SteamId | None]: ...
    def resolve_player_name(self, item: str | int | Player) -> str: ...
    def find_target_player_or_list_alternatives(self, player: Player, target: str | int) -> Player | None: ...
    def cmd_when(self, player: Player, msg: str, _channel: AbstractChannel) -> int: ...
    def cmd_nextbday(self, _player: Player, _msg: str, channel: AbstractChannel) -> None: ...
    def report_next_birthday(self, channel: AbstractChannel) -> None: ...
    def next_birthdate(self, birthday: datetime) -> datetime: ...
    def identify_reply_channel(self, channel: AbstractChannel) -> AbstractChannel: ...
    def handle_player_connected(self, player: Player) -> None: ...
    def handle_game_end(self, _data: dict) -> None: ...
    def handle_map(self, mapname: str, _factory: str) -> None: ...
    def handle_team_switch(self, player: Player, _old: str, new: str) -> None: ...
    def play_birthday_song(self) -> None: ...
    def has_birthday_today(self, player: Player) -> bool: ...
    def has_birthday_set(self, player: Player) -> bool: ...
    def can_still_pick_bday_map(self, player: Player) -> bool: ...
    def resolve_short_mapname(self, mapstring: str, player: Player) -> str | None: ...
    def determine_installed_maps(self) -> list[str]: ...
    def cleaned_up_longmapname(self, longmapname: str) -> str: ...
    def delay_change_map(self, _mapname: str) -> None: ...
