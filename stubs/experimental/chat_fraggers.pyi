from minqlx import Plugin, Player, KillData

def warn_player(player: Player, warning: str) -> None: ...
def punish_player(player: Player, punish_text: str) -> None: ...

SteamId = int

# noinspection PyPep8Naming
class chat_fraggers(Plugin):
    punishment_threshold: int
    warning_text: str
    punish_text: str
    chat_tracker: dict[SteamId, dict[SteamId, int]]
    def __init__(self) -> None: ...
    def handle_round_countdown(self, _round_number: int) -> None: ...
    def handle_damage_event(
        self,
        target: Player | None,
        attacker: Player | None,
        dmg: int,
        _dflags: int,
        _means_of_death: int,
    ) -> None: ...
    def handle_kill(self, victim: Player, killer: Player | None, _data: KillData) -> None: ...
