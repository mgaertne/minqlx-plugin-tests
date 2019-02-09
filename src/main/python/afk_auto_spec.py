import minqlx


class afk_auto_spec(minqlx.Plugin):
    """
    Uses:
    * qlx_autoSpecWarmup (default: False) whether to spec players during warmup
    """

    def __init__(self):
        super().__init__()

        self.add_hook("player_inactivity_kick", self.handle_player_inactive, priority=minqlx.PRI_HIGHEST)

        self.set_cvar_once("qlx_autoSpecWarmup", "0")

        self.spec_warmup = self.get_cvar("qlx_autoSpecWarmup", bool)

    def handle_player_inactive(self, player):
        if not self.game:
            return minqlx.RET_STOP_ALL

        if not self.spec_warmup and self.game.state != "in_progress":
            return minqlx.RET_STOP_ALL

        self.msg("^7Putting {}^7 to spec for inactivity.".format(player.name))
        player.put("spectator")
        return minqlx.RET_STOP_ALL
