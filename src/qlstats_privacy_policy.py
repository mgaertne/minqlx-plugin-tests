from typing import TYPE_CHECKING
import threading

import requests
from requests import Response

import minqlx
from minqlx import Player, AbstractChannel

if TYPE_CHECKING:
    from typing import Set, Dict

    SteamId = int

COLORED_QLSTATS_INSTRUCTIONS = "Error: Open qlstats.net, click Login/Sign-up, set privacy settings to ^6{}^7, " \
                               "click save and reconnect!"


# noinspection PyPep8Naming
class qlstats_privacy_policy(minqlx.Plugin):
    """
    Plugin that restricts playing on the server to certain QLStats.net privacy settings.

    Uses:
    - qlx_qlstatsPrivacyKick (default: 0), set to 1 to kick any clients with unallowed privacy settings upon connect.
    - qlx_qlstatsPrivacyWhitelist (default: "public, private, untracked")
        List of allowed privacy settings on this server. Take out any value from the default expansive list.
    - qlx_qlstatsPrivacyJoinAttempts (default: 5), amount of join attempts before the player gets kicked,
        if privacyKick is disabled. Set to -1 to disable kicking of players for their join attempts.
    """

    def __init__(self) -> None:
        super().__init__()
        self.set_cvar_once("qlx_qlstatsPrivacyBlock", "1")
        self.set_cvar_once("qlx_qlstatsPrivacyKick", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, private, untracked")
        self.set_cvar_once("qlx_qlstatsPrivacyJoinAttempts", "5")

        self.plugin_enabled = True
        self.kick_players = self.get_cvar("qlx_qlstatsPrivacyKick", bool)
        self.allowed_privacy = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list) or ["public", "private", "untracked"]
        self.max_num_join_attempts = self.get_cvar("qlx_qlstatsPrivacyJoinAttempts", int) or 5

        self.exceptions: Set[SteamId] = set()
        self.join_attempts: Dict[SteamId, int] = {}

        # Collection of threads looking up elo of players {steam_id: thread }
        self.connectthreads: Dict[SteamId, ConnectThread] = {}

        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_HIGHEST)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)

        self.add_command(("except", "e"), self.cmd_policy_exception, permission=5, usage="<player>")
        self.add_command("privacy", self.cmd_switch_plugin, permission=1, usage="[status]")

    def check_balance_plugin_loaded(self) -> bool:
        return 'balance' in self.plugins

    def check_for_right_version_of_balance_plugin(self) -> bool:
        return hasattr(self.plugins["balance"], "player_info")

    def check_for_correct_balance_plugin(self) -> bool:
        if not self.check_balance_plugin_loaded():
            self.logger.info("Balance plugin not loaded. "
                             "This plugin just works with the balance plugin in place.")
            return False

        if not self.check_for_right_version_of_balance_plugin():
            self.logger.info("Wrong version of the ^6balance^7 plugin loaded. Make sure to load "
                             "https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py.")
            return False

        return True

    def handle_player_connect(self, player: Player) -> int | str:
        if not self.plugin_enabled:
            return minqlx.RET_NONE

        if not self.game:
            return minqlx.RET_NONE

        if not self.check_for_correct_balance_plugin():
            self.disable_policy_check(minqlx.CHAT_CHANNEL)
            return minqlx.RET_NONE

        b = minqlx.Plugin._loaded_plugins['balance']   # pylint: disable=protected-access
        # noinspection PyUnresolvedReferences
        b.add_request(  # type: ignore
            {player.steam_id: self.game.type_short}, self.callback_connect, minqlx.CHAT_CHANNEL)

        if not self.get_cvar("qlx_qlstatsPrivacyBlock", bool):
            return minqlx.RET_NONE

        if player.steam_id not in self.connectthreads:
            ct = ConnectThread(player.steam_id, self.get_cvar("qlx_balanceApi") or "elo")
            self.connectthreads[player.steam_id] = ct
            ct.start()
            self.remove_thread(player.steam_id)  # remove it after a while

        # Check if thread is ready or not
        ct = self.connectthreads[player.steam_id]
        if ct.is_alive():
            return "Fetching your qlstats settings..."

        # Check if thread is ready or not
        try:
            # noinspection PyProtectedMember
            res = ct._result  # pylint: disable=protected-access
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

        except Exception as e:  # pylint: disable=broad-except
            minqlx.console_command(f"echo QLStatsPrivacyError: {e}")

        return minqlx.RET_NONE

    def callback_connect(self, players: Dict[SteamId, str], _channel: AbstractChannel) -> None:
        if not self.plugin_enabled:
            return

        if not self.kick_players:
            return

        # noinspection PyUnresolvedReferences
        player_info = self._loaded_plugins["balance"].player_info  # type: ignore

        for sid in players:
            if sid in self.exceptions:
                continue

            if sid not in player_info:
                continue

            if player_info[sid]["privacy"] not in self.allowed_privacy:
                self.delayed_kick(sid, minqlx.Plugin.clean_text(self.colored_qlstats_instructions()))

    def colored_qlstats_instructions(self) -> str:
        return COLORED_QLSTATS_INSTRUCTIONS.format("^7, ^6".join(self.allowed_privacy))

    @minqlx.delay(5)
    def delayed_kick(self, sid: SteamId, reason: str) -> None:
        self.kick(sid, reason)

    def handle_player_disconnect(self, player: Player, _reason: str) -> None:
        if player.steam_id in self.exceptions:
            self.exceptions.remove(player.steam_id)

        if player.steam_id in self.join_attempts:
            del self.join_attempts[player.steam_id]

    def handle_team_switch_attempt(self, player: Player, old: str, new: str) -> int:
        if not self.plugin_enabled:
            return minqlx.RET_NONE

        if not self.game:
            return minqlx.RET_NONE

        if player.steam_id in self.exceptions:
            return minqlx.RET_NONE

        if not self.check_for_correct_balance_plugin():
            self.disable_policy_check(minqlx.CHAT_CHANNEL)
            return minqlx.RET_NONE

        if new in ["red", "blue", "any"]:
            # noinspection PyUnresolvedReferences
            player_info = self._loaded_plugins["balance"].player_info  # type: ignore
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
                    self.msg(f"{player.name}^7 not allowed to join due to "
                             f"{player_info[player.steam_id]['privacy'].lower()} QLStats.net privacy settings. "
                             f"{self.join_attempts[player.steam_id]} join attempts before automatically kicking you.")
                    player.tell(f"Not allowed to join due to ^6{player_info[player.steam_id]['privacy'].lower()}^7 "
                                f"QLStats.net data. {self.join_attempts[player.steam_id]} join attempts before "
                                f"automatically kicking you.")
                else:
                    self.msg(f"{player.name}^7 not allowed to join due to "
                             f"{player_info[player.steam_id]['privacy'].lower()} QLStats.net privacy settings. ")
                    player.tell(f"Not allowed to join due to ^6{player_info[player.steam_id]['privacy'].lower()}^7 "
                                f"QLStats.net data. ")

                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell(self.colored_qlstats_instructions())

                if old in ["spectator", "free"]:
                    return minqlx.RET_STOP_ALL

                player.put("spectator")
        return minqlx.RET_NONE

    def cmd_policy_exception(self, player: Player, msg: str, channel: AbstractChannel) -> int:
        if len(msg) != 2:
            return minqlx.RET_USAGE

        teams = self.teams()
        speccing_players = teams["spectator"] + teams["free"]
        except_player = self.find_player(msg[1], speccing_players)

        if except_player is None or len(except_player) == 0:
            player.tell(f"^7Could not find player identified by ^1{msg[1]}^7.")
            return minqlx.RET_NONE

        if len(except_player) > 1:
            player_names = "^7, ".join([player.name for player in except_player])
            player.tell(f"^7More than one matching spectator found: {player_names}")
            player.tell("^7Please be more specific which one to put on the exception list!")
            return minqlx.RET_NONE

        channel.reply(f"^7An admin has allowed ^2{except_player[0].clean_name}^7 to temporarily join "
                      f"despite missing or inadequate qlstats privacy information.")
        self.exceptions.add(except_player[0].steam_id)
        return minqlx.RET_NONE

    def cmd_switch_plugin(self, _player: Player, msg: str, channel: AbstractChannel) -> int:
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 2:
            if msg[1] != "status":
                return minqlx.RET_USAGE

            enabled_or_disabled = "enabled" if self.plugin_enabled else "disabled"
            channel.reply(f"^7QLStats policy check is {enabled_or_disabled}")
            return minqlx.RET_NONE

        if not self.plugin_enabled:
            self.enable_policy_check(channel)
            return minqlx.RET_NONE

        self.disable_policy_check(channel)
        return minqlx.RET_NONE

    def disable_policy_check(self, channel: AbstractChannel) -> None:
        self.plugin_enabled = False
        channel.reply("^7QLStats policy check disabled. Everyone will be able to join.")

    def enable_policy_check(self, channel: AbstractChannel) -> None:
        if not self.check_for_correct_balance_plugin():
            return

        self.plugin_enabled = True
        channel.reply("^7QLStats policy check enabled.")

        if not self.game:
            return

        if self.kick_players:
            self.callback_connect(
                {player.steam_id: self.game.type_short for player in self.players()}, channel)
            return

        teams = self.teams()
        # noinspection PyUnresolvedReferences
        player_info = self._loaded_plugins["balance"].player_info  # type: ignore

        for player in teams["red"] + teams["blue"]:
            if player.steam_id not in player_info:
                player.tell("We couldn't fetch your ratings, yet. You will not be able to play, until we did.")
                player.put("spectator")
                continue

            if player_info[player.steam_id]["privacy"] not in self.allowed_privacy:
                self.msg(f"{player.name}^7 not allowed to join due to "
                         f"{player_info[player.steam_id]['privacy'].lower()} QLStats.net privacy settings.")
                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell(f"Not allowed to join due to ^6{player_info[player.steam_id]['privacy'].lower()}^7 "
                            f"QLStats.net data.")
                player.tell(self.colored_qlstats_instructions())
                player.put("spectator")

    @minqlx.delay(30)  # 30 seconds
    def remove_thread(self, sid: SteamId) -> None:
        if sid in self.connectthreads:
            del self.connectthreads[sid]


class ConnectThread(threading.Thread):

    def __init__(self, steam_id: SteamId, balance_api: str) -> None:
        super().__init__()
        self._balance_api = balance_api
        self._steam_id = steam_id
        self._result: Response | None = None

    def run(self) -> None:
        url = f"http://qlstats.net/{self._balance_api}/{self._steam_id}"
        self._result = requests.get(url, timeout=15)