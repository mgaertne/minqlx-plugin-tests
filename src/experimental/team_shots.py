from ast import literal_eval

from minqlx import Plugin


# noinspection PyPep8Naming
class team_shots(Plugin):
    def __init__(self):
        super().__init__()
        
        self.set_cvar_once("qlx_teamShots_minHealth", "5")
        self.set_cvar_once("qlx_teamShots_punishments", "{}")

        self.min_health = self.get_cvar("qlx_teamShots_minHealth", int) or 5        
        self.punishment_lookup = literal_eval(self.get_cvar("qlx_teamShots_punushments") or "{}")

        self.team_damages = {}
        self.team_shots = {}

        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_end", self.handle_game_end)

        self.add_hook("damage", self.handle_damage_event)

    def handle_game_countdown(self):
        self.team_damages = {}
        self.team_shots = {}

    def handle_game_end(self, _data):
        self.logger.debug("Overall team damages:")
        for steam_id, damage in self.team_damages.items():
            player = self.player(steam_id)
            self.logger.debug(f"team dmg: {player.clean_name}: {damage} dmg ({self.team_shots[player.steam_id]} shots)")

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
                attacker.center_print("^1watch your fire!")

            self.team_damages[attacker.steam_id] = self.team_damages.get(attacker.steam_id, 0) + dmg
            self.team_shots[attacker.steam_id] = self.team_shots.get(attacker.steam_id, 0) + 1
