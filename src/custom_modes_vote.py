import minqlx

from minqlx import Plugin

game_settings = {
    "dmflags": {'pql': '60', 'vql': '28'},
    "g_knockback_pg": {'pql': '1.25', 'vql': '1.10'},
    "g_knockback_rl": {'pql': '1.10', 'vql': '0.90'},
    "g_knockback_z": {'pql': '40', 'vql': '1000'},
    "g_max_knockback": {'pql': '160', 'vql': '120'},
    "g_respawn_delay_max": {'pql': '3500', 'vql': '2400'},
    "g_splashradius_pg": {'pql': '32', 'vql': '20'},
    "g_velocity_gl": {'pql': '800', 'vql': '700'},
    "pmove_AirControl": {'pql': '1', 'vql': '0'},
    "pmove_RampJump": {'pql': '1', 'vql': '0'},
    "pmove_WeaponRaiseTime": {'pql': '10', 'vql': '200'},
    "pmove_WeaponDropTime": {'pql': '10', 'vql': '200'},
    "weapon_reload_rg": {'pql': '1250', 'vql': '1500'},
    "weapon_reload_sg": {'pql': '950', 'vql': '1000'},
    "pmove_BunnyHop": {'pql': '0', 'vql': '1'},
    "pmove_CrouchStepJump": {'pql': '0', 'vql': '1'},
    "pmove_JumpTimeDeltaMin": {'pql': '50', 'vql': '100.0f'},
    "pmove_WaterSwimScale": {'pql': '0.5f', 'vql': '0.6f'},
    "pmove_WaterWadeScale": {'pql': '0.75f', 'vql': '0.8f'}
}


# noinspection PyPep8Naming
class custom_modes_vote(minqlx.Plugin):
    """
    This plugin allows switching to customizable game modes, ships with vanilla QL settings and PQL promode settings

    Uses:
    * qlx_modeVoteNewMapDefault (default: "pql") Default game mode upon new map loading, set to None to keep the
    previous map's mode even with the new map.
    """

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_modeVoteNewMapDefault", "pql")

        self.default_mode = self.get_cvar("qlx_modeVoteNewMapDefault", str)

        self.add_hook("map", self.handle_map_change)
        self.add_hook("vote_called", self.handle_vote_called)
        self.add_hook("vote_ended", self.handle_vote_ended, priority=minqlx.PRI_LOWEST)

        self.add_command("mode", self.cmd_switch_mode, permission=5,
                         usage=f"!mode [{'|'.join(self.available_modes())}]")

        self.mode = self.default_mode or ""

    # noinspection PyMethodMayBeStatic
    def available_modes(self):
        keys = set()
        for value in game_settings.values():
            for key in value.keys():
                keys.add(key)

        return keys

    def handle_map_change(self, _mapname, _factory):
        if self.default_mode and self.mode != self.default_mode:
            self.switch_mode(self.default_mode)

    def handle_vote_called(self, caller, vote, args):
        if vote.lower() != "mode":
            return minqlx.RET_NONE

        if args.lower() not in self.available_modes():
            return minqlx.RET_NONE

        if args.lower() == self.mode.lower():
            return minqlx.RET_STOP_ALL

        Plugin.callvote(f"mode {args.lower()}", f"mode {args.lower()}")
        minqlx.client_command(caller.id, "vote yes")

        self.msg(f"{caller.name}^7 called a vote.")
        return minqlx.RET_STOP_ALL

    def handle_vote_ended(self, _votes, vote, args, passed):
        if vote.lower() != "mode":
            return

        if args.lower() not in self.available_modes():
            return

        if not passed:
            return

        self.switch_mode(args.lower())

    def cmd_switch_mode(self, _player, msg, _channel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        if msg[1].lower() not in self.available_modes():
            return minqlx.RET_USAGE

        self.switch_mode(msg[1].lower())
        return minqlx.RET_NONE

    def switch_mode(self, mode):
        self.mode = mode
        for setting, values in game_settings.items():
            minqlx.console_command(f"{setting} {values[mode]}")
        self.msg(f"{mode.upper()} settings loaded!")
        self.center_print(f"{mode.upper()} settings loaded!")
