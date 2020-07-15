"""
This is a plugin created by ShiN0
Copyright (c) 2020 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.
"""

import minqlx

from minqlx.database import Redis

import requests

PLAYER_BASE = "minqlx:players:{0}"
IPS_BASE = "minqlx:ips"

class elocheck(minqlx.Plugin):
    """
    Checks qlstats for the elos of a player given as well as checking the elos of potentially aliases of the player
    by looking for connection from the same IP as the player has connected to locally.

    Uses:
    * qlx_elocheckPermission (default: "0") The permission for issuing the elocheck
    * qlx_elocheckReplyChannel (default: "public") The reply channel where the elocheck output is put to.
        Possible values: "public" or "private". Any other value leads to public announcements
    * qlx_elocheckShowSteamids (default: "0") Also lists the steam ids of the players checked
    """

    database = Redis

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_elocheckPermission", "0")
        self.set_cvar_once("qlx_elocheckReplyChannel", "public")
        self.set_cvar_once("qlx_elocheckShowSteamids", "0")

        self.reply_channel = self.get_cvar("qlx_elocheckReplyChannel")
        if self.reply_channel != "private":
            self.reply_channel = "public"
        self.show_steam_ids = self.get_cvar("qlx_elocheckShowSteamids", bool)

        self.add_command("elocheck", self.cmd_elocheck,
                         permission=self.get_cvar("qlx_elocheckPermission", int),
                         usage="[player or steam_id]")

    def cmd_elocheck(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.do_elocheck(player, msg[1], channel)

    @minqlx.thread
    def do_elocheck(self, player: minqlx.Player, target: str, channel: minqlx.AbstractChannel):
        target_players = self.find_target_player(target)

        target_steam_id = None

        if target_players is None or len(target_players) == 0:
            try:
                target_steam_id = int(target)

                if not self.db.exists(PLAYER_BASE.format(target_steam_id)):
                    player.tell("Sorry, player with steam id {} never played here.".format(target_steam_id))
                    return
            except ValueError:
                player.tell("Sorry, but no players matched your tokens: {}.".format(target))
                return

        if len(target_players) > 1:
            player.tell("A total of ^6{}^7 players matched for {}:".format(len(target_players), target))
            out = ""
            for p in target_players:
                out += " " * 2
                out += "{}^6:^7 {}\n".format(p.id, p.name)
            player.tell(out[:-1])
            return

        if len(target_players) == 1:
            target_steam_id = target_players.pop().steam_id

        reply_func = self.reply_func(player, channel)

        reply_func("{0}^7".format(self.format_player_elos(target_steam_id)))
        if not self.db.exists(PLAYER_BASE.format(target_steam_id) + ":ips"):
            return

        ips = self.db.smembers(PLAYER_BASE.format(target_steam_id) + ":ips")

        used_steam_ids = set()
        for ip in ips:
            if not self.db.exists(IPS_BASE + ":{0}".format(ip)):
                continue

            used_steam_ids = used_steam_ids | self.db.smembers(IPS_BASE + ":{0}".format(ip))

        if str(target_steam_id) in used_steam_ids:
            used_steam_ids.remove(str(target_steam_id))

        if len(used_steam_ids) == 0:
            return

        reply_func("Players from the same IPs:\n".format(self.format_player_elos(target_steam_id)))
        for steam_id in used_steam_ids:
            reply_func("{0}^7".format(self.format_player_elos(steam_id, indent=2)))

    def format_player_elos(self, steam_id, indent=0):
        a_elo = self.fetch_elos(steam_id, "elo")
        b_elo = self.fetch_elos(steam_id, "elo_b")

        result = " " * indent + "{0}^7\n".format(self.format_player_name(steam_id))
        if a_elo is not None and len(self.format_elos(a_elo)) > 0:
            result += " " * indent + "  " + "Elos: {0}\n".format(self.format_elos(a_elo))
        if b_elo is not None and len(self.format_elos(b_elo)) > 0:
            result += " " * indent + "  " + "B-Elos: {0}\n".format(self.format_elos(b_elo))

        return result

    def format_player_name(self, steam_id):
        result = ""

        player = self.player(steam_id)
        if player is not None:
            result += "{0}^7".format(player.name)
        elif self.db.exists(PLAYER_BASE.format(steam_id) + ":last_used_name"):
            result += "{0}^7".format(self.db[PLAYER_BASE.format(steam_id) + ":last_used_name"])
        else:
            result += "unknown"

        if self.show_steam_ids:
            result += " ({0})".format(steam_id)

        return result

    def format_elos(self, elos):
        result = ""

        for gametype in elos:
            if gametype == "steamid":
                continue
            if elos[gametype]["games"] != 0:
                result += "^2{0}^7: ^4{1}^7 ({2} games)  ".format(gametype.upper(), elos[gametype]["elo"], elos[gametype]["games"])
        return result

    def fetch_elos(self, steam_id, elo="elo"):
        url_base = "http://qlstats.net/"
        result = requests.get(url_base + "{}/{}".format(elo, steam_id))

        try:
            if result.status_code != requests.codes.ok:
                raise IOError("Invalid response code from qlstats.net.")
            js = result.json()

            if "players" not in js:
                raise IOError("Invalid response content from qlstats.net.")

            player_entry = [entry for entry in js["players"] if entry["steamid"] == str(steam_id)]

            if len(player_entry) <= 0:
                raise IOError("Response from qlstats.net did not include data for the requested player.")

            return player_entry[0]

        except Exception as e:
            minqlx.console_command("echo FakeCheckError: {}".format(e))

    def find_target_player(self, target: str):
        try:
            steam_id = int(target)

            target_player = self.player(steam_id)
            if target_player:
                return [target_player]
        except ValueError:
            pass
        except minqlx.NonexistentPlayerError:
            pass

        return self.find_player(target)

    def reply_func(self, player, channel):
        if self.reply_channel == "private":
            return player.tell
        return self.identify_reply_channel(channel).reply

    def identify_reply_channel(self, channel):
        if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                       minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
            return minqlx.CHAT_CHANNEL

        return channel
