import itertools
from ast import literal_eval

from minqlx import Plugin


# noinspection PyPep8Naming
class team_shots(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_teamShots_minHealth", "1")
        self.set_cvar_once("qlx_teamShots_punishments", "{}")

        self.min_health = self.get_cvar("qlx_teamShots_minHealth", int) or 1
        punishment_cvar_value = self.get_cvar("qlx_teamShots_punishments") or "{}"
        self.punishment_lookup = literal_eval(punishment_cvar_value) or {}

        self.team_damages = {}
        self.team_shots = {}

        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_end", self.handle_game_end)

        self.add_hook("damage", self.handle_damage_event)

    def handle_game_countdown(self):
        self.team_damages = {}
        self.team_shots = {}

    def handle_game_end(self, _data):
        if len(self.team_damages) == 0:
            return

        grouped_team_damages = itertools.groupby(
            sorted(self.team_damages, key=self.team_damages.get, reverse=True),  # type: ignore
            key=self.team_damages.get,
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
                    f"^5{self.team_shots[steam_id]} shots^7)"
                )
                prefix = "   "

    def handle_damage_event(self, target, attacker, dmg, dflags, means_of_death):
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

        if dflags & 16 == 0:
            punishment = self.punishment_lookup.get(means_of_death, 0)
            if punishment > 0:
                if attacker.health > self.min_health:
                    attacker.health -= punishment
                self.play_sound("sound/feedback/hit_teammate.ogg", player=attacker)
                attacker.center_print("^1watch your fire!")

            self.team_damages[attacker.steam_id] = (
                self.team_damages.get(attacker.steam_id, 0) + dmg
            )
            self.team_shots[attacker.steam_id] = (
                self.team_shots.get(attacker.steam_id, 0) + 1
            )
