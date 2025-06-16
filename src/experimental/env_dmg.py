import time

from minqlx import Plugin, Player
import minqlx


# noinspection PyPep8Naming
class env_dmg(Plugin):
    def __init__(self):
        super().__init__()

        self.add_hook("map", self.handle_map)
        self.add_hook("damage", self.handle_damage)
        self.add_hook("death", self.handle_death)

        self.recorded_entity_dmg = {}
        self.means_of_death_watchlist = {}

    def handle_map(self, _mapname, _factory):
        self.recorded_entity_dmg = {}

    def handle_damage(self, target, attacker, _dmg, _dflags, means_of_death):
        timestamp = int(time.time() * 1000)
        if target is not None and not isinstance(target, Player) and isinstance(attacker, Player):
            if target not in self.recorded_entity_dmg:
                self.recorded_entity_dmg[target] = []
            self.recorded_entity_dmg[target].append((timestamp, attacker.steam_id))

        if isinstance(target, Player) and attacker is not None and not isinstance(attacker, Player):
            self.scan_targetting_entities(attacker, means_of_death, timestamp)

    def scan_targetting_entities(self, entity_id, means_of_death, timestamp):
        for targetting_entity in minqlx.get_targetting_entities(entity_id):
            if targetting_entity in self.recorded_entity_dmg:
                list_of_inflictors = [
                    attacker
                    for inflict_timestamp, attacker in self.recorded_entity_dmg[targetting_entity]
                    if timestamp - inflict_timestamp <= 5000
                ]
                if len(list_of_inflictors) == 1:
                    self.means_of_death_watchlist[means_of_death] = list_of_inflictors[0]
            self.scan_targetting_entities(targetting_entity, means_of_death, timestamp)

    def handle_death(self, victim, killer, data):
        if killer is not None:
            return

        means_of_death_str = data["MOD"]
        if means_of_death_str not in ["UNKNOWN", "HURT", "CRUSH"]:
            return

        means_of_death = getattr(minqlx, f"MOD_{means_of_death_str}")
        if means_of_death not in self.means_of_death_watchlist:
            return

        potential_killer = self.player(self.means_of_death_watchlist[means_of_death])
        if potential_killer is not None:
            if potential_killer.steam_id == victim.steam_id:
                self.msg(f"Uh, looks like {victim.name}^7 may have killed himself^7")
            else:
                self.msg(f"Uh, looks like {potential_killer.name}^7 may have killed {victim.name}^7")
