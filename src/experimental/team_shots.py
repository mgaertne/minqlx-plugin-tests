import time
from ast import literal_eval
from operator import itemgetter

from minqlx import Plugin, Player


# noinspection PyPep8Naming
class team_shots(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_teamShots_minHealth", "1")
        self.set_cvar_once("qlx_teamShots_punishments", "{}")
        self.set_cvar_once("qlx_teamShots_min_damage", "15")
        self.set_cvar_once("qlx_teamShots_warning_text", "^1watch your fire!")
        self.set_cvar_once("qlx_teamShots_filtered_means_of_death", "18")

        self.min_health = self.get_cvar("qlx_teamShots_minHealth", int) or 1
        punishment_cvar_value = self.get_cvar("qlx_teamShots_punishments") or "{}"
        self.punishment_lookup = literal_eval(punishment_cvar_value) or {}
        self.min_damage = self.get_cvar("qlx_teamShots_min_damage", int) or 15
        self.warning_text = (
            self.get_cvar("qlx_teamShots_warning_text") or "^1watch your fire!"
        )
        filtered_mod_strings = self.get_cvar(
            "qlx_teamShots_filtered_means_of_death", list
        ) or ["18"]
        self.filtered_means_of_death = [int(entry) for entry in filtered_mod_strings]

        self.team_damages = {}

        self.add_hook("game_countdown", self.handle_game_countdown)

        self.add_hook("damage", self.handle_damage_event)

    def handle_game_countdown(self):
        self.team_damages = {}

    def handle_damage_event(self, target, attacker, dmg, dflags, means_of_death):
        timestamp = int(time.time() * 1000)

        if not self.game:
            return

        if self.game.state != "in_progress":
            return

        if not isinstance(target, Player):
            return

        if not isinstance(attacker, Player):
            return

        if target.id == attacker.id:
            return

        if target.team != attacker.team:
            return

        if target.health <= 0:
            return

        if dmg < self.min_damage:
            return

        if means_of_death in self.filtered_means_of_death:
            return

        if dflags & 16 != 0:
            return

        punishment = self.punishment_lookup.get(means_of_death, 0)
        if punishment > 0:
            if attacker.health > self.min_health:
                attacker.health -= punishment
            self.play_sound("sound/feedback/hit_teammate.ogg", player=attacker)

            if (
                attacker.steam_id in self.team_damages
                and timestamp
                - max(self.team_damages[attacker.steam_id], key=itemgetter(1))[0]
                < 2000
            ):
                attacker.center_print(self.warning_text)

        if attacker.steam_id not in self.team_damages:
            self.team_damages[attacker.steam_id] = []
        self.team_damages[attacker.steam_id].append((timestamp, dmg))
