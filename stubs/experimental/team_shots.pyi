from minqlx import Plugin, Player

SteamId = int

# noinspection PyPep8Naming
class team_shots(Plugin):
    min_health: int
    punishment_lookup: dict[int, int]
    min_damage: int
    warning_text: str
    filtered_means_of_death: list[int]
    team_damages: dict[SteamId, list[tuple[int, int]]]
    def __init__(self) -> None: ...
    def handle_game_countdown(self) -> None: ...
    def handle_damage_event(
        self,
        target: Player | None,
        attacker: Player | None,
        dmg: int,
        dflags: int,
        means_of_death: int,
    ) -> None: ...
