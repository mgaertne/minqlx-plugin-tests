from minqlx import Plugin


def warn_player(player, warning):
    player.center_print(warning)


def punish_player(player, punish_text):
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
    player.center_print(punish_text)


# noinspection PyPep8Naming
class chat_fraggers(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_chatFraggers_punishment_threshold", "250")
        self.punishment_threshold = (
            self.get_cvar("qlx_chatFraggers_punishment_threshold", int) or 250
        )

        self.set_cvar_once(
            "qlx_chatFraggers_warning_text", "^1Shoot Chatters = Insta-Ban"
        )
        self.warning_text = (
            self.get_cvar("qlx_chatFraggers_warning_text")
            or "^1Shoot Chatters = Insta-Ban"
        )

        self.set_cvar_once("qlx_chatFraggers_punish_text", "^1You have been warned!")
        self.punish_text = (
            self.get_cvar("qlx_chatFraggers_warning_text") or "^1You have been warned!"
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

        if target is None:
            return

        if attacker is None:
            return

        if target.id == attacker.id:
            return

        if target.team == attacker.team:
            return

        if not target.is_alive:
            return

        if target.health <= 0:
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
            warn_player(attacker, self.warning_text)
            return

        punish_player(attacker, self.punish_text)

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
            warn_player(killer, self.warning_text)
            return

        punish_player(killer, self.punish_text)
