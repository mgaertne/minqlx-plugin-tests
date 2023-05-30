import itertools
import time
from ast import literal_eval
from operator import itemgetter

from minqlx import Plugin


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
        filtered_mod_strings = self.get_cvar("qlx_teamShots_filtered_means_of_death", list) or ["18"]
        self.filtered_means_of_death = [int(entry) for entry in filtered_mod_strings]

        self.team_damages = {}

        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_end", self.handle_game_end)

        self.add_hook("damage", self.handle_damage_event)

    def handle_game_countdown(self):
        self.team_damages = {}

    def handle_game_end(self, _data):
        if len(self.team_damages) == 0:
            return

        team_damages = {}
        for steam_id in self.team_damages:
            team_damages[steam_id] = sum(
                [dmg for _, dmg in self.team_damages[steam_id]]
            )

        grouped_team_damages = itertools.groupby(
            sorted(team_damages, key=team_damages.get, reverse=True),  # type: ignore
            key=team_damages.get,
        )
        grouped_team_damages_dict = {
            team_dmg: list(steam_ids) for team_dmg, steam_ids in grouped_team_damages
        }

        self.msg("^7Top 3 team damage inflicter:")
        extra = 0
        for counter, (team_damage, steam_ids) in enumerate(
                grouped_team_damages_dict.items(), start=1
        ):
            if counter + extra > 3:
                break

            prefix = f"^5{counter + extra:2}^7."
            extra += max(0, len(steam_ids) - 1)

            for steam_id in steam_ids:
                player = self.player(steam_id)
                if player is None:
                    continue
                self.msg(
                    f"  {prefix} {player.name}^7 (^5{team_damage} team damage^7, "
                    f"^5{len(self.team_damages[steam_id])} shots^7)"
                )
                prefix = "   "

    def handle_damage_event(self, target, attacker, dmg, dflags, means_of_death):
        timestamp = int(time.time() * 1000)

        if not self.game:
            return

        if self.game.state != "in_progress":
            return

        if attacker is None:
            return

        if target.id == attacker.id:
            return

        if target.team != attacker.team:
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
