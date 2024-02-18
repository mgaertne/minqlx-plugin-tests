import minqlx


# noinspection PyPep8Naming
class admin_votes(minqlx.Plugin):
    def __init__(self):
        super().__init__()

        self.mods_admins_voted = []

        self.add_hook("vote", self.process_vote, priority=minqlx.PRI_LOWEST)
        self.add_hook("vote_started", self.handle_vote_started)

    def process_vote(self, player, vote_yes_no):
        if not self.is_vote_active():
            return minqlx.RET_NONE

        if player.privileges not in ["root", "admin", "mod"]:
            return minqlx.RET_NONE

        if player.steam_id in self.mods_admins_voted:
            player.tell("Vote already cast.")
            return minqlx.RET_STOP_ALL

        if not self.get_cvar("g_allowSpecVote", bool) and player.team == "spectator":
            return minqlx.RET_STOP_ALL

        configstring_index = 10 if vote_yes_no else 11
        current_votes = int(minqlx.get_configstring(configstring_index))
        minqlx.set_configstring(configstring_index, f"{current_votes + 1}")

        self.mods_admins_voted.append(player.steam_id)
        return minqlx.RET_STOP_ALL

    def handle_vote_started(self, _player, _vote, _args):
        self.mods_admins_voted = []
