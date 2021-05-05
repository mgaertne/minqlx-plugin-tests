import minqlx

import requests
import threading

"""
Plugin that restricts playing on the server to certain QLStats.net privacy settings.

Uses:
- qlx_qlstatsPrivacyKick (default: 0), set to 1 to kick any clients with unallowed privacy settings upon connect.
- qlx_qlstatsPrivacyWhitelist (default: "public, anonymous, private, untracked")
    List of allowed privacy settings on this server. Take out any value from the default expansive list.
- qlx_qlstatsPrivacyJoinAttempts (default: 5), amount of join attempts before the player gets kicked,
    if privacyKick is disabled. Set to -1 to disable kicking of players for their join attempts.
"""

COLORED_QLSTATS_INSTRUCTIONS = "Error: Open qlstats.net, click Login/Sign-up, set privacy settings to ^6{}^7, " \
                               "click save and reconnect!"


class qlstats_privacy_policy(minqlx.Plugin):

    def __init__(self):
        super().__init__()
        self.set_cvar_once("qlx_qlstatsPrivacyBlock", "1")
        self.set_cvar_once("qlx_qlstatsPrivacyKick", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, anonymous, private, untracked")
        self.set_cvar_once("qlx_qlstatsPrivacyJoinAttempts", "5")

        self.plugin_enabled = True
        self.kick_players = self.get_cvar("qlx_qlstatsPrivacyKick", bool)
        self.allowed_privacy = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list)
        self.max_num_join_attempts = self.get_cvar("qlx_qlstatsPrivacyJoinAttempts", int)

        self.exceptions = set()
        self.join_attempts = dict()

        # Collection of threads looking up elo of players {steam_id: thread }
        self.connectthreads = {}

        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_HIGHEST)
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

    def handle_player_connect(self, player):
        if not self.plugin_enabled:
            return

        if not self.game:
            return

        if not self.check_for_correct_balance_plugin():
            self.disable_policy_check(minqlx.CHAT_CHANNEL)
            return

        b = minqlx.Plugin._loaded_plugins['balance']
        b.add_request({player.steam_id: self.game.type_short}, self.callback_connect, minqlx.CHAT_CHANNEL)

        if not self.get_cvar("qlx_qlstatsPrivacyBlock", bool):
            return

        if player.steam_id not in self.connectthreads:
            ct = ConnectThread(player.steam_id, self.get_cvar("qlx_balanceApi"))
            self.connectthreads[player.steam_id] = ct
            ct.start()
            self.remove_thread(player.steam_id)  # remove it after a while

        # Check if thread is ready or not
        ct = self.connectthreads[player.steam_id]
        if ct.isAlive():
            return "Fetching your qlstats settings..."

        # Check if thread is ready or not
        try:
            res = ct._result
            if not res:
                return "Fetching your qlstats settings..."

            if res.status_code != requests.codes.ok:
                raise IOError("Invalid response code from qlstats.net.")
            self.logger.debug(res.text)
            js = res.json()

            if "playerinfo" not in js:
                raise IOError("Invalid response content from qlstats.net.")

            if str(player.steam_id) not in js["playerinfo"]:
                raise IOError("Response from qlstats.net did not include data for the requested player.")

            if "privacy" not in js["playerinfo"][str(player.steam_id)]:
                raise IOError("Response from qlstats.net did not include privacy information.")

            if js["playerinfo"][str(player.steam_id)]["privacy"] not in self.allowed_privacy:
                return minqlx.Plugin.clean_text(self.colored_qlstats_instructions())

        except Exception as e:
            minqlx.console_command("echo QLStatsPrivacyError: {}".format(e))

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

        if player.steam_id in self.join_attempts:
            del self.join_attempts[player.steam_id]

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
                if self.max_num_join_attempts > 0:
                    if player.steam_id not in self.join_attempts:
                        self.join_attempts[player.steam_id] = self.max_num_join_attempts

                    self.join_attempts[player.steam_id] -= 1

                    if self.join_attempts[player.steam_id] < 0:
                        player.kick(minqlx.Plugin.clean_text(self.colored_qlstats_instructions()))
                        return minqlx.RET_STOP_ALL
                    self.msg("{}^7 not allowed to join due to {} QLStats.net privacy settings. "
                             "{} join attempts before automatically kicking you."
                             .format(player.name, player_info[player.steam_id]["privacy"].lower(),
                                     self.join_attempts[player.steam_id]))
                    player.tell("Not allowed to join due to ^6{}1^7 QLStats.net data. "
                                "{} join attempts before automatically kicking you."
                                .format(player_info[player.steam_id]["privacy"].lower(),
                                        self.join_attempts[player.steam_id]))
                else:
                    self.msg("{}^7 not allowed to join due to {} QLStats.net privacy settings. "
                             .format(player.name, player_info[player.steam_id]["privacy"].lower()))
                    player.tell("Not allowed to join due to ^6{}1^7 QLStats.net data. "
                                .format(player_info[player.steam_id]["privacy"].lower()))

                player.center_print("^3Join not allowed. See instructions in console!")
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

    @minqlx.delay(30)  # 30 seconds
    def remove_thread(self, sid):
        if sid in self.connectthreads:
            del self.connectthreads[sid]


class ConnectThread(threading.Thread):

    def __init__(self, steam_id, balance_api):
        super(ConnectThread, self).__init__()
        self._balance_api = balance_api
        self._steam_id = steam_id
        self._result = None

    def run(self):
        url = "http://qlstats.net/{elo}/{}".format(self._steam_id, elo=self._balance_api)
        self._result = requests.get(url)
