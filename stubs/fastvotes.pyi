from typing import TYPE_CHECKING

from minqlx import Plugin

if TYPE_CHECKING:
    from typing import Protocol

    from minqlx import Player

# noinspection PyPep8Naming
class fastvotes(Plugin):
    fastvote_types: list[str]
    track_vote: bool

    def __init__(self) -> None: ...
    def resolve_strategy_for_fastvote(self, strategy: str) -> FastVoteStrategy: ...
    def handle_vote(self, _player: Player, vote: str, _args: str) -> None: ...
    def handle_vote_ended(self, _votes: tuple[int, int], _vote: str, _args: str, _passed: bool) -> None: ...
    def process_vote(self, _player: Player, yes: bool) -> None: ...

class FastVoteStrategy(Protocol):
    def evaluate_votes(self, yes_votes: int, no_votes: int) -> bool | None: ...

class ThresholdFastVoteStrategy:
    threshold_fast_pass_diff: int
    threshold_fast_fail_diff: int

    def __init__(self) -> None: ...
    def evaluate_votes(self, yes_votes: int, no_votes: int) -> bool | None: ...

class ParticipationFastVoteStrategy:
    participation_percentage: float

    def __init__(self) -> None: ...
    def evaluate_votes(self, yes_votes: int, no_votes: int) -> bool | None: ...
