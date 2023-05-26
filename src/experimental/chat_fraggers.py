from minqlx import Plugin


def warn_player(player):
    player.center_print("^1Shoot Chatters = Insta-Ban")


def punish_player(player):
    player.armor = 0
    player.health = 1
    player.weapons(
        g=False,
        mg=False,
        sg=False,
        gl=False,
        rl=False,
        lg=False,
        rg=False,
        pg=False,
        bfg=False,
        gh=False,
        ng=False,
        pl=False,
        cg=False,
        hmg=False,
    )
    player.weapon(15)
    player.center_print("^1You have been warned!")


# noinspection PyPep8Naming
class chat_fraggers(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_chatFraggers_punishment_threshold", "250")
        self.punishment_threshold = (
            self.get_cvar("qlx_chatFraggers_punishment_threshold", int) or 250
        )

        self.chat_tracker = {}

        self.add_hook("round_countdown", self.handle_round_countdown)

        self.add_hook("damage", self.handle_damage_event)
        self.add_hook("kill", self.handle_kill)

    def handle_round_countdown(self, _round_number):
        self.chat_tracker = {}

    def handle_damage_event(self, target, attacker, dmg, _dflags, _means_of_death):
        if not self.game:
            return

        if self.game.state != "in_progress":
            return

        if attacker is None:
            return

        if target.id == attacker.id:
            return

        if target.team == attacker.team:
            return

        if not hasattr(target.state, "is_chatting") or not target.state.is_chatting:
            return

        if attacker.steam_id not in self.chat_tracker:
            self.chat_tracker[attacker.steam_id] = {}
        self.chat_tracker[attacker.steam_id][target.steam_id] = (
            self.chat_tracker[attacker.steam_id].get(target.steam_id, 0) + dmg
        )

        if (
            self.chat_tracker[attacker.steam_id][target.steam_id]
            < self.punishment_threshold
        ):
            warn_player(attacker)
            return

        punish_player(attacker)

    def handle_kill(self, victim, killer, _data):
        if not self.game:
            return

        if self.game.state != "in_progress":
            return

        if not hasattr(victim.state, "is_chatting") or not victim.state.is_chatting:
            return

        if killer is None:
            return

        if killer.steam_id not in self.chat_tracker:
            return

        if victim.steam_id not in self.chat_tracker[killer.steam_id]:
            return

        if (
            self.chat_tracker[killer.steam_id][victim.steam_id]
            < self.punishment_threshold
        ):
            warn_player(killer)
            return

        punish_player(killer)
