from minqlx import Plugin


# noinspection PyPep8Naming
class chat_fraggers(Plugin):
    def __init__(self):
        super().__init__()

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

        if hasattr(target.state, "is_chatting") and target.state.is_chatting:
            if attacker.steam_id not in self.chat_tracker:
                self.chat_tracker[attacker.steam_id] = {}
            self.chat_tracker[attacker.steam_id][target.steam_id] += (
                self.chat_tracker[attacker.steam_id].get(target.steam_id, 0) + dmg
            )
            attacker.center_print("^1Shoot Chatters = Insta-Ban")

    def handle_kill(self, victim, killer, _data):
        if not victim.state.is_chatting:
            return

        if killer is None:
            return
        
        if killer.steam_id not in self.chat_tracker:
            return

        if victim.steam_id not in self.chat_tracker[killer.steam_id]:
            return

        if self.chat_tracker[killer.steam_id][victim.steam_id] < 300:
            return

        killer.armor = 0
        killer.health = 1
        killer.weapons(
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
        killer.center_print("^1You have been warned!")
