from minqlx import AbstractChannel, Player, Plugin
from requests import Session
from typing import Callable, Awaitable, Iterable, Iterator

from minqlx.database import Redis

SteamId = int
PLAYER_BASE: str
IPS_BASE: str

def requests_retry_session(
    retries: int = ...,
    backoff_factor: float = ...,
    status_forcelist: tuple[int, int, int] = ...,
    session: Session | None = ...,
) -> Session: ...
def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel: ...
def remove_trailing_color_code(text: str) -> str: ...

# noinspection PyPep8Naming
class elocheck(Plugin):
    database: Redis
    reply_channel: str
    show_steam_ids: bool
    balance_api: str
    previous_map: str | None
    previous_gametype: str | None
    previous_ratings: dict[str, RatingProvider]
    ratings: dict[str, RatingProvider]
    rating_diffs: dict[str, dict[SteamId, dict]]
    informed_players: list[SteamId]
    def __init__(self) -> None: ...
    def fetch_elos_from_all_players(self) -> None: ...
    async def fetch_ratings(
        self, steam_ids: list[SteamId], mapname: str | None = ...
    ) -> None: ...
    def fetch_mapbased_ratings(
        self, steam_ids: list[SteamId], mapname: str | None = ...
    ) -> tuple[str, Awaitable[dict | None]]: ...
    def append_ratings(self, rating_provider_name: str, json_result: dict) -> None: ...
    def handle_map_change(self, mapname: str, _factory: str) -> None: ...
    def fetch_and_diff_ratings(self, mapname: str) -> None: ...
    def handle_player_connect(self, player: Player) -> None: ...
    def handle_team_switch(self, player: Player, _old: str, new: str) -> None: ...
    def format_rating_diffs_for_rating_provider_name_and_player(
        self, rating_provider_name: str, steam_id: SteamId
    ) -> str | None: ...
    def wants_to_be_informed(self, steam_id: SteamId) -> bool: ...
    def handle_game_end(self, data: dict) -> None: ...
    def cmd_elocheck(
        self, player: Player, msg: str, channel: AbstractChannel
    ) -> int | None: ...
    def do_elocheck(
        self, player: Player, target: str, channel: AbstractChannel
    ) -> None: ...
    def find_target_player(self, target: str) -> list[Player]: ...
    def reply_func(
        self, player: Player, channel: AbstractChannel
    ) -> Callable[[str], None]: ...
    def used_steam_ids_for(self, steam_id: SteamId) -> list[int]: ...
    def fetch_aliases(self, steam_ids: list[SteamId]) -> dict[SteamId, list[str]]: ...
    def format_player_elos(
        self,
        a_elo: RatingProvider | None,
        b_elo: RatingProvider | None,
        truskill: RatingProvider | None,
        map_based_truskill: RatingProvider | None,
        steam_id: SteamId,
        indent: int = ...,
        aliases: list[str] | None = ...,
    ) -> str: ...
    def format_player_name(self, steam_id: SteamId) -> str: ...
    def resolve_player_name(self, steam_id: SteamId) -> str: ...
    def cmd_aliases(
        self, player: Player, msg: str, channel: AbstractChannel
    ) -> int | None: ...
    def do_aliases(
        self, player: Player, target: str, channel: AbstractChannel
    ) -> None: ...
    def format_player_aliases(self, steam_id: SteamId, aliases: list[str]) -> str: ...
    def cmd_switch_elo_changes_notifications(
        self, player: Player, _msg: str, _channel: AbstractChannel
    ) -> int | None: ...

FILTERED_OUT_GAMETYPE_RESPONSES: Iterable[str]

class SkillRatingProvider:
    name: str
    url_base: str
    balance_api: str
    timeout: int
    def __init__(
        self, name: str, url_base: str, balance_api: str, timeout: int = ...
    ) -> None: ...
    async def fetch_elos(
        self, steam_ids: list[SteamId], *, headers: dict[str, str] | None = ...
    ) -> dict | None: ...

TRUSKILLS: SkillRatingProvider
A_ELO: SkillRatingProvider
B_ELO: SkillRatingProvider

class RatingProvider:
    jsons: list[dict]
    def __init__(self, json: dict) -> None: ...
    def __iter__(self) -> Iterator[SteamId]: ...
    def __contains__(self, item: object) -> bool: ...
    def __getitem__(self, item: object) -> object | dict | PlayerRating: ...
    def __sub__(self, other: object) -> dict[SteamId, dict[str, dict]]: ...
    @staticmethod
    def from_json(json_response: dict) -> RatingProvider: ...
    def append_ratings(self, json_response: dict) -> None: ...
    def player_data_for(self, steam_id: SteamId) -> dict | None: ...
    def gametype_data_for(self, steam_id: SteamId, gametype: str) -> dict: ...
    def rating_for(self, steam_id: SteamId, gametype: str) -> int | float | None: ...
    def games_for(self, steam_id: SteamId, gametype: str) -> int: ...
    def rated_gametypes_for(self, steam_id: SteamId) -> list[str]: ...
    def privacy_for(self, steam_id: SteamId) -> str | None: ...
    def rated_steam_ids(self) -> list[SteamId]: ...
    def format_elos(self, steam_id: SteamId) -> str: ...

class PlayerRating:
    ratings: dict
    time: int
    local: bool
    def __init__(self, ratings, _time: int = ..., local: bool = ...) -> None: ...
    def __iter__(self) -> Iterator[int | float]: ...
    def __contains__(self, item: object) -> bool: ...
    def __getitem__(self, item: object) -> dict[str, int | float | str | bool]: ...
    def __getattr__(self, attr: str) -> str: ...