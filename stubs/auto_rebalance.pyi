from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from typing import Iterable

    from minqlx import Player, CancellableEventReturn

DEFAULT_RATING: int = 1500
SUPPORTED_GAMETYPES: Iterable[str] = ("ca", "ctf", "dom", "ft", "tdm", "duel", "ffa")

# noinspection PyPep8Naming
class auto_rebalance(Plugin):
    last_new_player_id: int | None
    score_diff_suggestion_threshold: int
    winning_streak_suggestion_threshold: int
    num_announcements: int
    winning_teams: list[str]
    plugin_version: str

    def __init__(self) -> None: ...
    def handle_team_switch_attempt(
        self, player: Player, old: str, new: str
    ) -> CancellableEventReturn: ...
    def other_team(self, team: str) -> str: ...
    def format_team(self, team: str) -> str: ...
    def calculate_player_average_difference(
        self, gametype: str, team1: list[Player], team2: list[Player]
    ) -> float: ...
    def team_average(self, gametype: str, team: list[Player]) -> float: ...
    def handle_round_start(self, _roundnumber: int) -> None: ...
    def handle_round_end(self, data: dict) -> CancellableEventReturn: ...
    def team_is_on_a_winning_streak(self, team: str) -> bool: ...
    def announced_often_enough(self, winning_team: str) -> bool: ...
    def handle_reset_winning_teams(self, *_args: list, **_kwargs: dict) -> None: ...
