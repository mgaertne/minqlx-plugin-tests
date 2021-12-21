"""
This is a plugin created by ShiN0
Copyright (c) 2020 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.
"""

import minqlx
from minqlx import Plugin

from minqlx.database import Redis

import os
import math
import time
import random
import itertools
import threading

from abc import abstractmethod

from operator import itemgetter

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

PLAYER_BASE = "minqlx:players:{0}"
IPS_BASE = "minqlx:ips"

SUPPORTED_GAMETYPES = ("ad", "ca", "ctf", "dom", "ft", "tdm")


def requests_retry_session(
        retries=3,
        backoff_factor=0.1,
        status_forcelist=(500, 502, 504),
        session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class balancetwo(minqlx.Plugin):
    """
    Checks qlstats for the elos of a player given as well as checking the elos of potentially aliases of the player
    by looking for connection from the same IP as the player has connected to locally.

    Uses:
    * qlx_balancetwo_ratingSystem (default: "mapbased-truskills") Either "mapbased-truskills", "truskills", "a-elo",
    "b-elo".
    In the future there might be a "custom" option for other rating providers.
    * qlx_balancetwo_ratingLimit_min (default: "15") minimum rating for players trying to connect
    * qlx_balancetwo_ratingLimit_max (default: "35") maximum rating for players trying to connect
    * qlx_balancetwo_ratingLimit_minGames (default: "10") minimum amount of rated games for player trying to connect
    * qlx_balancetwo_ratingStrategy (default: "") unused at the moment. For future use
    * qlx_balancetwo_autoSwitch (default: "0") automatically execute suggested switches rather than waiting for !agree
    from players.
    * qlx_balancetwo_uniquePlayerSwitches (default: "0") During a game, avoid switches that already happened during the
    same game
    * qlx_balancetwo_autoRebalance (default: "1") When new players join, the new players are automatically put on teams
    that result in the lower difference between the the teams.
    * qlx_balancetwo_elocheckPermission (default: "0") The permission for issuing the elocheck
    * qlx_balancetwo_elocheckReplyChannel (default: "public") The reply channel where the elocheck output is put to.
        Possible values: "public" or "private". Any other value leads to public announcements
    * qlx_balancetwo_elocheckShowSteamids (default: "0") Also lists the steam ids of the players checked
    """

    database = Redis

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_balancetwo_ratingSystem", "mapbased-truskills")

        self.set_cvar_once("qlx_balancetwo_ratingLimit_kick", "1")

        self.set_cvar_once("qlx_balancetwo_ratingLimit_min", "15")
        self.set_cvar_once("qlx_balancetwo_ratingLimit_max", "35")
        self.set_cvar_once("qlx_balancetwo_ratingLimit_minGames", "10")

        self.set_cvar_once("qlx_balancetwo_elocheckPermission", "0")
        self.set_cvar_once("qlx_balancetwo_elocheckReplyChannel", "public")
        self.set_cvar_once("qlx_balancetwo_elocheckShowSteamids", "0")

        # indicates whether switch suggestions need to be opted-in (!a) or vetoed (!v) by the suggested players
        self.set_cvar_once("qlx_balancetwo_autoSwitch", "0")
        # if set to true, this avoids suggesting the same players for switching in the same game twice, might lead to
        # fewer possible suggestions
        self.set_cvar_once("qlx_balancetwo_uniquePlayerSwitches", "0")
        self.set_cvar_once("qlx_balancetwo_minimumSuggestionDiff", "25")
        self.set_cvar_once("qlx_balancetwo_minimumStddevDiff", "50")

        self.set_cvar_once("qlx_balancetwo_autoRebalance", "1")

        self.ratingLimit_kick = self.get_cvar("qlx_balancetwo_ratingLimit_kick", bool)

        self.ratingLimit_min = self.get_cvar("qlx_balancetwo_ratingLimit_min", int)
        self.ratingLimit_max = self.get_cvar("qlx_balancetwo_ratingLimit_max", int)
        self.ratingLimit_minGames = self.get_cvar("qlx_balancetwo_ratingLimit_minGames", int)

        self.reply_channel = self.get_cvar("qlx_balancetwo_elocheckReplyChannel")
        if self.reply_channel != "private":
            self.reply_channel = "public"
        self.show_steam_ids = self.get_cvar("qlx_balancetwo_elocheckShowSteamids", bool)

        self.auto_switch = self.get_cvar("qlx_balancetwo_autoSwitch", bool)
        self.unique_player_switches = self.get_cvar("qlx_balancetwo_uniquePlayerSwitches", bool)

        self.minimum_suggestion_diff = self.get_cvar("qlx_balancetwo_minimumSuggestionDiff", float)
        self.minimum_suggestion_stddev_diff = self.get_cvar("qlx_balancetwo_minimumStddevDiff", int)

        self.auto_rebalance = self.get_cvar("qlx_balancetwo_autoRebalance", bool)

        self.add_command(("elocheck", "getrating", "getelo", "elo"), self.cmd_elocheck,
                         permission=self.get_cvar("qlx_balancetwo_elocheckPermission", int),
                         usage="<player or steam_id>")
        self.add_command("aliases", self.cmd_aliases,
                         permission=self.get_cvar("qlx_balancetwo_elocheckPermission", int),
                         usage="[player or steam_id]")
        self.add_command(("ratings", "elos", "selo"), self.cmd_ratings)

        self.add_command("eloupdates", self.cmd_switch_elo_changes_notifications, usage="<0/1>")

        self.add_command("balance", self.cmd_balance, 1)
        self.add_command(("teams", "teens"), self.cmd_teams)
        self.add_command("do", self.cmd_do, 1)
        self.add_command("dont", self.cmd_dont, 1)
        self.add_command(("agree", "a"), self.cmd_agree, client_cmd_perm=0)
        self.add_command(("veto", "v"), self.cmd_veto, client_cmd_perm=0)
        self.add_command(("nokick", "dontkick"), self.cmd_nokick, 2, usage="[<name>]")

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_LOWEST)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("game_end", self.handle_game_end)

        self.rating_system = self.get_cvar("qlx_balancetwo_ratingSystem")
        self.balance_api = self.get_cvar("qlx_balanceApi")

        self.kickthreads = {}

        self.jointimes = {}
        self.last_new_player_id = None
        self.previous_teams = None

        self.previous_map = None
        self.previous_gametype = None
        self.previous_ratings = {}

        self.ratings = {}
        self.rating_diffs = {}
        self.fetch_elos_from_all_players()

        self.informed_players = []

        self.switched_players = []
        self.switch_suggestion = None
        self.in_countdown = False

        self.twovstwo_steam_ids = []
        self.twovstwo_combinations = []
        self.twovstwo_iter = None

        self.prevent = False
        self.last_action = "spec"

    @minqlx.thread
    def fetch_elos_from_all_players(self):
        self.fetch_ratings([player.steam_id for player in self.players()])

    def fetch_ratings(self, steam_ids, mapname=None):
        self.fetch_mapbased_ratings(steam_ids, mapname)

        for rating_provider in [TRUSKILLS, A_ELO, B_ELO]:
            rating_results = rating_provider.fetch_elos(steam_ids)
            self.append_ratings(rating_provider.name, rating_results)

    def fetch_mapbased_ratings(self, steam_ids, mapname=None):
        if mapname is None and (self.game is None or self.game.map is None):
            return

        if mapname is None:
            mapname = self.game.map.lower()

        rating_results = TRUSKILLS.fetch_elos(steam_ids, headers={"X-QuakeLive-Map": mapname})
        rating_provider_name = "{} {}".format(mapname, TRUSKILLS.name)
        self.append_ratings(rating_provider_name, rating_results)

    def append_ratings(self, rating_provider_name, json_result):
        if json_result is None:
            return

        if rating_provider_name in self.ratings:
            self.ratings[rating_provider_name].append_ratings(json_result)
            return

        self.ratings[rating_provider_name] = RatingProvider.from_json(json_result)

    def cmd_elocheck(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 1:
            target = player.steam_id
        else:
            target = msg[1]

        self.do_elocheck(player, target, channel)

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

        used_steam_ids = self.used_steam_ids_for(target_steam_id)
        aliases = self.fetch_aliases(used_steam_ids)
        truskill = RatingProvider.from_json(TRUSKILLS.fetch_elos(used_steam_ids))
        a_elo = RatingProvider.from_json(A_ELO.fetch_elos(used_steam_ids))
        b_elo = RatingProvider.from_json(B_ELO.fetch_elos(used_steam_ids))
        map_based_truskill = None
        if self.game is not None and self.game.map is not None:
            map_based_truskill = RatingProvider.from_json(
                TRUSKILLS.fetch_elos(used_steam_ids, headers={"X-QuakeLive-Map": self.game.map.lower()}))

        if target_steam_id in aliases:
            target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                         target_steam_id, aliases=aliases[target_steam_id])
        else:
            target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                         target_steam_id)
        reply_func("{0}^7".format(target_player_elos))

        alternative_steam_ids = used_steam_ids[:]
        alternative_steam_ids.remove(target_steam_id)
        if len(alternative_steam_ids) == 0:
            return

        reply_func("Players from the same IPs:\n")
        for steam_id in alternative_steam_ids:
            if steam_id in aliases:
                player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill, steam_id,
                                                      aliases=aliases[steam_id])
            else:
                player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill, steam_id)
            reply_func("{0}^7".format(player_elos))

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

    def used_steam_ids_for(self, steam_id):
        if not self.db.exists(PLAYER_BASE.format(steam_id) + ":ips"):
            return [steam_id]

        ips = self.db.smembers(PLAYER_BASE.format(steam_id) + ":ips")

        used_steam_ids = set()
        for ip in ips:
            if not self.db.exists(IPS_BASE + ":{0}".format(ip)):
                continue

            used_steam_ids = used_steam_ids | self.db.smembers(IPS_BASE + ":{0}".format(ip))

        return [int(_steam_id) for _steam_id in used_steam_ids]

    def fetch_aliases(self, steam_ids):
        url_template = "{}aliases/".format(A_ELO.url_base) + "{}.json"

        try:
            result = requests_retry_session().get(
                url_template.format("+".join([str(steam_id) for steam_id in steam_ids])), timeout=A_ELO.timeout)
        except requests.RequestException as exception:
            self.logger.debug("request exception: {}".format(exception))
            return {}

        if result.status_code != requests.codes.ok:
            return {}
        js = result.json()

        aliases = {}
        for steam_id in steam_ids:
            if str(steam_id) not in js:
                continue

            player_entry = js[str(steam_id)]
            aliases[steam_id] = []
            cleaned_aliases = []
            for entry in player_entry:
                if self.clean_text(entry) not in cleaned_aliases:
                    aliases[steam_id].append(entry)
                    cleaned_aliases.append(self.clean_text(entry))
        return aliases

    def format_player_elos(self, a_elo, b_elo, truskill, map_based_truskill, steam_id, indent=0, aliases=None):
        display_name = self.resolve_player_name(steam_id)
        result = " " * indent + "{0}^7\n".format(self.format_player_name(steam_id))
        if aliases is not None:
            displayed_aliases = aliases[:]
            displayed_aliases.remove(display_name)
            if len(displayed_aliases) != 0:
                if len(displayed_aliases) <= 5:
                    result += " " * indent + "Aliases used: {}^7\n".format("^7, ".join(displayed_aliases[:5]))
                else:
                    result += " " * indent + "Aliases used: {}^7, ... (^4!aliases <player>^7 to list all)\n" \
                        .format("^7, ".join(displayed_aliases[:5]))

        if map_based_truskill is not None:
            formatted_map_based_truskills = map_based_truskill.format_elos(steam_id)
            if formatted_map_based_truskills is not None and len(formatted_map_based_truskills) > 0:
                result += " " * indent + "  " + "{1} Truskills: {0}\n" \
                    .format(formatted_map_based_truskills, self.game.map.lower())

        formatted_truskills = truskill.format_elos(steam_id)
        if truskill is not None and len(formatted_truskills) > 0:
            result += " " * indent + "  " + "Truskills: {0}\n".format(formatted_truskills)

        formatted_a_elos = a_elo.format_elos(steam_id)
        if a_elo is not None and len(formatted_a_elos) > 0:
            result += " " * indent + "  " + "Elos: {0}\n".format(formatted_a_elos)

        formatted_b_elos = b_elo.format_elos(steam_id)
        if b_elo is not None and len(formatted_b_elos) > 0:
            result += " " * indent + "  " + "B-Elos: {0}\n".format(formatted_b_elos)
        return result

    def format_player_name(self, steam_id):
        result = ""

        player_name = self.resolve_player_name(steam_id)
        result += "{0}^7".format(player_name)

        if self.show_steam_ids:
            result += " ({0})".format(steam_id)

        return result

    def resolve_player_name(self, steam_id):
        player = self.player(steam_id)
        if player is not None:
            return self.remove_trailing_color_code(player.name)

        if self.db.exists(PLAYER_BASE.format(steam_id) + ":last_used_name"):
            return self.remove_trailing_color_code(self.db[PLAYER_BASE.format(steam_id) + ":last_used_name"])

        return "unknown"

    def remove_trailing_color_code(self, text):
        if not text.endswith("^7"):
            return text

        return text[:-2]

    def cmd_aliases(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.do_aliases(player, msg[1], channel)

    @minqlx.thread
    def do_aliases(self, player: minqlx.Player, target: str, channel: minqlx.AbstractChannel):
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

        aliases = self.fetch_aliases([target_steam_id])

        if target_steam_id not in aliases:
            reply_func("Sorry, no aliases returned for {}".format(target_steam_id))
            return

        reply_func("{0}^7".format(self.format_player_aliases(target_steam_id, aliases[target_steam_id])))

    def format_player_aliases(self, steam_id, aliases):
        result = "{0}^7\n".format(self.format_player_name(steam_id))
        result += "Aliases used: {}".format("^7, ".join(aliases))
        return result

    def cmd_ratings(self, player, msg, channel):
        teams = self.teams()
        gametype = self.game.type_short

        mapname = self.game.map.lower()
        map_based_rating_provider_name = "{} {}".format(mapname, TRUSKILLS.name)

        if TRUSKILLS.name in self.ratings and map_based_rating_provider_name in self.ratings:
            truskills_rating_provider = self.ratings[TRUSKILLS.name]
            mapbased_truskills_rating_provider = self.ratings[map_based_rating_provider_name]

            channel.reply("^3{}^7 ratings (^3general^7/^3map-based^7) (^3{}^7)"
                          .format(TRUSKILLS.name, TRUSKILLS.url_base.split(':')[1].strip('/')))

            self.report_ratings_for_team(channel, teams["free"], gametype,
                                         truskills_rating_provider, mapbased_truskills_rating_provider,
                                         primary_rating_prefix="^6", secondary_rating_prefix="^6")
            self.report_ratings_for_team(channel, teams["red"], gametype,
                                         truskills_rating_provider, mapbased_truskills_rating_provider,
                                         primary_rating_prefix="^1", secondary_rating_prefix="^1")
            self.report_ratings_for_team(channel, teams["blue"], gametype,
                                         truskills_rating_provider, mapbased_truskills_rating_provider,
                                         primary_rating_prefix="^4", secondary_rating_prefix="^4")
            self.report_ratings_for_team(channel, teams["spectator"], gametype,
                                         truskills_rating_provider, mapbased_truskills_rating_provider)

        if A_ELO.name in self.ratings and B_ELO.name in self.ratings:
            primary_rating_provider = self.ratings[A_ELO.name]
            secondary_rating_provider = self.ratings[B_ELO.name]

            channel.reply("^5=================================^7")
            channel.reply("^3Elo^7 ratings (^3A elo^7/^3B elo^7) (^3{}^7)"
                          .format(A_ELO.url_base.split(':')[1].strip('/')))

            self.report_ratings_for_team(channel, teams["free"], gametype,
                                         primary_rating_provider, secondary_rating_provider,
                                         primary_rating_prefix="A:^6", secondary_rating_prefix="B:^6")
            self.report_ratings_for_team(channel, teams["red"], gametype,
                                         primary_rating_provider, secondary_rating_provider,
                                         primary_rating_prefix="A:^1", secondary_rating_prefix="B:^1")
            self.report_ratings_for_team(channel, teams["blue"], gametype,
                                         primary_rating_provider, secondary_rating_provider,
                                         primary_rating_prefix="A:^4", secondary_rating_prefix="B:^4")
            self.report_ratings_for_team(channel, teams["spectator"], gametype,
                                         primary_rating_provider, secondary_rating_provider,
                                         primary_rating_prefix="A:", secondary_rating_prefix="B:")

    def report_ratings_for_team(self, channel, team, gametype, primary_rating_provider, secondary_rating_provider,
                                primary_rating_prefix="", secondary_rating_prefix=""):
        if team is None or len(team) <= 0:
            return

        primary_filtered = [player for player in team if player.steam_id in primary_rating_provider.rated_steam_ids()]
        primary_filtered = [player for player in primary_filtered
                            if gametype in primary_rating_provider.rated_gametypes_for(player.steam_id)]
        primary_filtered = [player for player in primary_filtered
                            if primary_rating_provider.games_for(player.steam_id, gametype) > 0]

        rated_player_texts = []
        if len(primary_filtered) > 0:
            primary_sorted = sorted(primary_filtered,
                                    key=lambda x: primary_rating_provider[x.steam_id][gametype]["elo"], reverse=True)

            for player in primary_sorted:
                if player.steam_id in secondary_rating_provider.rated_steam_ids() and \
                        gametype in secondary_rating_provider.rated_gametypes_for(player.steam_id) and \
                        secondary_rating_provider.games_for(player.steam_id, gametype) > 0:
                    rated_player_texts.append("{}^7: {}{}^7/{}{}^7"
                                              .format(player.name,
                                                      primary_rating_prefix,
                                                      primary_rating_provider[player.steam_id][gametype]["elo"],
                                                      secondary_rating_prefix,
                                                      secondary_rating_provider[player.steam_id][gametype]["elo"]))
                else:
                    rated_player_texts.append("{}^7: {}{}^7/{}^5{}^7"
                                              .format(player.name,
                                                      primary_rating_prefix,
                                                      primary_rating_provider[player.steam_id][gametype]["elo"],
                                                      secondary_rating_prefix,
                                                      secondary_rating_provider[player.steam_id][gametype]["elo"]))

        primary_unranked = [player for player in team if player not in primary_filtered]

        if len(primary_unranked) > 0:
            secondary_filtered = [player for player in primary_unranked
                                  if player.steam_id in secondary_rating_provider.rated_steam_ids()]
            secondary_filtered = [player for player in secondary_filtered
                                  if gametype in secondary_rating_provider.rated_gametypes_for(player.steam_id)]
            secondary_filtered = [player for player in secondary_filtered
                                  if secondary_rating_provider.games_for(player.steam_id, gametype) > 0]

            if len(secondary_filtered) > 0:
                secondary_sorted = sorted(secondary_filtered,
                                          key=lambda x: primary_rating_provider[x.steam_id][gametype]["elo"],
                                          reverse=True)

                for player in secondary_sorted:
                    rated_player_texts.append("{}^7: {}^5{}/{}{}^7"
                                              .format(player.name,
                                                      primary_rating_prefix,
                                                      primary_rating_provider[player.steam_id][gametype]["elo"],
                                                      secondary_rating_prefix,
                                                      secondary_rating_provider[player.steam_id][gametype]["elo"]))

            secondary_unranked = [player for player in primary_unranked if player not in secondary_filtered]
            for player in secondary_unranked:
                rated_player_texts.append("{}^7: {}^5{}^7/{}^5{}^7"
                                          .format(player.name,
                                                  primary_rating_prefix,
                                                  primary_rating_provider[player.steam_id][gametype]["elo"],
                                                  secondary_rating_prefix,
                                                  secondary_rating_provider[player.steam_id][gametype]["elo"]))

        channel.reply(", ".join(rated_player_texts))

    def cmd_switch_elo_changes_notifications(self, player, msg, channel):
        flag = self.wants_to_be_informed(player.steam_id)
        self.db.set_flag(player, "balancetwo:rating_changes", not flag)

        if flag:
            player.tell(
                "Notifications for elo and truskill changes have been disabled. "
                "Use ^6{}eloupdates^7 to enable them again.".format(self.get_cvar("qlx_commandPrefix")))
        else:
            player.tell(
                "Notifications for elo and truskill changes have been enabled. "
                "Use ^6{}eloupdates^7 to disable them again.".format(self.get_cvar("qlx_commandPrefix")))

        return minqlx.RET_STOP_ALL

    def wants_to_be_informed(self, steam_id):
        return self.db.get_flag(steam_id, "balancetwo:rating_changes", default=False)

    def cmd_balance(self, player, msg, channel):
        gt = self.game.type_short
        if gt not in SUPPORTED_GAMETYPES:
            player.tell("This game mode is not supported by the balance plugin.")
            return minqlx.RET_STOP_ALL

        teams = self.teams()
        if len(teams["red"] + teams["blue"]) % 2 != 0:
            player.tell("The total number of players should be an even number.")
            return minqlx.RET_STOP_ALL

        players = dict([(p.steam_id, gt) for p in teams["red"] + teams["blue"]])
        self.callback_balance(players, minqlx.CHAT_CHANNEL)

    def callback_balance(self, players, channel):
        if not self.game:
            return

        if self.game.state == "in_progress":
            return

        teams = self.teams()
        current = teams["red"] + teams["blue"]

        if len(current) % 2 == 1:
            player_to_spec = self.find_player_to_spec(current)
            self.logger.debug("putting {} to spec".format(player_to_spec.clean_name))
            player_to_spec.put("spectator")

        balanced_teams = self.find_balanced_teams()
        if balanced_teams is None:
            return
        red_steam_ids, blue_steam_ids = balanced_teams

        changed = False

        for steam_id in red_steam_ids:
            player = self.player(steam_id)
            if player.team != "red":
                changed = True
                self.logger.debug("putting {} to red".format(player.clean_name))
                player.put("red")

        for steam_id in blue_steam_ids:
            player = self.player(steam_id)
            if player.team != "blue":
                changed = True
                self.logger.debug("putting {} to blue".format(player.clean_name))
                player.put("blue")

        if not changed:
            channel.reply("Teams are good! Nothing to balance.")
            return True

        self.report_teams(red_steam_ids, blue_steam_ids, channel)
        return True

    def find_player_to_spec(self, players):
        return min([player for player in players], key=lambda _player: self.find_games_here(_player))

    def find_games_here(self, player):
        completed_key = "minqlx:players:{}:games_completed"

        if not self.db.exists(completed_key.format(player.steam_id)):
            return 0

        return int(self.db[completed_key.format(player.steam_id)])

    def find_time(self, player):
        if not (player.steam_id in self.jointimes):
            self.jointimes[player.steam_id] = time.time()
        return self.jointimes[player.steam_id]

    def find_balanced_teams(self):
        teams = self.teams()

        #        if 3 < len(teams["red"] + teams["blue"]) < 6:
        #            return self.find_next_2vs2_teams()

        if len(teams["red"] + teams["blue"]) < 8:
            return self.find_non_recent_small_balanced_teams()

        return self.find_large_balanced_teams()

    def find_next_2vs2_teams(self):
        teams = self.teams()

        steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        if self.twovstwo_iter is None or not self.check_all_steam_ids(steam_ids):
            self.twovstwo_steam_ids = steam_ids
            self.twovstwo_combinations = self.filter_combinations(steam_ids)
            self.twovstwo_iter = random_iterator(self.twovstwo_combinations)

        red_steam_ids = list(next(self.twovstwo_iter))
        blue_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in red_steam_ids]

        return red_steam_ids, blue_steam_ids

    def check_all_steam_ids(self, steam_ids):
        return sorted(steam_ids) == sorted(self.twovstwo_steam_ids)

    def filter_combinations(self, steam_ids):
        gametype = self.game.type_short

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug("Balancing aborted. No ratings found for {}.".format(configured_rating_provider_name))
            return []
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        combinations = []
        if len(steam_ids) != 4:
            return []
        combinations_list = [(steam_ids[0], steam_ids[1]), (steam_ids[0], steam_ids[2]), (steam_ids[0], steam_ids[3])]

        for red_steam_ids in combinations_list:
            blue_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in red_steam_ids]

            red_avg = self.team_average(red_steam_ids, gametype, rating_provider=configured_rating_provider)
            blue_avg = self.team_average(blue_steam_ids, gametype, rating_provider=configured_rating_provider)
            diff = abs(red_avg - blue_avg)

            if diff < self.minimum_suggestion_diff:
                combinations.append((red_steam_ids, diff))

        return combinations_list

    def find_non_recent_small_balanced_teams(self):
        teams = self.teams()

        gt = self.game.type_short

        steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug("Balancing aborted. No ratings found for {}.".format(configured_rating_provider_name))
            return
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        team_combinations = []

        for combination in itertools.combinations(steam_ids, int(len(steam_ids) / 2)):
            red_steam_ids = list(combination)
            blue_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in red_steam_ids]

            if self.previous_teams is not None and (
                    sorted(red_steam_ids) == sorted(self.previous_teams[0]) or
                    sorted(red_steam_ids) == sorted(self.previous_teams[1])):
                continue

            if self.previous_teams is not None and (
                    sorted(blue_steam_ids) == sorted(self.previous_teams[0]) or
                    sorted(blue_steam_ids) == sorted(self.previous_teams[1])):
                continue

            red_avg = self.team_average(red_steam_ids, gt, rating_provider=configured_rating_provider)
            blue_avg = self.team_average(blue_steam_ids, gt, rating_provider=configured_rating_provider)
            diff = abs(red_avg - blue_avg)

            team_combinations.append((red_steam_ids, blue_steam_ids, diff))

        filtered_combinations = [(red_steam_ids, blue_steam_ids, diff) for (red_steam_ids, blue_steam_ids, diff) in
                                 team_combinations if diff < self.minimum_suggestion_diff]

        self.logger.debug("team_combinations: {}".format(team_combinations))
        self.logger.debug("filtered_combinations: {}".format(filtered_combinations))

        if len(filtered_combinations) > 0:
            red_team, blue_team, diff = random.choice(filtered_combinations)
        elif len(team_combinations) > 0:
            red_team, blue_team, diff = min(team_combinations, key=itemgetter(2))
        else:
            red_team = [player.steam_id for player in teams["red"]]
            blue_team = [player.steam_id for player in teams["blue"]]

        return red_team, blue_team

    def find_large_balanced_teams(self):
        teams = self.teams()

        gametype = self.game.type_short

        steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug("Balancing aborted. No ratings found for {}.".format(configured_rating_provider_name))
            return [], []

        configured_rating_provider = self.ratings[configured_rating_provider_name]
        rated_steam_ids = [steam_id for steam_id in steam_ids
                           if steam_id in configured_rating_provider.rated_steam_ids()]
        rated_steam_ids = [steam_id for steam_id in rated_steam_ids if
                           gametype in configured_rating_provider.rated_gametypes_for(steam_id)]
        rated_steam_ids = [steam_id for steam_id in rated_steam_ids if
                           configured_rating_provider[steam_id][gametype]["games"] > 0]
        rated_steam_ids.sort(key=lambda steam_id: configured_rating_provider[steam_id][gametype]["elo"])
        if len(rated_steam_ids) % 2 == 1:
            rated_steam_ids.remove(rated_steam_ids[0])

        red_steam_ids = []
        blue_steam_ids = []

        while len(rated_steam_ids) > 0:
            player1 = rated_steam_ids.pop()
            player2 = rated_steam_ids.pop()

            option1_red_average = self.team_average(red_steam_ids + [player1], gametype,
                                                    rating_provider=configured_rating_provider)
            option1_blue_average = self.team_average(blue_steam_ids + [player2], gametype,
                                                     rating_provider=configured_rating_provider)
            option1_diff = abs(option1_red_average - option1_blue_average)

            option2_red_average = self.team_average(red_steam_ids + [player2], gametype,
                                                    rating_provider=configured_rating_provider)
            option2_blue_average = self.team_average(blue_steam_ids + [player1], gametype,
                                                     rating_provider=configured_rating_provider)
            option2_diff = abs(option2_red_average - option2_blue_average)

            if option1_diff < option2_diff:
                red_steam_ids.append(player1)
                blue_steam_ids.append(player2)
            else:
                red_steam_ids.append(player2)
                blue_steam_ids.append(player1)
        return red_steam_ids, blue_steam_ids

    def report_teams(self, red_team, blue_team, channel):
        gt = self.game.type_short

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug("No ratings for configured rating provider {} found. Abandoning."
                              .format(configured_rating_provider_name))
            return

        configured_rating_provider = self.ratings[configured_rating_provider_name]

        avg_red = self.team_average(red_team, gt, rating_provider=configured_rating_provider)
        avg_blue = self.team_average(blue_team, gt, rating_provider=configured_rating_provider)
        avg_diff = avg_red - avg_blue

        stddev_red = self.team_stddev(red_team, gt, mu=avg_red, rating_provider=configured_rating_provider)
        stddev_blue = self.team_stddev(blue_team, gt, mu=avg_blue, rating_provider=configured_rating_provider)

        if configured_rating_provider_name.endswith(TRUSKILLS.name):
            if avg_diff >= 0.005:
                channel.reply(
                    "{} ratings: ^1{:.02f} (deviation: {:.02f}) "
                    "^7vs ^4{:.02f} (deviation: {:.02f})^7 - DIFFERENCE: ^1{:.02f}"
                    .format(configured_rating_provider_name, avg_red, stddev_red, avg_blue, stddev_blue, abs(avg_diff)))
                return
            if avg_diff <= -0.005:
                channel.reply(
                    "{} ratings: ^1{:.02f} (deviation: {:.02f}) "
                    "^7vs ^4{:.02f} (deviation: {:.02f})^7 - DIFFERENCE: ^4{:.02f}"
                    .format(configured_rating_provider_name, avg_red, stddev_red, avg_blue, stddev_blue, abs(avg_diff)))
                return
            channel.reply(
                "{} ratings: ^1{:.02f} (deviation: {:.02f}) ^7vs ^4{:.02f} (deviation: {:.02f})^7 - Holy shit!"
                .format(configured_rating_provider_name, avg_red, stddev_red, avg_blue, stddev_blue))
            return

        if int(avg_diff) > 0:
            channel.reply("{} ratings: ^1{:.0f} (deviation: {:.0f}) "
                          "^7vs ^4{:.0f} (deviation: {:.0f})^7 - DIFFERENCE: ^1{:.0f}"
                          .format(configured_rating_provider_name, avg_red, stddev_red,
                                  avg_blue, stddev_blue, abs(avg_diff)))
            return
        if int(avg_diff) < 0:
            channel.reply("{} ratings: ^1{:.0f} (deviation: {:.0f}) "
                          "^7vs ^4{:.0f} (deviation: {:.0f})^7 - DIFFERENCE: ^4{:.0f}"
                          .format(configured_rating_provider_name, avg_red, stddev_red,
                                  avg_blue, stddev_blue, abs(avg_diff)))
            return
        channel.reply(
            "{} ratings: ^1{:.0f} (deviation: {:.0f}) ^7vs ^4{:.0f} (deviation: {:.0f})^7 - Holy shit!"
            .format(configured_rating_provider_name, avg_red, stddev_red, avg_blue, stddev_blue))

    def configured_rating_provider_name(self):
        if self.game is not None and self.game.map is not None:
            if self.rating_system == "mapbased-truskills":
                rating_provider_name = "{} {}".format(self.game.map.lower(), TRUSKILLS.name)
                return rating_provider_name
        if self.rating_system.endswith("truskills"):
            return TRUSKILLS.name

        if self.rating_system == "a-elo":
            return A_ELO.name

        if self.rating_system == "b-elo":
            return B_ELO.name

    def team_average(self, steam_ids, gametype, rating_provider=None):
        if not steam_ids or len(steam_ids) == 0:
            return 0

        configured_rating_provider = rating_provider
        if configured_rating_provider is None:
            configured_rating_provider_name = self.configured_rating_provider_name()
            if configured_rating_provider_name not in self.ratings:
                return 0

            configured_rating_provider = self.ratings[configured_rating_provider_name]

        for steam_id in steam_ids:
            if steam_id not in configured_rating_provider.rated_steam_ids():
                return 0

        return sum([configured_rating_provider[steam_id][gametype]["elo"] for steam_id in steam_ids]) / len(
            steam_ids)

    def team_stddev(self, steam_ids, gametype, mu=None, rating_provider=None):
        if not steam_ids or len(steam_ids) == 0:
            return 0

        configured_rating_provider = rating_provider
        if configured_rating_provider is None:
            configured_rating_provider_name = self.configured_rating_provider_name()
            if configured_rating_provider_name not in self.ratings:
                return 0

            configured_rating_provider = self.ratings[configured_rating_provider_name]

        for steam_id in steam_ids:
            if steam_id not in configured_rating_provider.rated_steam_ids():
                return 0

        team_elos = [pow(configured_rating_provider[steam_id][gametype]["elo"] - mu, 2) for steam_id in steam_ids]
        return math.sqrt(sum(team_elos) / len(steam_ids))

    def cmd_teams(self, player, msg, channel):
        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            player.tell("This game mode is not supported by the balance plugin.")
            return minqlx.RET_STOP_ALL

        teams = self.teams()
        if len(teams["red"]) != len(teams["blue"]):
            player.tell("Both teams should have the same number of players.")
            return minqlx.RET_STOP_ALL

        self.report_teams([player.steam_id for player in teams["red"]],
                          [player.steam_id for player in teams["blue"]],
                          channel)

        if len(teams["red"] + teams["blue"]) == 0:
            channel.reply("No players active currently")
            return minqlx.RET_STOP_ALL

        if len(teams["red"] + teams["blue"]) == 4:
            i = random.randint(0, 99)
            if not i:
                channel.reply("Teens look ^6good!")
            else:
                channel.reply("Teams look good!")
            self.switch_suggestion = None
            return minqlx.RET_STOP_ALL

        self.collect_suggestions(teams, gametype, channel)

    @minqlx.thread
    def collect_suggestions(self, teams, gametype, channel):
        possible_switches = self.filtered_suggestions(teams, gametype)

        if self.unique_player_switches and len(self.switched_players) > 0:
            possible_switches = list(filter(lambda suggestion:
                                            suggestion.red_player.steam_id not in self.switched_players
                                            and suggestion.blue_player.steam_id not in self.switched_players,
                                            possible_switches))
        self.handle_suggestions_collected(possible_switches, channel)

    def filtered_suggestions(self, teams, gametype):
        player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = \
            self.minimum_suggestion_parameters(gametype, player_steam_ids)

        avg_red = self.team_average([player.steam_id for player in teams["red"]], gametype,
                                    rating_provider=configured_rating_provider)
        avg_blue = self.team_average([player.steam_id for player in teams["blue"]], gametype,
                                     rating_provider=configured_rating_provider)
        avg_diff = abs(avg_red - avg_blue)

        possible_switches = self.possible_switches(teams, gametype)

        if avg_diff <= minimum_suggestion_diff:
            stddev_red = self.team_stddev([player.steam_id for player in teams["red"]], gametype, mu=avg_red,
                                          rating_provider=configured_rating_provider)
            stddev_blue = self.team_stddev([player.steam_id for player in teams["blue"]], gametype, mu=avg_blue,
                                           rating_provider=configured_rating_provider)
            stddev_diff = abs(stddev_red - stddev_blue)
            return list(filter(lambda suggestion:
                               stddev_diff - abs(suggestion.stddev_diff) >= minimum_suggestion_stddev_diff and
                               abs(suggestion.stddev_diff) <= minimum_suggestion_stddev_diff and
                               abs(suggestion.avg_diff) <= minimum_suggestion_diff,
                               possible_switches))

        return list(filter(
            lambda suggestion: avg_diff > abs(suggestion.avg_diff) and
                    avg_diff - abs(suggestion.avg_diff) >= minimum_suggestion_diff,
                    possible_switches))

    def minimum_suggestion_parameters(self, gametype, steam_ids):
        return self.minimum_suggestion_diff, self.minimum_suggestion_stddev_diff

    def possible_switches(self, teams, gametype):
        player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = \
            self.minimum_suggestion_parameters(gametype, player_steam_ids)

        switches = []
        for red_p in teams["red"]:
            for blue_p in teams["blue"]:
                r = [player.steam_id for player in teams["red"]
                     if player.steam_id != red_p.steam_id] + [blue_p.steam_id]
                b = [player.steam_id for player in teams["blue"]
                     if player.steam_id != blue_p.steam_id] + [red_p.steam_id]
                avg_red = self.team_average(r, gametype, rating_provider=configured_rating_provider)
                avg_blue = self.team_average(b, gametype, rating_provider=configured_rating_provider)
                diff = avg_red - avg_blue

                if diff <= minimum_suggestion_diff:
                    stddev_red = self.team_stddev(r, gametype, mu=avg_red, rating_provider=configured_rating_provider)
                    stddev_blue = self.team_stddev(b, gametype, mu=avg_blue, rating_provider=configured_rating_provider)
                    stddev_diff = stddev_red - stddev_blue
                    suggestion = Suggestion(red_p, blue_p, diff, stddev_diff)

                    switches.append(suggestion)

        return switches

    def handle_suggestions_collected(self, possible_switches, channel):
        rating_strategy = self.rating_strategy(self.get_cvar("qlx_balancetwo_ratingStrategy", str))
        switch_suggestion_queue = SuggestionQueue(possible_switches, rating_strategy)

        if switch_suggestion_queue and len(switch_suggestion_queue) > 0:
            switch = switch_suggestion_queue.best_suggestion()
            channel.reply(switch.announcement())

            if not self.switch_suggestion or switch != self.switch_suggestion:
                self.switch_suggestion = switch
        else:
            i = random.randint(0, 99)
            if not i:
                channel.reply("Teens look ^6good!")
            else:
                channel.reply("Teams look good!")
            self.switch_suggestion = None

        return True

    def rating_strategy(self, strategy):
        return DiffSuggestionRatingStrategy()

    def cmd_do(self, player, msg, channel):
        if self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.switch_suggestion.execute()

    def cmd_dont(self, player, msg, channel):
        if not self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.msg("An admin prevented the switch! The switch will be terminated.")
        self.switch_suggestion = None

    def cmd_agree(self, player, msg, channel):
        if self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        if self.switch_suggestion.all_agreed():
            return

        self.switch_suggestion.agree(player)

        if not self.switch_suggestion.all_agreed():
            return

        # If the game's in progress and we're not in the round countdown, wait for next round.
        if self.game.state == "in_progress" and not self.in_countdown:
            self.msg("The switch will be executed at the start of next round.")
            return

        # Otherwise, switch right away.
        self.execute_suggestion()

    def execute_suggestion(self):
        try:
            self.switch_suggestion.execute()
        except minqlx.NonexistentPlayerError:
            self.switch_suggestion = None
            return
        except PlayerMovedToSpecError:
            self.switch_suggestion = None
            return

        self.switched_players += self.switch_suggestion.affected_steam_ids()
        self.switch_suggestion = None

    def cmd_veto(self, player, msg, channel):
        if not self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.switch_suggestion.agree(player)

        if not self.switch_suggestion.all_agreed():
            return

        self.msg("Both players vetoed! The switch will be terminated.")
        self.switch_suggestion = None

    def cmd_nokick(self, player, msg, channel):
        def dontkick(_steam_id):
            if _steam_id not in self.kickthreads:
                return

            kickthread = self.kickthreads[_steam_id]

            _resolved_player = self.player(_steam_id)
            if _resolved_player is None:
                return

            kickthread.stop()

            del self.kickthreads[_steam_id]

            _resolved_player.unmute()

            channel.reply("^7An admin has prevented {}^7 from being kicked.".format(_resolved_player.name))

        if self.kickthreads is None or len(self.kickthreads.keys()) == 0:
            player.tell("^6Psst^7: There are no people being kicked right now.")
            return minqlx.RET_STOP_ALL

        if len(self.kickthreads.keys()) == 1:
            dontkick(list(self.kickthreads.keys())[0])
            return

        _scheduled_players = []
        for steam_id in self.kickthreads.keys():
            if not self.kickthreads[steam_id].is_alive():
                continue

            _player = self.player(steam_id)
            if _player is None:
                continue

            _scheduled_players.append(_player)

        _names = [p.name for p in _scheduled_players]

        if len(msg) < 2:
            player.tell("^6Psst^7: did you mean ^6{}^7?".format("^7 or ^6".join(_names)))
            return minqlx.RET_STOP_ALL

        matched_players = [_player for _player in _scheduled_players if msg[1] in _player.name]

        if len(matched_players) == 0:
            player.tell("^6Psst^7: no players matched '^6{}^7'?".format(msg[1]))
            return minqlx.RET_STOP_ALL

        if len(matched_players) > 1:
            _matched_names = [_player.name for _player in matched_players]
            player.tell("^6Psst^7: did you mean ^6{}^7?".format("^7 or ^6".join(_matched_names)))
            return minqlx.RET_STOP_ALL

        dontkick(matched_players[0].steam_id)

    def handle_map_change(self, mapname, factory):
        @minqlx.delay(3)
        def fetch_ratings_from_newmap(_mapname):
            steam_ids = [player.steam_id for player in self.players()]
            self.fetch_mapbased_ratings(steam_ids, mapname=_mapname)

        self.switched_players = []
        self.informed_players = []
        self.previous_ratings = self.ratings
        self.ratings = {}
        self.fetch_and_diff_ratings()

        fetch_ratings_from_newmap(mapname.lower())

        self.clean_up_kickthreads()

    @minqlx.thread
    def clean_up_kickthreads(self):
        dead_threads = []
        for steam_id in self.kickthreads.keys():
            thread = self.kickthreads[steam_id]
            if not thread.is_alive():
                dead_threads.append(steam_id)

        for dead_thread in dead_threads:
            del self.kickthreads[dead_thread]

    @minqlx.thread
    def fetch_and_diff_ratings(self):
        for rating_provider in [TRUSKILLS, A_ELO, B_ELO]:
            if rating_provider.name in self.previous_ratings:
                rating_results = \
                    rating_provider.fetch_elos(self.previous_ratings[rating_provider.name].rated_steam_ids())
                if rating_results is None:
                    continue

                self.append_ratings(rating_provider.name, rating_results)
                self.rating_diffs[rating_provider.name] = \
                    RatingProvider.from_json(rating_results) - self.previous_ratings[rating_provider.name]

        if self.previous_map is None:
            return

        rating_provider_name = "{} {}".format(self.previous_map, TRUSKILLS.name)
        if rating_provider_name not in self.previous_ratings:
            return

        rating_results = TRUSKILLS.fetch_elos(self.previous_ratings[rating_provider_name].rated_steam_ids(),
                                              headers={"X-QuakeLive-Map": self.previous_map})
        if rating_results is None:
            return

        self.append_ratings(rating_provider_name, rating_results)
        self.rating_diffs[rating_provider_name] = \
            RatingProvider.from_json(rating_results) - self.previous_ratings[rating_provider_name]

    def handle_player_connect(self, player):
        @minqlx.thread
        def fetch_player_elos(_player):
            self.fetch_ratings([_player.steam_id])
            self.schedule_kick_for_players_outside_rating_limits([_player.steam_id])

        self.record_join_times(player)
        fetch_player_elos(player)

    def record_join_times(self, player):
        if player.steam_id in self.jointimes:
            if (time.time() - self.jointimes[player.steam_id]) < 5:
                return

        self.jointimes[player.steam_id] = time.time()

    def schedule_kick_for_players_outside_rating_limits(self, steam_ids):
        if not self.ratingLimit_kick:
            return

        for steam_id in steam_ids:
            if not self.is_player_within_configured_rating_limit(steam_id):
                if steam_id not in self.kickthreads or not self.kickthreads[steam_id].is_alive():
                    configured_rating_provider_name = self.configured_rating_provider_name()
                    configured_rating_provider = self.ratings[configured_rating_provider_name]

                    if steam_id not in configured_rating_provider:
                        continue

                    gametype = self.game.type_short
                    player_ratings = configured_rating_provider.rating_for(steam_id, gametype)

                    if self.ratingLimit_min <= player_ratings:
                        highlow = "high"
                    else:
                        highlow = "low"

                    t = KickThread(steam_id, player_ratings, highlow)
                    t.start()
                    self.kickthreads[steam_id] = t

    def handle_player_disconnect(self, player, reason):
        if player.steam_id in self.jointimes:
            del self.jointimes[player.steam_id]

    def handle_team_switch_attempt(self, player, old, new):
        self.logger.debug("{} switched from {} to {}".format(player.clean_name, old, new))
        if not self.game:
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        if new in ["red", "blue", "any", "free"]:
            rating_check = self.check_rating_limit(player)
            if rating_check is not None:
                return rating_check

        if self.game.state != "in_progress":
            return minqlx.RET_NONE

        return self.try_auto_rebalance(player, old, new)

    def check_rating_limit(self, player):
        if self.is_player_within_configured_rating_limit(player.steam_id):
            return

        if self.ratingLimit_kick:
            kickmsg = "so you'll be kicked shortly..."
        else:
            kickmsg = "but you are free to keep watching."

        player.tell("^6You do not meet the skill rating requirements to play on this server, {}".format(kickmsg))
        player.center_print(
            "^6You do not meet the skill rating requirements to play on this server, {}".format(kickmsg))

        return minqlx.RET_STOP_ALL

    def is_player_within_configured_rating_limit(self, steam_id):
        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name.endswith("truskills"):
            configured_rating_provider_name = TRUSKILLS.name

        if configured_rating_provider_name not in self.ratings:
            self.logger.debug("Ratings not found. Allowing player to join: {}.".format(configured_rating_provider_name))
            return True

        configured_rating_provider = self.ratings[configured_rating_provider_name]

        if steam_id not in configured_rating_provider:
            return False

        gametype = self.game.type_short
        player_ratings = configured_rating_provider.rating_for(steam_id, gametype)

        if self.ratingLimit_min <= player_ratings <= self.ratingLimit_max:
            return True

        player_games = configured_rating_provider.games_for(steam_id, gametype)

        return player_games < self.ratingLimit_minGames

    def try_auto_rebalance(self, player, old, new):
        if not self.auto_rebalance:
            return minqlx.RET_NONE

        if old not in ["spectator", "free"] or new not in ['red', 'blue', 'any']:
            return minqlx.RET_NONE

        teams = self.teams()
        if len(teams["red"]) == len(teams["blue"]):
            self.last_new_player_id = player.steam_id
            return minqlx.RET_NONE

        if not self.last_new_player_id:
            return minqlx.RET_NONE

        last_new_player = self.player(self.last_new_player_id)
        if not last_new_player:
            self.last_new_player_id = None
            return minqlx.RET_NONE

        gametype = self.game.type_short

        other_than_last_players_team = self.other_team(last_new_player.team)
        new_player_team = teams[other_than_last_players_team].copy() + [player]
        proposed_diff = self.calculate_player_average_difference(gametype,
                                                                 teams[last_new_player.team].copy(),
                                                                 new_player_team)

        alternative_team_a = [player for player in teams[last_new_player.team] if player != last_new_player] + \
                             [player]
        alternative_team_b = teams[other_than_last_players_team].copy() + [last_new_player]
        alternative_diff = self.calculate_player_average_difference(gametype,
                                                                    alternative_team_a,
                                                                    alternative_team_b)

        self.last_new_player_id = None
        if proposed_diff > alternative_diff:
            last_new_player.tell("{}, you have been moved to {} to maintain team balance."
                                 .format(last_new_player.clean_name, self.format_team(other_than_last_players_team)))
            last_new_player.put(other_than_last_players_team)
            if new in [last_new_player.team]:
                return minqlx.RET_NONE
            if new not in ["any"]:
                player.tell("{}, you have been moved to {} to maintain team balance."
                            .format(player.clean_name, self.format_team(last_new_player.team)))
            player.put(last_new_player.team)
            return minqlx.RET_STOP_ALL

        if new not in ["any", other_than_last_players_team]:
            player.tell("{}, you have been moved to {} to maintain team balance."
                        .format(player.clean_name, self.format_team(other_than_last_players_team)))
            player.put(other_than_last_players_team)
            return minqlx.RET_STOP_ALL

        return minqlx.RET_NONE

    def other_team(self, team):
        if team == "red":
            return "blue"
        return "red"

    def calculate_player_average_difference(self, gametype, team1, team2):
        team1_steam_ids = [player.steam_id for player in team1]
        team2_steam_ids = [player.steam_id for player in team2]
        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        team1_avg = self.team_average(gametype, team1_steam_ids, rating_provider=configured_rating_provider)
        team2_avg = self.team_average(gametype, team2_steam_ids, rating_provider=configured_rating_provider)
        return abs(team1_avg - team2_avg)

    def format_team(self, team):
        if team == "red":
            return "^1red^7"
        if team == "blue":
            return "^4blue^7"

        return "^3{}^7".format(team)

    def handle_team_switch(self, player, old, new):
        if self.last_new_player_id == player.steam_id and new in ["free", "spectator"]:
            self.last_new_player_id = None

        if new not in ["red", "blue", "any"]:
            return

        self.inform_about_rating_changes(player)

    def inform_about_rating_changes(self, player):
        if player.steam_id in self.informed_players:
            return

        self.informed_players.append(player.steam_id)

        if not self.wants_to_be_informed(player.steam_id):
            return

        changed_ratings = []
        previous_truskills = "{} {}".format(self.previous_map, TRUSKILLS.name)

        for rating_provider_name in [previous_truskills, TRUSKILLS.name, A_ELO.name, B_ELO.name]:
            formatted_diffs = self.format_rating_diffs_for_rating_provider_name_and_player(
                rating_provider_name, player.steam_id)
            if formatted_diffs is not None:
                changed_ratings.append(formatted_diffs)

        if len(changed_ratings) == 0:
            return

        player.tell("Your ratings changed since the last map: {}".format(", ".join(changed_ratings)))

    def format_rating_diffs_for_rating_provider_name_and_player(self, rating_provider_name, steam_id):
        if rating_provider_name not in self.rating_diffs or steam_id not in self.rating_diffs[rating_provider_name] or \
                self.previous_gametype not in self.rating_diffs[rating_provider_name][steam_id] or \
                rating_provider_name not in self.ratings or steam_id not in self.ratings[rating_provider_name]:
            return None

        current_rating = self.ratings[rating_provider_name][steam_id][self.previous_gametype]["elo"]
        rating_diff = self.rating_diffs[rating_provider_name][steam_id][self.previous_gametype]
        if rating_provider_name.endswith(TRUSKILLS.name):
            if rating_diff < 0.0:
                return "^3{}^7: ^4{:.02f}^7 (^1{:+.02f}^7)".format(rating_provider_name, current_rating, rating_diff)
            elif rating_diff > 0.0:
                return "^3{}^7: ^4{:.02f}^7 (^2{:+.02f}^7)".format(rating_provider_name, current_rating, rating_diff)
            return None

        if rating_diff < 0:
            return "^3{}^7: ^4{:d}^7 (^1{:+d}^7)".format(rating_provider_name, current_rating, rating_diff)
        elif rating_diff > 0:
            return "^3{}^7: ^4{:d}^7 (^2{:+d}^7)".format(rating_provider_name, current_rating, rating_diff)

        return None

    @minqlx.delay(5)
    def handle_game_countdown(self):
        self.msg("^7Balancing on skill ratings...")
        self.callback_balance(None, minqlx.CHAT_CHANNEL)

    def handle_round_countdown(self, round_number):
        @minqlx.next_frame
        def execute_switch_suggestion():
            self.execute_suggestion()

        if (not self.auto_switch and self.switch_suggestion is not None and self.switch_suggestion.all_agreed()) or \
                (self.auto_switch and self.switch_suggestion is not None and
                 not self.switch_suggestion.all_agreed()):
            execute_switch_suggestion()

        self.in_countdown = True

        self.even_up_teams()
        self.balance_before_start(round_number)

    def even_up_teams(self):
        teams = self.teams()

        player_count = len(teams["red"] + teams["blue"])

        if player_count == 1:
            return

        team_diff = len(teams["red"]) - len(teams["blue"])

        if abs(team_diff) == 0:
            return

        even_to, even_from = ["blue", "red"] if team_diff > 0 else ["red", "blue"]
        n = int(abs(team_diff) / 2)

        last = self.identify_player_to_move()

        if team_diff % 2 == 0:
            amount_players_moved = last.name if n == 1 else "{} players".format(n)
            self.msg(
                "^6Uneven teams detected!^7 At round start i'll move {} to {}".format(amount_players_moved, even_to))
            return

        amount_players_moved = "lowest player" if n == 1 else "{} lowest players".format(n)
        message = " and move {} to {}".format(amount_players_moved, even_to) if n else ''
        self.msg("^6Uneven teams detected!^7 Server will auto spec {}{}.".format(last.name, message))

    def identify_player_to_move(self):
        teams = self.teams()

        # See which team is bigger than the other
        if len(teams["blue"]) > len(teams["red"]):
            bigger_team = teams["blue"].copy()
        elif len(teams["red"]) > len(teams["blue"]):
            bigger_team = teams["red"].copy()
        else:
            self.msg("Cannot pick last player since there are none.")
            return

        if (self.game.red_score + self.game.blue_score) >= 1:
            self.msg("Picking someone to {} based on score".format(self.last_action))
            lowest_score = bigger_team[0].score
            lowest_players = [bigger_team[0]]
            for p in bigger_team:
                if lowest_score == 0 and p.score <= lowest_score:
                    lowest_players.append(p)
                elif p.score < lowest_players[0].score:
                    lowest_score = max(p.score, 0)
                    lowest_players = [p]
                elif p.score == lowest_players[0].score:
                    lowest_players.append(p)

            if len(lowest_players) == 1:
                lowest_player = lowest_players[0]
            else:
                lowest_players2 = [lowest_players[0]]
                for player in lowest_players:
                    if player.stats.damage_dealt < lowest_players2[0].stats.damage_dealt:
                        lowest_players2 = [player]
                    elif player.stats.damage_dealt == lowest_players2[0].stats.damage_dealt:
                        lowest_players2.append(player)

                if len(lowest_players2) == 1:
                    lowest_player = lowest_players2[0]
                else:
                    lowest_player = max(lowest_players2, key=lambda e1: self.find_time(e1))
        else:
            self.msg("Picking someone to {} based on join times.".format(self.last_action))
            lowest_player = max(bigger_team, key=lambda e1: self.find_time(e1))
        self.msg("Picked {} from the {} team.".format(lowest_player.name, lowest_player.team))
        return lowest_player

    def handle_round_start(self, round_number):
        self.last_new_player_id = None
        self.in_countdown = False

        self.balance_before_start(round_number, True)

    @minqlx.thread
    def balance_before_start(self, roundnumber, direct=False):
        @minqlx.next_frame
        def game_logic(func):
            func()

        @minqlx.next_frame
        def slay_player(p):
            p.health = 0

        def exclude_player(p):
            t = self.teams().copy()
            if p in t['red']:
                t['red'].remove(p)
            if p in t['blue']:
                t['blue'].remove(p)
            return t

        countdown = int(self.get_cvar('g_roundWarmupDelay'))
        if self.game.type_short == "ft":
            countdown = int(self.get_cvar('g_freezeRoundDelay'))
        if not direct:
            time.sleep(max(countdown / 1000 - 0.8, 0))

        teams = self.teams()
        player_count = len(teams["red"] + teams["blue"])

        if player_count == 1 or self.game.state not in ["in_progress"]:
            return

        if self.game.type_short == "ca":
            if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
                return

        if self.game.type_short == "tdm":
            if self.game.fraglimit in [self.game.blue_score, self.game.red_score]:
                return

        if self.game.type_short == "ctf":
            if self.game.capturelimit in [self.game.blue_score, self.game.red_score]:
                return

        team_diff = len(teams["red"]) - len(teams["blue"])

        while abs(team_diff) >= 1:
            last = self.identify_player_to_move()

            if not last:
                self.msg(
                    "Error: Trying to balance before round {} start. Red({}) - Blue({}) players"
                    .format(roundnumber, len(teams['red']), len(teams['blue'])))
                return
            if team_diff % 2 == 0:
                even_to, even_from = ["blue", "red"] if team_diff > 0 else ["red", "blue"]
                game_logic(lambda: last.put(even_to))
                self.msg("^6Uneven teams action^7: Moved {} from {} to {}".format(last.name, even_from, even_to))

            else:
                if self.prevent or self.last_action == "ignore":
                    excluded_teams = exclude_player(last)
                    self.msg("^6Uneven teams^7: {} will not be moved to spec".format(last.name))
                elif self.last_action == "slay":
                    if "anti_rape" in minqlx.Plugin._loaded_plugins:
                        game_logic(lambda: last.put("spectator"))
                        self.msg("^6Uneven teams action^7: {} was moved to spec to even teams!".format(last.name))
                        self.msg("Not slayed because anti_rape plugin is loaded.")
                    else:
                        slay_player(last)
                        self.msg("{} ^7has been ^1slain ^7to even the teams!")
                else:
                    self.msg("^6Uneven teams action^7: {} was moved to spec to even teams!".format(last.name))
                    game_logic(lambda: last.put("spectator"))
            time.sleep(0.2)

    def handle_game_end(self, data):
        if not self.game or bool(data["ABORTED"]):
            return

        teams = self.teams()
        self.previous_teams = [player.steam_id for player in teams["red"]], \
                              [player.steam_id for player in teams["blue"]]

        self.previous_map = data["MAP"].lower()
        self.previous_gametype = data["GAME_TYPE"].lower()
        # self.record_team_stats(self.previous_gametype)

        if len(teams["red"] + teams["blue"]) == 4 and self.twovstwo_iter is None:
            steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]
            self.twovstwo_steam_ids = steam_ids
            self.twovstwo_combinations = [(steam_ids[0], steam_ids[1]),
                                          (steam_ids[0], steam_ids[2]),
                                          (steam_ids[0], steam_ids[3])]
            self.twovstwo_iter = random_iterator(self.twovstwo_combinations)

            next_twovstwo = sorted(list(next(self.twovstwo_iter)))
            other_twovstwo = sorted([steam_id for steam_id in steam_ids if steam_id not in next_twovstwo])
            red_steam_ids = sorted([player.steam_id for player in teams["red"]])
            blue_steam_ids = sorted([player.steam_id for player in teams["blue"]])
            while not (next_twovstwo == red_steam_ids or
                       next_twovstwo == blue_steam_ids or
                       other_twovstwo == red_steam_ids or
                       other_twovstwo == blue_steam_ids):
                next_twovstwo = sorted(list(next(self.twovstwo_iter)))
                other_twovstwo = sorted([steam_id for steam_id in steam_ids if steam_id not in next_twovstwo])

    @minqlx.thread
    def record_team_stats(self, gametype):
        teams = self.teams()

        if len(teams["red"] + teams["blue"]) == 2:
            return

        stats = [
            self.game.map,
            self.game.red_score,
            self.game.blue_score,
            self.team_stats(teams["red"], gametype),
            self.team_stats(teams["blue"], gametype)
        ]

        elostats_filename = os.path.join(self.get_cvar("fs_homepath"), "elostats.txt")
        with open(elostats_filename, "a") as elostats_file:
            elostats_file.write("{}\n".format(stats))

    def team_stats(self, team, gametype):
        returned = {}
        for player in team:
            a_elo = 0
            if A_ELO.name in self.ratings and player.steam_id in self.ratings[A_ELO.name]:
                a_elo = self.ratings[A_ELO.name][player.steam_id][gametype]["elo"]
            b_elo = 0
            if B_ELO.name in self.ratings and player.steam_id in self.ratings[B_ELO.name]:
                b_elo = self.ratings[B_ELO.name][player.steam_id][gametype]["elo"]
            truskill = 0
            if TRUSKILLS.name in self.ratings and player.steam_id in self.ratings[TRUSKILLS.name]:
                truskill = self.ratings[TRUSKILLS.name][player.steam_id][gametype]["elo"]
            returned[player.steam_id] = [a_elo, b_elo, truskill]

        return returned


FILTERED_OUT_GAMETYPE_RESPONSES = ["steamid"]


class SkillRatingProvider:
    def __init__(self, name, url_base, balance_api, timeout=7):
        self.name = name
        self.url_base = url_base
        self.balance_api = balance_api
        self.timeout = timeout

    def fetch_elos(self, steam_ids, headers=None):
        if len(steam_ids) == 0:
            return None

        request_url = self.url_base + "{}/{}".format(self.balance_api,
                                                     "+".join([str(steam_id) for steam_id in steam_ids]))
        try:
            result = requests_retry_session().get(request_url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exception:
            minqlx.get_logger("balancetwo").debug("request exception: {}".format(exception))
            return None

        if result.status_code != requests.codes.ok:
            return None
        return result.json()


TRUSKILLS = SkillRatingProvider("Truskill", "http://stats.houseofquake.com/", "elo/map_based")
A_ELO = SkillRatingProvider("Elo", "http://qlstats.net/", "elo", timeout=15)
B_ELO = SkillRatingProvider("B-Elo", "http://qlstats.net/", "elo_b", timeout=15)


class RatingProvider:
    def __init__(self, json):
        self.jsons = [json]

    def __iter__(self):
        return iter(self.rated_steam_ids())

    def __contains__(self, item):
        if not isinstance(item, int) and not isinstance(item, str):
            return False

        steam_id = item
        if isinstance(item, str):
            try:
                steam_id = int(item)
            except ValueError:
                return False

        for json_rating in self.jsons:
            if "playerinfo" not in json_rating:
                continue

            if str(steam_id) in json_rating["playerinfo"]:
                return True

        return False

    def __getitem__(self, item):
        if item not in self:
            raise TypeError

        steam_id = item
        if isinstance(item, str):
            try:
                steam_id = int(item)
            except ValueError:
                raise TypeError

        for json_rating in reversed(self.jsons):
            if "playerinfo" not in json_rating:
                continue

            if str(steam_id) not in json_rating["playerinfo"]:
                continue

            return PlayerRating(json_rating["playerinfo"][str(steam_id)])

        return None

    def __sub__(self, other):
        returned = {}

        if not isinstance(other, RatingProvider):
            raise TypeError("Can't subtract '{}' from a RatingProvider".format(type(other).__name__))

        for steam_id in self:
            if steam_id not in other:
                returned[steam_id] = {gametype: self.gametype_data_for(steam_id, gametype)
                                      for gametype in self.rated_gametypes_for(steam_id)}
                continue

            returned[steam_id] = {}
            for gametype in self.rated_gametypes_for(steam_id):
                if gametype not in other.rated_gametypes_for(steam_id):
                    returned[steam_id][gametype] = self.gametype_data_for(steam_id, gametype)
                    continue
                gametype_diff = self.gametype_data_for(steam_id, gametype)["elo"] - \
                    other.gametype_data_for(steam_id, gametype)["elo"]

                if gametype_diff == 0:
                    continue
                returned[steam_id][gametype] = round(gametype_diff, 2)

        return returned

    @staticmethod
    def from_json(json_response):
        return RatingProvider(json_response)

    def append_ratings(self, json_response):
        self.jsons.append(json_response)

    def player_data_for(self, steam_id):
        return self[steam_id]

    def gametype_data_for(self, steam_id, gametype):
        if gametype not in self[steam_id]:
            return None

        return self[steam_id][gametype]

    def rating_for(self, steam_id, gametype):
        if gametype not in self[steam_id]:
            return None

        if "elo" not in self[steam_id][gametype]:
            return None

        return self[steam_id][gametype]["elo"]

    def games_for(self, steam_id, gametype):
        if gametype not in self[steam_id]:
            return None

        if "games" not in self[steam_id][gametype]:
            return None

        return self[steam_id][gametype]["games"]

    def rated_gametypes_for(self, steam_id):
        player_data = self[steam_id]

        if player_data is None:
            return []

        return [gametype for gametype in player_data if gametype not in FILTERED_OUT_GAMETYPE_RESPONSES]

    def privacy_for(self, steam_id):
        player_data = self[steam_id]

        if player_data is None:
            return None

        if "privacy" not in player_data:
            return "private"

        return player_data["privacy"]

    def rated_steam_ids(self):
        returned = []
        for json_rating in self.jsons:
            if "playerinfo" not in json_rating:
                continue

            returned = returned + [int(steam_id) for steam_id in json_rating["playerinfo"]]

        return [steam_id for steam_id in set(returned)]

    def format_elos(self, steam_id):
        result = ""

        for gametype in self.rated_gametypes_for(steam_id):
            if self.games_for(steam_id, gametype) != 0:
                result += "^2{0}^7: ^4{1}^7 ({2} games)  ".format(gametype.upper(),
                                                                  self[steam_id][gametype]["elo"],
                                                                  self[steam_id][gametype]["games"])
        return result

    def has_ratings_for_all(self, gametype, steam_ids):
        for steam_id in steam_ids:
            if steam_id not in self:
                return False

            if gametype not in self[steam_id]:
                return False

            if self[steam_id][gametype]["games"] == 0:
                return False

        return True


class PlayerRating:
    def __init__(self, ratings, _time=-1, local=False):
        self.ratings = ratings
        self.time = _time
        self.local = local

    def __iter__(self):
        return iter(self.ratings["ratings"])

    def __contains__(self, item):
        if not isinstance(item, str):
            return False

        return item in self.ratings["ratings"]

    def __getitem__(self, item):
        if item not in self:
            raise KeyError

        if not isinstance(item, str):
            raise KeyError

        returned = self.ratings["ratings"][item].copy()
        returned["time"] = self.time
        returned["local"] = self.local
        return returned

    def __getattr__(self, attr):
        if attr not in ["privacy"]:
            raise AttributeError("'{}' object has no atrribute '{}'".format(self.__class__.__name__, attr))

        return self.ratings["privacy"]


class SuggestionRatingStrategy:
    @abstractmethod
    def best_suggestion(self, suggestions):
        pass


class DiffSuggestionRatingStrategy(SuggestionRatingStrategy):
    def best_suggestion(self, suggestions):
        return min(suggestions, key=lambda suggestion: abs(suggestion.avg_diff))


class SuggestionQueue:
    def __init__(self, items=None, strategy=DiffSuggestionRatingStrategy()):
        self.suggestions = items if items is not None else []
        self.strategy = strategy

    def __str__(self):
        return "[{}]".format(", ".join([str(suggestion) for suggestion in self.suggestions]))

    def __len__(self):
        return len(self.suggestions)

    def best_suggestion(self):
        if len(self.suggestions) == 0:
            return None

        if len(self.suggestions) == 1:
            return self.suggestions[0]

        return self.strategy.best_suggestion(self.suggestions)


class Suggestion:
    def __init__(self, red_player, blue_player, avg_diff, stddev_diff=0):
        self.red_player = red_player
        self.blue_player = blue_player
        self.avg_diff = avg_diff
        self.stddev_diff = stddev_diff
        self._agreed = dict()
        self.auto_switch = Plugin.get_cvar("qlx_balancetwo_autoSwitch", bool)

    def __eq__(self, other):
        if not isinstance(other, Suggestion):
            return False

        return self.red_player == other.red_player and self.blue_player == other.blue_player and \
            self.avg_diff == other.avg_diff and self.stddev_diff == other.stddev_diff

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        red_player = "({}, score: {}, dmg: {}, time: {})".format(self.red_player.clean_name,
                                                                 self.red_player.score,
                                                                 self.red_player.stats.damage_dealt,
                                                                 self.red_player.stats.time)
        blue_player = "({}, score: {}, dmg: {}, time: {})".format(self.blue_player.clean_name,
                                                                  self.blue_player.score,
                                                                  self.blue_player.stats.damage_dealt,
                                                                  self.blue_player.stats.time)

        return "Switch {} with {}, resulting diff: {}" \
            .format(red_player, blue_player, self.avg_diff, self.stddev_diff)

    def announcement(self):
        if not self.auto_switch:
            return "SUGGESTION: switch ^6{}^7 with ^6{}^7. Mentioned players can type ^6!a^7 to agree." \
                .format(self.red_player.clean_name, self.blue_player.clean_name)

        return "NOTICE: Server will switch ^6{}^7 with ^6{}^7 at start of next round. " \
               "Both mentioned players need to type ^6!v^7 to veto the switch." \
            .format(self.red_player.clean_name, self.blue_player.clean_name)

    def agree(self, player):
        self._agreed[player.steam_id] = True

    def agreed(self, player):
        return self._agreed.get(player.steam_id, False)

    def all_agreed(self):
        return self.agreed(self.red_player) and self.agreed(self.blue_player)

    def affected_steam_ids(self):
        return [self.red_player.steam_id, self.blue_player.steam_id]

    def validate_players(self):
        self.red_player.update()
        self.blue_player.update()

    def execute(self):
        self.red_player.update()
        self.blue_player.update()

        if self.red_player.team == "spectator":
            raise PlayerMovedToSpecError(self.red_player)

        if self.blue_player.team == "spectator":
            raise PlayerMovedToSpecError(self.blue_player)

        Plugin.switch(self.red_player, self.blue_player)

    @property
    def max_score(self):
        return max(self.red_player.score, self.blue_player.score)

    @property
    def score_sum(self):
        return self.red_player.score + self.blue_player.score


class KickThread(threading.Thread):

    def __init__(self, steam_id, rating, highlow):
        threading.Thread.__init__(self)
        self.steam_id = steam_id
        self.rating = rating
        self.highlow = highlow
        self.go = True

    def try_msg(self):
        time.sleep(5)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        kickmsg = "so you'll be ^6kicked ^7shortly..."
        Plugin.msg("^7Sorry, {} your rating ({}) is too {}, {}".format(player.name, self.rating, self.highlow, kickmsg))

    def try_mute(self):
        @minqlx.next_frame
        def execute():
            try:
                player.mute()
            except ValueError:
                pass

        time.sleep(5)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        execute()

    def try_kick(self):
        @minqlx.next_frame
        def execute():
            try:
                player.kick("^1GOT KICKED!^7 Rating ({}) was too {} for this server.".format(self.rating, self.highlow))
            except ValueError:
                pass

        time.sleep(30)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        execute()

    def run(self):
        self.try_mute()
        self.try_msg()
        self.try_kick()

    def stop(self):
        self.go = False


class PlayerMovedToSpecError(Exception):
    def __init__(self, player):
        self.player = player


class random_iterator:
    def __init__(self, seq):
        self.seq = seq
        self.random_seq = random.sample(self.seq, len(self.seq))
        self.iterator = iter(self.random_seq)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            self.random_seq = random.sample(self.seq, len(self.seq))
            self.iterator = iter(self.random_seq)
            return next(self.iterator)
