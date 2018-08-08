import minqlx

"""
Plugin that restricts playing on the server to certain QLStats.net privacy settings.

Uses:
- set qlx_qlstatsPrivacyKick (default: 0), set to 1 to kick any clients with unallowed privacy settings upon connect.
- set qlx_qlstatsPrivacyWhitelist (default: "public, anoynmous, private, untracked")
    List of allowed privacy settings on this server. Take out any value from the default expansive list.
"""

COLORED_QLSTATS_INSTRUCTIONS = "Open qlstats.net, click log in, choose either of these: ^6{}^7, " \
                               "click save and reconnect!"


class qlstats_privacy_policy(minqlx.Plugin):

    def __init__(self):
        super().__init__()
        self.set_cvar_once("qlx_qlstatsPrivacyKick", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, anonymous, private, untracked")

        self.plugin_enabled = True
        self.kick_players = self.get_cvar("qlx_qlstatsPrivacyKick", bool)
        self.allowed_privacy = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list)

        self.exceptions = set()

        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)

        self.add_command(("except", "e"), self.cmd_policy_exception, permission=5, usage="<player>")
        self.add_command("privacy", self.cmd_switch_plugin, permission=1, usage="[status]")

    def check_balance_plugin_loaded(self):
        return 'balance' in self.plugins

    def check_for_right_version_of_balance_plugin(self):
        return hasattr(self.plugins["balance"], "player_info")

    def check_for_correct_balance_plugin(self):
        if not self.check_balance_plugin_loaded():
            self.logger.info("Balance plugin not loaded. "
                             "This plugin just works with the balance plugin in place.")
            return False

        if not self.check_for_right_version_of_balance_plugin():
            self.logger.info("Wrong version of the ^6balance^7 plugin loaded. Make sure to load "
                             "https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py.")
            return False

        return True

    @minqlx.delay(5)
    def handle_player_connect(self, player):
        if not self.game:
            return

        if not self.check_for_correct_balance_plugin():
            self.disable_policy_check(minqlx.CHAT_CHANNEL)
            return

        b = minqlx.Plugin._loaded_plugins['balance']
        b.add_request({player.steam_id: self.game.type_short}, self.callback_connect, minqlx.CHAT_CHANNEL)

    def callback_connect(self, players, channel):
        if not self.plugin_enabled:
            return

        if not self.kick_players:
            return

        player_info = self.plugins["balance"].player_info

        for sid in players:
            if sid in self.exceptions:
                continue

            if sid not in player_info:
                continue

            if player_info[sid]["privacy"] not in self.allowed_privacy:
                self.delayed_kick(sid, minqlx.Plugin.clean_text(self.colored_qlstats_instructions()))

    def colored_qlstats_instructions(self):
        return COLORED_QLSTATS_INSTRUCTIONS.format("^7, ^6".join(self.allowed_privacy))

    @minqlx.delay(5)
    def delayed_kick(self, sid, reason):
        self.kick(sid, reason)

    def handle_player_disconnect(self, player, reason):
        if player.steam_id in self.exceptions:
            self.exceptions.remove(player.steam_id)

    def handle_team_switch_attempt(self, player, old, new):
        if not self.plugin_enabled:
            return

        if not self.game:
            return

        if player.steam_id in self.exceptions:
            return

        if not self.check_for_correct_balance_plugin():
            self.disable_policy_check(minqlx.CHAT_CHANNEL)
            return

        if new in ["red", "blue", "any"]:
            player_info = self.plugins["balance"].player_info
            if player.steam_id not in player_info:
                player.tell("We couldn't fetch your ratings, yet. You will not be able to join, until we did.")
                return minqlx.RET_STOP_ALL
            if player_info[player.steam_id]["privacy"] not in self.allowed_privacy:
                self.msg("{}^7 not allowed to join due to {} QLStats.net privacy settings."
                         .format(player.name, player_info[player.steam_id]["privacy"].lower()))
                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell("Not allowed to join due to ^6{}1^7 QLStats.net data."
                            .format(player_info[player.steam_id]["privacy"].lower()))
                player.tell(self.colored_qlstats_instructions())
                if old in ["spectator", "free"]:
                    return minqlx.RET_STOP_ALL

                player.put("spectator")

    def cmd_policy_exception(self, player, msg, channel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        teams = self.teams()
        speccing_players = teams["spectator"] + teams["free"]
        except_player = self.find_player(msg[1], speccing_players)

        if except_player is None or len(except_player) == 0:
            player.tell("^7Could not find player identified by ^1{}^7.".format(msg[1]))
            return

        if len(except_player) > 1:
            player.tell("^7More than one matching spectator found: {}"
                        .format("^7, ".join([player.name for player in except_player])))
            player.tell("^7Please be more specific which one to put on the exception list!")
            return

        channel.reply("^7An admin has allowed ^2{}^7 to temporarily join despite missing or "
                      "inadequate qlstats privacy information."
                      .format(except_player[0].clean_name))
        self.exceptions.add(except_player[0].steam_id)

    def cmd_switch_plugin(self, player, msg, channel):
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 2:
            if msg[1] != "status":
                return minqlx.RET_USAGE

            channel.reply("^7QLStats policy check is {}".format("enabled" if self.plugin_enabled else "disabled"))
            return

        if not self.plugin_enabled:
            self.enable_policy_check(channel)
            return

        self.disable_policy_check(channel)

    def disable_policy_check(self, channel):
        self.plugin_enabled = False
        channel.reply("^7QLStats policy check disabled. Everyone will be able to join.")

    def enable_policy_check(self, channel):
        if not self.check_for_correct_balance_plugin():
            return

        self.plugin_enabled = True
        channel.reply("^7QLStats policy check enabled.")

        if self.kick_players:
            self.callback_connect(
                {player.steam_id: self.game.type_short for player in self.players()}, channel)
            return

        teams = self.teams()
        player_info = self.plugins["balance"].player_info

        for player in teams["red"] + teams["blue"]:
            if player.steam_id not in player_info:
                player.tell("We couldn't fetch your ratings, yet. You will not be able to play, until we did.")
                player.put("spectator")
                continue

            if player_info[player.steam_id]["privacy"] not in self.allowed_privacy:
                self.msg("{}^7 not allowed to join due to {} QLStats.net privacy settings."
                         .format(player.name, player_info[player.steam_id]["privacy"].lower()))
                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell("Not allowed to join due to ^6{}1 7 QLStats.net data."
                            .format(player_info[player.steam_id]["privacy"].lower()))
                player.tell(self.colored_qlstats_instructions())
                player.put("spectator")
