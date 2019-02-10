import minqlx


class afk_auto_spec(minqlx.Plugin):
    """
    Uses:
    * qlx_autoSpecWarmup (default: False) whether to spec players during warmup
    """

    def __init__(self):
        super().__init__()

        self.add_hook("player_inactivity_kick_warning", self.handle_player_inactive_warning, priority=minqlx.PRI_HIGHEST)
        self.add_hook("player_inactivity_kick", self.handle_player_inactive, priority=minqlx.PRI_HIGHEST)

        self.set_cvar_once("qlx_autoSpecWarmup", "0")

        self.spec_warmup = self.get_cvar("qlx_autoSpecWarmup", bool)

    def validate_game(self, game):
        if not game:
            return False

        if not self.spec_warmup and game.state != "in_progress":
            return False

        return True

    def validate_player(self, game, player):
        if game.type_short != "ffa" and player.team not in ["red", "blue"]:
            return False

        if game.type_short == "ffa" and player.team not in ["free", "red", "blue"]:
            return False

        return True

    def handle_player_inactive_warning(self, player):
        if not self.validate_game(self.game):
            return minqlx.RET_STOP_ALL

        if not self.validate_player(self.game, player):
            return minqlx.RET_STOP_ALL

        warning_period = self.get_cvar("g_inactivityWarning", int)
        player.center_print("^1Knock! Knock!\n^7Putting you to spectator in {} seconds.".format(warning_period))
        return minqlx.RET_STOP_ALL

    def handle_player_inactive(self, player):
        if not self.validate_game(self.game):
            return minqlx.RET_STOP_ALL

        if not self.validate_player(self.game, player):
            return minqlx.RET_STOP_ALL

        self.msg("^7Putting {}^7 to spec for inactivity.".format(player.name))
        player.put("spectator")
        return minqlx.RET_STOP_ALL
