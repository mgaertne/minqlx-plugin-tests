from minqlx import Plugin, Player, DeathData

SteamId = int
Timestamp = int

# noinspection PyPep8Naming
class env_dmg(Plugin):
    recorded_entity_dmg: dict[int, list[tuple[Timestamp, SteamId]]]
    means_of_death_watchlist: dict[int, SteamId]
    def __init__(self) -> None: ...
    def handle_map(self, _mapname: str, _factory: str) -> None: ...
    def handle_damage(
        self,
        target: Player | int | None,
        attacker: Player | int | None,
        dmg: int,
        dflags: int,
        means_of_death: int,
    ) -> None: ...
    def scan_targetting_entities(
        self, entity_id: int, means_of_death: int, timestamp: Timestamp
    ) -> None: ...
    def handle_death(
        self, victim: Player, killer: Player | None, _data: DeathData
    ) -> None: ...
