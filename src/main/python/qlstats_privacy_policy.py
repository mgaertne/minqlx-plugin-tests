import minqlx

"""
Plugin that restricts playing on the server to certain QLStats.net privacy settings.

Uses:
- set qlx_qlstatsPrivacyKick (default: 0), set to 1 to kick any clients with unallowed privacy settings upon connect.
- set qlx_qlstatsPrivacyWhitelist (default: "public, anoynmous, private, untracked") 
    List of allowed privacy settings on this server. Take out any value from the default expansive list.
"""


class qlstats_privacy_policy(minqlx.Plugin):

    def __init__(self):
        self.set_cvar_once("qlx_qlstatsPrivacyKick", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, anonymous, private, untracked")

        self.kick_players = self.get_cvar("qlx_qlstatsPrivacyKick", bool)
        self.allowed_privacy = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list)

        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)

    @minqlx.delay(5)
    def handle_player_connect(self, player):
        if 'balance' in minqlx.Plugin._loaded_plugins:
            b = minqlx.Plugin._loaded_plugins['balance']
            b.add_request({player.steam_id: self.game.type_short}, self.callback_connect, minqlx.CHAT_CHANNEL)
        else:
            self.msg("^7Couldn't fetch ratings for {}^7, make sure ^6balance^7 is loaded.".format(player.name))

    def callback_connect(self, players, channel):
        if not self.kick_players:
            return

        player_info = self.plugins["balance"].player_info

        for sid in players:
            if player_info[sid]["privacy"] not in self.allowed_privacy:
                self.delayed_kick(sid, "Go to ^2https://qlstats.net/account/login^7 "
                                       "and set ^2Privacy Settings^7 to either of these: ^2{}^^7, "
                                       "click ^2Save Settings^7, then reconnect"
                                  .format("^7, ^2".join(self.allowed_privacy)))

    @minqlx.delay(5)
    def delayed_kick(self, sid, reason):
        self.kick(sid, reason)

    def handle_player_disconnect(self, player, reason):
        if 'balance' in minqlx.Plugin._loaded_plugins:
            if player.steam_id in self.plugins["balance"].player_info:
                del self.plugins["balance"].player_info[player.steam_id]
            if player.steam_id in self.plugins["balance"].ratings:
                del self.plugins["balance"].ratings[player.steam_id]

    def handle_team_switch_attempt(self, player, old, new):
        if not self.game:
            return

        if new in ["red", "blue", "any"]:
            player_info = self.plugins["balance"].player_info
            if player_info[player.steam_id]["privacy"] not in self.allowed_privacy:
                self.msg("{}^7, you're not allowed to join any team "
                         "for disallowed QLStats privacy settings on this server.".format(player.name))
                player.tell("Go to ^2https://qlstats.net/account/login^7 "
                            "and set ^2Privacy Settings^7 to either of these: ^2{}^7, "
                            "click ^2Save Settings^7, then reconnect."
                            .format("^7, ^2".join(self.allowed_privacy)))
                if old in ["spectators", "free"]:
                    return minqlx.RET_STOP_ALL

                player.put("spectators")
