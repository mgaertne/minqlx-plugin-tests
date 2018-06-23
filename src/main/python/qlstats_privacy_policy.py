import minqlx

"""
Plugin that restricts playing on the server to certain QLStats.net privacy settings.

Uses:
- set qlx_qlstatsPrivacyKick (default: 0), set to 1 to kick any clients with unallowed privacy settings upon connect.
- set qlx_qlstatsPrivacyWhitelist (default: "public, anoynmous, private, untracked")
    List of allowed privacy settings on this server. Take out any value from the default expansive list.
"""

COLORED_QLSTATS_INSTRUCTIONS = "Go to ^2https://qlstats.net/account/login^7 " \
                       "and set ^2Privacy Settings^7 to either of these: ^6{}^7, " \
                       "click ^2Save Settings^7, then reconnect."

class qlstats_privacy_policy(minqlx.Plugin):

    def __init__(self):
        if 'balance' not in minqlx.Plugin._loaded_plugins:
            self.logger.log("Balance plugin not loaded. "
                            "This plugin just work with the balance plugin in place.")
            raise minqlx.PluginLoadError("Balance plugin not loaded. "
                                         "This plugin just work with the balance plugin in place.")

        if not hasattr(self.plugins["balance"], "player_info"):
            self.logger.log("Wrong version of the ^6balance^7 plugin loaded. Make sure to load "
                            "https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py.")
            raise minqlx.PluginLoadError("Wrong version of the balance plugin loaded. Make sure to load "
                                         "https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py.")

        self.set_cvar_once("qlx_qlstatsPrivacyKick", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, anonymous, private, untracked")

        self.kick_players = self.get_cvar("qlx_qlstatsPrivacyKick", bool)
        self.allowed_privacy = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list)

        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)

    @minqlx.delay(5)
    def handle_player_connect(self, player):
        b = minqlx.Plugin._loaded_plugins['balance']
        b.add_request({player.steam_id: self.game.type_short}, self.callback_connect, minqlx.CHAT_CHANNEL)

    def callback_connect(self, players, channel):
        if not self.kick_players:
            return

        player_info = self.plugins["balance"].player_info

        for sid in players:
            if sid not in player_info:
                continue
            if player_info[sid]["privacy"] not in self.allowed_privacy:
                self.delayed_kick(sid, minqlx.Plugin.clean_text(self.colored_qlstats_instructions()))

    def colored_qlstats_instructions(self):
        return COLORED_QLSTATS_INSTRUCTIONS.format("^7, ^6".join(self.allowed_privacy))

    @minqlx.delay(5)
    def delayed_kick(self, sid, reason):
        self.kick(sid, reason)

    def handle_team_switch_attempt(self, player, old, new):
        if not self.game:
            return

        if new in ["red", "blue", "any"]:
            player_info = self.plugins["balance"].player_info
            if player.steam_id not in player_info:
                player.tell("We couldn't fetch your ratings, yet. You will not be able to join, until we did.")
                return minqlx.RET_STOP_ALL
            if player_info[player.steam_id]["privacy"] not in self.allowed_privacy:
                self.msg("{}^7, you're not allowed to join any team "
                         "for incorrect or missing QLStats.net privacy settings on this server.".format(player.name))
                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell(self.colored_qlstats_instructions())
                if old in ["spectator", "free"]:
                    return minqlx.RET_STOP_ALL

                player.put("spectator")

