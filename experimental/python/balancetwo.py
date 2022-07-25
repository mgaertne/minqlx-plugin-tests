"""
This is a plugin created by ShiN0
Copyright (c) 2020 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.
"""
from __future__ import annotations

import os
import math
import random
import itertools
import threading
import time
import asyncio

from abc import abstractmethod
from ast import literal_eval
from collections import Counter

from operator import itemgetter
from typing import Callable, Any, Optional, Iterator, Sequence, TypeVar

from datetime import datetime, timedelta

import aiohttp.client_exceptions
from aiohttp import ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry

from requests import Session, RequestException, codes
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore

import minqlx
from minqlx import Plugin, Player, AbstractChannel

from minqlx.database import Redis


SteamId = int

PLAYER_BASE = "minqlx:players:{0}"
IPS_BASE = "minqlx:ips"

SUPPORTED_GAMETYPES = ("ad", "ca", "ctf", "dom", "ft", "tdm")


def requests_retry_session(
        retries: int = 3,
        backoff_factor: float = 0.1,
        status_forcelist: tuple[int, int, int] = (500, 502, 504),
        session: Session = None,
) -> Session:
    session = session or Session()
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


def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel:
    if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                   minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
        return minqlx.CHAT_CHANNEL

    return channel


def remove_trailing_color_code(text: str) -> str:
    if not text.endswith("^7"):
        return text

    return text[:-2]


def other_team(team: str) -> str:
    if team == "red":
        return "blue"
    return "red"


def format_team(team: str) -> str:
    if team == "red":
        return "^1red^7"
    if team == "blue":
        return "^4blue^7"

    return f"^3{team}^7"


def report_ratings_for_team(channel: AbstractChannel, team: list[Player], gametype: str,
                            primary_rating_provider: RatingProvider, secondary_rating_provider: RatingProvider, *,
                            _primary_rating_prefix: str = "", _secondary_rating_prefix: str = "") -> None:
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
                                key=lambda x: primary_rating_provider.rating_for(x.steam_id, gametype), reverse=True)

        for player in primary_sorted:
            primary_rating = primary_rating_provider.rating_for(player.steam_id, gametype)
            secondary_rating = secondary_rating_provider.rating_for(player.steam_id, gametype)
            if player.steam_id in secondary_rating_provider.rated_steam_ids() and \
                    gametype in secondary_rating_provider.rated_gametypes_for(player.steam_id) and \
                    secondary_rating_provider.games_for(player.steam_id, gametype) > 0:
                primary_rating = primary_rating_provider.rating_for(player.steam_id, gametype)
                secondary_rating = secondary_rating_provider.rating_for(player.steam_id, gametype)
                rated_player_texts.append(
                    f"{player.name}^7: {_primary_rating_prefix}{primary_rating}^7/"
                    f"{_secondary_rating_prefix}{secondary_rating}^7")
            else:
                rated_player_texts.append(
                    f"{player.name}^7: {_primary_rating_prefix}{primary_rating}^7/"
                    f"{_secondary_rating_prefix}^5{secondary_rating}^7")

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
                                      key=lambda x: primary_rating_provider.rating_for(x.steam_id, gametype),
                                      reverse=True)

            for player in secondary_sorted:
                primary_rating = primary_rating_provider.rating_for(player.steam_id, gametype)
                secondary_rating = secondary_rating_provider.rating_for(player.steam_id, gametype)
                rated_player_texts.append(
                    f"{player.name}^7: {_primary_rating_prefix}^5{primary_rating}/"
                    f"{_secondary_rating_prefix}{secondary_rating}^7")

        secondary_unranked = [player for player in primary_unranked if player not in secondary_filtered]
        for player in secondary_unranked:
            primary_rating = primary_rating_provider.rating_for(player.steam_id, gametype)
            secondary_rating = secondary_rating_provider.rating_for(player.steam_id, gametype)
            rated_player_texts.append(
                f"{player.name}^7: {_primary_rating_prefix}^5{primary_rating}^7/"
                f"{_secondary_rating_prefix}^5{secondary_rating}^7")

    channel.reply(", ".join(rated_player_texts))


# noinspection PyPep8Naming
class balancetwo(Plugin):
    """
    Checks qlstats for the elos of a player given as well as checking the elos of potentially aliases of the player
    by looking for connection from the same IP as the player has connected locally to.

    Uses:
    * qlx_balancetwo_ratingSystem (default: "mapbased-truskills") Either "mapbased-truskills", "truskills", "a-elo",
        "b-elo".
        In the future there might be a "custom" option for other rating providers.
    * qlx_balancetwo_ratingStrategy (default: "") unused at the moment. For future use
    * qlx_balancetwo_ratingLimit_block (default: "0") block players connecting outside the rating limits from
        connecting at all?
    * qlx_balancetwo_ratingLimit_kick (default: "1") automatically kick player outside the rating limits?
    * qlx_balancetwo_ratingLimit_min (default: "{'a-elo': 800, 'b-elo': 800, 'truskills': 15}")
        dictionary of minimum ratings for players trying to connect, based on a-elo, b-elo, truskills.
        Any value not listed will not be checked, i.e. '{'a-elo': 800}' will only check for a min rating of 800 a-elo.
    * qlx_balancetwo_ratingLimit_max (default: "{'a-elo': 1600, 'b-elo': 1600, 'truskills': 35}")
        dictionary of maximum ratings for players trying to connect, format similar to the minimum ratings.
    * qlx_balancetwo_ratingLimit_minGames (default: "10") dictionary of minimum amount of rated games for players
        trying to connect, format similar to minimum and maximum ratings.
    * qlx_balancetwo_minimumSuggestionDiff (default: "2") minimum difference between avaerage team ratings for
        suggestion switches. This can either be a simple value or a dictionary of max_rounds_played: suggestion value
        to make late changes on teams less likely or more likely.
    * qlx_balancetwo_minimumStddevDiff (default: "50") minimum difference between team standard deviations allowed.
        The format remarks for the minimumSuggestionDiff apply here as well.
    * qlx_balancetwo_autoSwitch (default: "0") automatically execute suggested switches rather than waiting for !agree
        from players.
    * qlx_balancetwo_repeatvetoedsuggestions (default: "0") Whether declined or vetoed suggestions should come up with
        later !teams invocations.
    * qlx_balancetwo_uniquePlayerSwitches (default: "0") During a game, avoid switches that already happened during the
        same game
    * qlx_balancetwo_autoRebalance (default: "1") When new players join, the new players are automatically put on teams
    that result in the lower difference between the teams.
    * qlx_balancetwo_elocheckPermission (default: "0") The permission level for issuing the elocheck
    * qlx_balancetwo_elocheckReplyChannel (default: "public") The reply channel where the elocheck output is put to.
        Possible values: "public" or "private". Any other value leads to public announcements
    * qlx_balancetwo_elocheckShowSteamids (default: "0") Also lists the steam ids of the players checked
    * qlx_qlstatsPrivacyBlock (default: "0") set to 1 to kick any clients with unallowed privacy settings upon connect.
    * qlx_qlstatsPrivacyWhitelist (default: "public, private, untracked")
        List of allowed privacy settings on this server. Take out any value from the default expansive list.
    * qlx_qlstatsPrivacyJoinAttempts (default: "5") amount of join attempts before the player gets kicked,
        if privacyKick is disabled. Set to -1 to disable kicking of players for their join attempts.

    Commands supported:
    * !elocheck <player or steam_id> (aliases: !getrating, !getelo", !elo) (permission level based on
        qlx_balancetwo_elocheckPermission): Checks the ratings of the provided player (or the player herself of omitted)
    * !aliases [player or steam_id] (permission level based on qlx_balancetwo_elocheckPermission):
        Lists the aliases the given player has played under according to qlstats.net
    * !elos (aliases: !ratings, !selo): Lists the ratings of all the players currently connected in a condensed form,
        split by truskills first, then qlstats.net, sorted by teams the players are currently in and even
        sub-categorized between truskills and map-based truskills, or a-elo/b-elo respectively.
    * !eloupdates <0|1>: enables or disables informing the player of updates to her/his ratings after map change whe
        s/he joins a team.
    * !balance (permission level 1): balance the current teams
    * !last [spec|ignore] (permission level 2): with uneven teams, how to proceed with the extra player on round start.
        Either put that player to spec, or ignore the situation and have uneven teams play out their matches.
    * !teams (aliases: !teens): Check the current balance between the teams based on the configured rating provider.
    * !do or !dont (permission level 1): based on qlx_balancetwo_autoSwitch either proceed with the switch suggestion
        or veto it as an admin.
    * !agree (alias: !a) or !veto (alias: !v): based on qlx_balancetwo_autoSwitch either agree to the suggested switch
        or veto it.
    * !nokick <name> (alias: !dontkick) (permission level 2): prevent a particular falling off the configured rating
        limits from being kicked automatically.
    * !privacy [0|1] (permission level: 1): enable or disable qlstats.net privacy checks
    * !add_exception <name|id|steam_id> (alias: !elo_exception) (permission level 3): add a player as an exception
        preventing her/him from being automatically kicked or having to issue !nokick
    * !del_exceptiion <name|id|steam_id> (alias !rem_exception) (permission level 3): remove someone from that list of
        exceptions
    """
    database = Redis

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_balancetwo_ratingSystem", "mapbased-truskills")

        self.set_cvar_once("qlx_balancetwo_ratingLimit_block", "0")
        self.set_cvar_once("qlx_balancetwo_ratingLimit_kick", "1")

        self.set_cvar_once("qlx_balancetwo_ratingLimit_min", "{'a-elo': 800, 'b-elo': 800, 'truskills': 15}")
        self.set_cvar_once("qlx_balancetwo_ratingLimit_max", "{'a-elo': 1600, 'b-elo': 1600, 'truskills': 35}")
        self.set_cvar_once("qlx_balancetwo_ratingLimit_minGames", "10")

        self.set_cvar_once("qlx_balancetwo_minimumSuggestionDiff", "2")
        self.set_cvar_once("qlx_balancetwo_minimumStddevDiff", "50")
        self.set_cvar_once("qlx_balancetwo_lastAction", "spec")

        self.set_cvar_once("qlx_balancetwo_autoSwitch", "0")
        self.set_cvar_once("qlx_balancetwo_repeatvetoedsuggestions", "0")
        self.set_cvar_once("qlx_balancetwo_uniquePlayerSwitches", "0")
        self.set_cvar_once("qlx_balancetwo_autoRebalance", "1")

        self.set_cvar_once("qlx_balancetwo_elocheckPermission", "0")
        self.set_cvar_once("qlx_balancetwo_elocheckReplyChannel", "public")
        self.set_cvar_once("qlx_balancetwo_elocheckShowSteamids", "0")

        self.set_cvar_once("qlx_qlstatsPrivacyBlock", "0")
        self.set_cvar_once("qlx_qlstatsPrivacyWhitelist", "public, private, untracked")
        self.set_cvar_once("qlx_qlstatsPrivacyJoinAttempts", "5")

        self.rating_system: str = self.get_cvar("qlx_balancetwo_ratingSystem")

        self.ratingLimit_kick: bool = self.get_cvar("qlx_balancetwo_ratingLimit_kick", bool)

        self.ratingLimit_min: dict[str, Any] = self.parse_rating_limit("qlx_balancetwo_ratingLimit_min")
        self.ratingLimit_max: dict[str, Any] = self.parse_rating_limit("qlx_balancetwo_ratingLimit_max")
        self.ratingLimit_minGames: dict[str, Any] = self.parse_rating_limit("qlx_balancetwo_ratingLimit_minGames")

        self.minimum_suggestion_diff: dict[int, Any] = \
            self.parse_suggestion_minimum("qlx_balancetwo_minimumSuggestionDiff")
        self.minimum_suggestion_stddev_diff: dict[int, Any] = \
            self.parse_suggestion_minimum("qlx_balancetwo_minimumStddevDiff")

        self.last_action: str = self.get_cvar("qlx_balancetwo_lastAction")

        self.auto_switch: bool = self.get_cvar("qlx_balancetwo_autoSwitch", bool)
        self.repeat_vetoed_switches: bool = self.get_cvar("qlx_balancetwo_repeatvetoedsuggestions", bool)
        self.unique_player_switches: bool = self.get_cvar("qlx_balancetwo_uniquePlayerSwitches", bool)
        self.auto_rebalance: bool = self.get_cvar("qlx_balancetwo_autoRebalance", bool)

        self.reply_channel: str = self.get_cvar("qlx_balancetwo_elocheckReplyChannel")
        if self.reply_channel != "private":
            self.reply_channel = "public"
        self.show_steam_ids: bool = self.get_cvar("qlx_balancetwo_elocheckShowSteamids", bool)

        self.allowed_privacy: list[str] = self.get_cvar("qlx_qlstatsPrivacyWhitelist", list)
        self.max_num_join_attempts: int = self.get_cvar("qlx_qlstatsPrivacyJoinAttempts", int)

        self.connectthreads: dict[str, ConnectThread] = {}
        self.kickthreads: dict[SteamId, KickThread] = {}
        self.exceptions: set[SteamId] = set()

        self.jointimes: dict[SteamId, datetime] = {}
        self.last_new_player_id: Optional[SteamId] = None
        self.previous_teams: tuple[list[SteamId], list[SteamId]] = ([], [])

        self.previous_map: Optional[str] = None
        self.previous_gametype: Optional[str] = None
        self.previous_ratings: dict[str, RatingProvider] = {}

        self.ratings: dict[str, RatingProvider] = {}
        self.rating_diffs: dict[str, dict[SteamId, Any]] = {}

        self.informed_players: list[SteamId] = []

        self.vetoed_switches: list[Suggestion] = []
        self.switched_players: list[SteamId] = []
        self.switch_suggestion: Optional[Suggestion] = None
        self.in_countdown: bool = False

        self.twovstwo_steam_ids: list[SteamId] = []
        self.twovstwo_combinations: list[tuple[SteamId, SteamId]] = []
        self.twovstwo_iter: Iterator[tuple[SteamId, SteamId]] = RandomIterator(self.twovstwo_combinations)

        self.privacy_checks_enabled: bool = True
        self.join_attempts: dict[SteamId, int] = {}

        self.add_command(("elocheck", "getrating", "getelo", "elo"), self.cmd_elocheck,
                         permission=self.get_cvar("qlx_balancetwo_elocheckPermission", int),
                         usage="<player or steam_id>")
        self.add_command("aliases", self.cmd_aliases,
                         permission=self.get_cvar("qlx_balancetwo_elocheckPermission", int),
                         usage="[player or steam_id]")
        self.add_command(("ratings", "elos", "selo"), self.cmd_ratings)

        self.add_command("eloupdates", self.cmd_switch_elo_changes_notifications, usage="<0/1>")

        self.add_command("balance", self.cmd_balance, 1)
        self.add_command("last", self.cmd_last_action, 2, usage="[SPEC|IGNORE]")
        self.add_command(("teams", "teens"), self.cmd_teams)

        self.add_command("do", self.cmd_do, 1)
        self.add_command("dont", self.cmd_dont, 1)
        self.add_command(("agree", "a"), self.cmd_agree, client_cmd_perm=0)
        self.add_command(("veto", "v"), self.cmd_veto, client_cmd_perm=0)

        self.add_command(("nokick", "dontkick"), self.cmd_nokick, 2, usage="[<name>]")

        self.add_command("privacy", self.cmd_switch_privacy_checks, permission=1, usage="[0/1]")

        self.add_command(("add_exception", "elo_exception"), self.cmd_add_exception, 3,
                         usage="<name>|<steam_id> <name>")
        self.add_command(("del_exception", "rem_exception"), self.cmd_del_exception, 3, usage="<name>|<id>|<steam_id>")

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_HIGHEST)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("game_end", self.handle_game_end)

        self.fetch_elos_from_all_players()

    def parse_rating_limit(self, cvar: str) -> dict[str, Any]:
        configured_rating_limits = self.get_cvar(cvar)
        if configured_rating_limits is None:
            return {}
        evaluated_rating_limits = literal_eval(configured_rating_limits)

        if isinstance(evaluated_rating_limits, int):
            if self.rating_system.endswith(TRUSKILLS.name):
                return {TRUSKILLS.name: evaluated_rating_limits}

            return {self.rating_system: evaluated_rating_limits}

        if isinstance(evaluated_rating_limits, dict):
            returned_rating_limits = {}
            for rating_system in evaluated_rating_limits.keys():
                if rating_system.lower() not in ["a-elo", "b-elo", "truskills"]:
                    self.logger.debug(f"Found unknown rating provider in {cvar}: {rating_system} Ignoring")
                    continue
                if rating_system.lower() == "a-elo":
                    rating_provider_name = A_ELO.name
                elif rating_system.lower() == "b-elo":
                    rating_provider_name = B_ELO.name
                else:
                    rating_provider_name = TRUSKILLS.name
                returned_rating_limits[rating_provider_name] = evaluated_rating_limits[rating_system]

            return returned_rating_limits

        self.logger.debug(f"Rating limit cvar {cvar} misconfigured. Could not parse {configured_rating_limits} "
                          f"No rating limits will be used!")
        return {}

    def parse_suggestion_minimum(self, cvar: str) -> dict[int, Any]:
        configured_suggestion_minimum = self.get_cvar(cvar)
        if configured_suggestion_minimum is None:
            return {}
        evaluated_suggestion_minimum = literal_eval(configured_suggestion_minimum)

        if isinstance(evaluated_suggestion_minimum, int):
            return {666: evaluated_suggestion_minimum}

        if isinstance(evaluated_suggestion_minimum, float):
            return {666: evaluated_suggestion_minimum}

        if isinstance(evaluated_suggestion_minimum, dict):
            return evaluated_suggestion_minimum

        self.logger.debug(f"Suggestion minimum cvar {cvar} misconfigured. Could not parse "
                          f"{configured_suggestion_minimum} No suggestion minimums will be used!")
        return {}

    @minqlx.thread
    def fetch_elos_from_all_players(self) -> None:
        asyncio.run(self.fetch_ratings([player.steam_id for player in self.players()]))

    async def fetch_ratings(self, steam_ids: list[SteamId], mapname: str = None) -> None:
        async_requests = []

        for rating_provider in [TRUSKILLS, A_ELO, B_ELO]:
            missing_steam_ids = steam_ids
            if rating_provider in self.ratings:
                rated_steam_ids = self.ratings[rating_provider.name].rated_steam_ids()
                missing_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in rated_steam_ids]

            async_requests.append(rating_provider.fetch_elos(missing_steam_ids))

        mapbased_rating_provider_name, mapbased_fetching = self.fetch_mapbased_ratings(steam_ids, mapname)

        fetched_rating_providers = [TRUSKILLS.name, A_ELO.name, B_ELO.name]
        if mapbased_rating_provider_name is not None:
            fetched_rating_providers.append(mapbased_rating_provider_name)
            async_requests.append(mapbased_fetching)

        results = await asyncio.gather(*async_requests, return_exceptions=True)
        print(results)

        for rating_provider_name, rating_results in zip(fetched_rating_providers, results):
            if isinstance(rating_results, BaseException):
                continue
            self.append_ratings(rating_provider_name, rating_results)

    def fetch_mapbased_ratings(self, steam_ids: list[SteamId], mapname: str = None):
        if mapname is None:
            if self.game is None or self.game.map is None:
                return None, None

            mapname = self.game.map.lower()

        rating_provider_name = f"{mapname} {TRUSKILLS.name}"
        missing_steam_ids = steam_ids
        if rating_provider_name in self.ratings:
            rated_steam_ids = self.ratings[rating_provider_name].rated_steam_ids()
            missing_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in rated_steam_ids]

        if len(missing_steam_ids) == 0:
            return None, None

        return rating_provider_name, TRUSKILLS.fetch_elos(missing_steam_ids, headers={"X-QuakeLive-Map": mapname})

    def append_ratings(self, rating_provider_name: str, json_result: dict[str, Any]) -> None:
        if json_result is None:
            return

        if rating_provider_name in self.ratings:
            self.ratings[rating_provider_name].append_ratings(json_result)
            return

        self.ratings[rating_provider_name] = RatingProvider.from_json(json_result)

    def cmd_elocheck(self, player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 1:
            target = str(player.steam_id)
        else:
            target = msg[1]

        self.do_elocheck(player, target, channel)
        return minqlx.RET_NONE

    @minqlx.thread
    def do_elocheck(self, player: Player, target: str, channel: AbstractChannel) -> None:
        async def _async_elocheck():
            target_players = self.find_target_player(target)

            target_steam_id = None

            if target_players is None or len(target_players) == 0:
                try:
                    target_steam_id = int(target)

                    if not self.db.exists(PLAYER_BASE.format(target_steam_id)):
                        player.tell(f"Sorry, player with steam id {target_steam_id} never played here.")
                        return
                except ValueError:
                    player.tell(f"Sorry, but no players matched your tokens: {target}.")
                    return

            if len(target_players) > 1:
                amount_matched_players = len(target_players)
                player.tell(f"A total of ^6{amount_matched_players}^7 players matched for {target}:")
                out = ""
                for p in target_players:
                    out += " " * 2
                    out += f"{p.id}^6:^7 {p.name}\n"
                player.tell(out[:-1])
                return

            if len(target_players) == 1:
                target_steam_id = target_players.pop().steam_id

            if target_steam_id is None:
                return

            reply_func = self.reply_func(player, channel)

            used_steam_ids = self.used_steam_ids_for(target_steam_id)
            aliases = self.fetch_aliases(used_steam_ids)

            async_requests = [
                TRUSKILLS.fetch_elos(used_steam_ids),
                A_ELO.fetch_elos(used_steam_ids),
                B_ELO.fetch_elos(used_steam_ids),
            ]
            if self.game is not None and self.game.map is not None:
                async_requests.append(
                    TRUSKILLS.fetch_elos(used_steam_ids, headers={"X-QuakeLive-Map": self.game.map.lower()})
                )

            results = await asyncio.gather(*async_requests, return_exceptions=True)

            truskill = RatingProvider.from_json(results[0]) if not isinstance(results[0], Exception) else None
            a_elo = RatingProvider.from_json(results[1]) if not isinstance(results[1], Exception) else None
            b_elo = RatingProvider.from_json(results[2]) if not isinstance(results[2], Exception) else None
            map_based_truskill = None
            if self.game is not None and self.game.map is not None and not isinstance(results[3], BaseException):
                map_based_truskill = RatingProvider.from_json(results[3])

            if target_steam_id in aliases:
                target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                             target_steam_id, aliases=aliases[target_steam_id])
            else:
                target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                             target_steam_id)
            reply_func(f"{target_player_elos}^7\n\n")

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
                reply_func(f"{player_elos}^7\n\n")

        asyncio.run(_async_elocheck())

    def find_target_player(self, target: str) -> list[Player]:
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

    def reply_func(self, player: Player, channel: AbstractChannel) -> Callable[[str], None]:
        if self.reply_channel == "private":
            return player.tell
        return identify_reply_channel(channel).reply

    def used_steam_ids_for(self, steam_id: SteamId) -> list[int]:
        if self.db is None:
            return []

        if not self.db.exists(PLAYER_BASE.format(steam_id) + ":ips"):
            return [steam_id]

        ips = self.db.smembers(PLAYER_BASE.format(steam_id) + ":ips")

        used_steam_ids: set[str] = set()
        for ip in ips:
            if not self.db.exists(IPS_BASE + f":{ip}"):
                continue

            used_steam_ids = used_steam_ids | self.db.smembers(IPS_BASE + f":{ip}")

        return [int(_steam_id) for _steam_id in used_steam_ids]

    def fetch_aliases(self, steam_ids: list[SteamId]) -> dict[SteamId, list[str]]:
        formatted_steam_ids = "+".join([str(steam_id) for steam_id in steam_ids])
        url_template = f"{A_ELO.url_base}aliases/{formatted_steam_ids}.json"

        try:
            result = requests_retry_session().get(url_template, timeout=A_ELO.timeout)
        except RequestException as exception:
            self.logger.debug(f"request exception: {exception}")
            return {}

        if result.status_code != codes.ok:
            return {}
        js = result.json()

        aliases: dict[SteamId, list[str]] = {}
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

    def format_player_elos(self, a_elo: RatingProvider, b_elo: RatingProvider,
                           truskill: RatingProvider, map_based_truskill: Optional[RatingProvider],
                           steam_id: SteamId, indent: int = 0, aliases: list[str] = None) -> str:
        display_name = self.resolve_player_name(steam_id)
        formatted_player_name = self.format_player_name(steam_id)
        result = [" " * indent + f"{formatted_player_name}^7"]
        if aliases is not None:
            displayed_aliases = aliases[:]
            if display_name in displayed_aliases:
                displayed_aliases.remove(display_name)
            if len(displayed_aliases) != 0:
                formatted_aliases = "^7, ".join(displayed_aliases[:5])
                if len(displayed_aliases) <= 5:
                    result.append(" " * indent + f"Aliases used: {formatted_aliases}^7")
                else:
                    result.append(" " * indent +
                                  f"Aliases used: {formatted_aliases}^7, ... (^4!aliases <player>^7 to list all)")

        if map_based_truskill is not None and self.game is not None:
            formatted_map_based_truskills = map_based_truskill.format_elos(steam_id)
            if formatted_map_based_truskills is not None and len(formatted_map_based_truskills) > 0:
                formatted_mapname = self.game.map.lower()
                formatted_line = " " * indent + "  " + f"{formatted_mapname} Truskills: {formatted_map_based_truskills}"
                for line in minqlx.CHAT_CHANNEL.split_long_lines(formatted_line, delimiter="  "):
                    result.append(line)

        formatted_truskills = truskill.format_elos(steam_id) if truskill is not None else None
        if formatted_truskills is not None and len(formatted_truskills) > 0:
            formatted_line = " " * indent + "  " + f"Truskills: {formatted_truskills}"
            for line in minqlx.CHAT_CHANNEL.split_long_lines(formatted_line, delimiter="  "):
                result.append(line)

        formatted_a_elos = a_elo.format_elos(steam_id) if a_elo is not None else None
        if formatted_a_elos is not None and len(formatted_a_elos) > 0:
            formatted_line = " " * indent + "  " + f"Elos: {formatted_a_elos}"
            for line in minqlx.CHAT_CHANNEL.split_long_lines(formatted_line, delimiter="  "):
                result.append(line)

        formatted_b_elos = b_elo.format_elos(steam_id) if b_elo is not None else None
        if formatted_b_elos is not None and len(formatted_b_elos) > 0:
            formatted_line = " " * indent + "  " + f"B-Elos: {formatted_b_elos}"
            for line in minqlx.CHAT_CHANNEL.split_long_lines(formatted_line, delimiter="  "):
                result.append(line)

        return "\n".join(result)

    def format_player_name(self, steam_id: SteamId) -> str:
        result = ""

        player_name = self.resolve_player_name(steam_id)
        result += f"{player_name}^7"

        if self.show_steam_ids:
            result += f" ({steam_id})"

        return result

    def resolve_player_name(self, steam_id: SteamId) -> str:
        if not self.db:
            return "unknown"

        player = self.player(steam_id)
        if player is not None:
            return remove_trailing_color_code(player.name)

        if self.db.exists(PLAYER_BASE.format(steam_id) + ":last_used_name"):
            return remove_trailing_color_code(self.db[PLAYER_BASE.format(steam_id) + ":last_used_name"])

        return "unknown"

    def cmd_aliases(self, player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.do_aliases(player, msg[1], channel)
        return minqlx.RET_NONE

    @minqlx.thread
    def do_aliases(self, player: Player, target: str, channel: AbstractChannel) -> None:
        target_players = self.find_target_player(target)

        target_steam_id = None

        if target_players is None or len(target_players) == 0:
            try:
                target_steam_id = int(target)

                if self.db is None or not self.db.exists(PLAYER_BASE.format(target_steam_id)):
                    player.tell(f"Sorry, player with steam id {target_steam_id} never played here.")
                    return
            except ValueError:
                player.tell(f"Sorry, but no players matched your tokens: {target}.")
                return

        if len(target_players) > 1:
            amount_alternatives = len(target_players)
            player.tell(f"A total of ^6{amount_alternatives}^7 players matched for {target}:")
            out = ""
            for p in target_players:
                out += " " * 2
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])
            return

        if len(target_players) == 1:
            target_steam_id = target_players.pop().steam_id

        if target_steam_id is None:
            return

        reply_func = self.reply_func(player, channel)

        aliases = self.fetch_aliases([target_steam_id])

        if target_steam_id not in aliases:
            reply_func(f"Sorry, no aliases returned for {target_steam_id}")
            return

        formatted_aliases = self.format_player_aliases(target_steam_id, aliases[target_steam_id])
        reply_func(f"{formatted_aliases}^7")

    def format_player_aliases(self, steam_id: SteamId, aliases: list[str]) -> str:
        formatted_player_name = self.format_player_name(steam_id)
        formatted_aliseses = "^7, ".join(aliases)
        return f"{formatted_player_name}^7\nAliases used: {formatted_aliseses}"

    def cmd_ratings(self, _player: Player, _msg: str, channel: AbstractChannel) -> None:
        if self.game is None:
            return

        teams = self.teams()
        gametype = self.game.type_short

        mapname = self.game.map.lower()
        map_based_rating_provider_name = f"{mapname} {TRUSKILLS.name}"

        if TRUSKILLS.name in self.ratings and map_based_rating_provider_name in self.ratings:
            truskills_rating_provider = self.ratings[TRUSKILLS.name]
            mapbased_truskills_rating_provider = self.ratings[map_based_rating_provider_name]

            truskills_url = TRUSKILLS.url_base.split(':')[1].strip('/')
            channel.reply(f"^3{TRUSKILLS.name}^7 ratings (^3general^7/^3map-based^7) (^3{truskills_url}^7)")

            report_ratings_for_team(channel, teams["free"], gametype,
                                    truskills_rating_provider, mapbased_truskills_rating_provider,
                                    _primary_rating_prefix="^6", _secondary_rating_prefix="^6")
            report_ratings_for_team(channel, teams["red"], gametype,
                                    truskills_rating_provider, mapbased_truskills_rating_provider,
                                    _primary_rating_prefix="^1", _secondary_rating_prefix="^1")
            report_ratings_for_team(channel, teams["blue"], gametype,
                                    truskills_rating_provider, mapbased_truskills_rating_provider,
                                    _primary_rating_prefix="^4", _secondary_rating_prefix="^4")
            report_ratings_for_team(channel, teams["spectator"], gametype,
                                    truskills_rating_provider, mapbased_truskills_rating_provider)

        if A_ELO.name in self.ratings and B_ELO.name in self.ratings:
            primary_rating_provider = self.ratings[A_ELO.name]
            secondary_rating_provider = self.ratings[B_ELO.name]

            channel.reply("^5=================================^7")
            qlstats_url = A_ELO.url_base.split(':')[1].strip('/')
            channel.reply(f"^3Elo^7 ratings (^3A elo^7/^3B elo^7) (^3{qlstats_url}^7)")

            report_ratings_for_team(channel, teams["free"], gametype,
                                    primary_rating_provider, secondary_rating_provider,
                                    _primary_rating_prefix="A:^6", _secondary_rating_prefix="B:^6")
            report_ratings_for_team(channel, teams["red"], gametype,
                                    primary_rating_provider, secondary_rating_provider,
                                    _primary_rating_prefix="A:^1", _secondary_rating_prefix="B:^1")
            report_ratings_for_team(channel, teams["blue"], gametype,
                                    primary_rating_provider, secondary_rating_provider,
                                    _primary_rating_prefix="A:^4", _secondary_rating_prefix="B:^4")
            report_ratings_for_team(channel, teams["spectator"], gametype,
                                    primary_rating_provider, secondary_rating_provider,
                                    _primary_rating_prefix="A:", _secondary_rating_prefix="B:")

    def cmd_switch_elo_changes_notifications(self, player: Player, _msg: str, _channel: AbstractChannel) \
            -> Optional[int]:
        if self.db is None:
            return minqlx.RET_NONE

        flag = self.wants_to_be_informed(player.steam_id)
        self.db.set_flag(player, "balancetwo:rating_changes", not flag)

        command_prefix = self.get_cvar("qlx_commandPrefix")
        if flag:
            player.tell(
                "Notifications for elo and truskill changes have been disabled. "
                f"Use ^6{command_prefix}eloupdates^7 to enable them again.")
        else:
            player.tell(
                "Notifications for elo and truskill changes have been enabled. "
                f"Use ^6{command_prefix}eloupdates^7 to disable them again.")

        return minqlx.RET_STOP_ALL

    def wants_to_be_informed(self, steam_id: SteamId) -> bool:
        if self.db is None:
            return False

        return self.db.get_flag(steam_id, "balancetwo:rating_changes", default=False)

    def cmd_balance(self, player: Player, _msg: str, _channel: AbstractChannel) -> Optional[int]:
        if self.game is None:
            return minqlx.RET_NONE

        gt = self.game.type_short
        if gt not in SUPPORTED_GAMETYPES:
            player.tell("This game mode is not supported by the balance plugin.")
            return minqlx.RET_STOP_ALL

        teams = self.teams()
        if len(teams["red"] + teams["blue"]) % 2 != 0:
            player.tell("The total number of players should be an even number.")
            return minqlx.RET_STOP_ALL

        self.callback_balance(minqlx.CHAT_CHANNEL)
        return minqlx.RET_NONE

    def callback_balance(self, channel: AbstractChannel) -> None:
        if not self.game:
            return

        if self.game.state == "in_progress":
            return

        teams = self.teams()
        steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        if len(steam_ids) % 2 == 1:
            player_to_spec = self.identify_player_to_move()

            if player_to_spec is not None:
                steam_ids.remove(player_to_spec.steam_id)

        team1_steam_ids, team2_steam_ids = self.find_balanced_teams(steam_ids)
        if len(team1_steam_ids) == 0 or len(team2_steam_ids) == 0:
            return

        team1 = self.dominant_team_for_steam_ids(team1_steam_ids)
        team2 = other_team(team1)

        team1_to_move_steam_ids = [player.steam_id for player in
                                   [self.player(steam_id) for steam_id in team1_steam_ids]
                                   if player is not None and player.team != team1]
        team2_to_move_steam_ids = [player.steam_id for player in
                                   [self.player(steam_id) for steam_id in team2_steam_ids]
                                   if player is not None and player.team != team2]

        if len(team1_to_move_steam_ids) == 0 and len(team2_to_move_steam_ids) == 0:
            channel.reply("Teams are good! Nothing to balance.")
            return

        for steam_id1, steam_id2 in itertools.zip_longest(team1_to_move_steam_ids, team2_to_move_steam_ids):
            if steam_id1 is not None:
                player1 = self.player(steam_id1)
                if player1 is not None:
                    player1.put(team1)

            if steam_id2 is not None:
                player2 = self.player(steam_id2)
                if player2 is not None:
                    player2.put(team2)

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            if player.steam_id not in team1_steam_ids + team2_steam_ids:
                player.put("spectator")

        if team1 == "red":
            self.report_teams(team1_steam_ids, team2_steam_ids, channel)
        else:
            self.report_teams(team2_steam_ids, team1_steam_ids, channel)
        return

    def dominant_team_for_steam_ids(self, steam_ids: list[SteamId]):
        list_of_teams = []
        for steam_id in steam_ids:
            player = self.player(steam_id)

            if player is None:
                continue

            list_of_teams.append(player.team)

        teams_counter = Counter(list_of_teams)
        if teams_counter["blue"] > teams_counter["red"]:
            return "blue"

        return "red"

    def find_time(self, steam_id: SteamId) -> datetime:
        if steam_id not in self.jointimes:
            self.jointimes[steam_id] = datetime.now()
        return self.jointimes[steam_id]

    def find_balanced_teams(self, steam_ids: list[SteamId]) -> tuple[list[SteamId], list[SteamId]]:
        teams = self.teams()

        if len(teams["red"] + teams["blue"]) < 8:
            return self.find_non_recent_small_balanced_teams(steam_ids)

        return self.find_large_balanced_teams(steam_ids)

    def find_non_recent_small_balanced_teams(self, steam_ids: list[SteamId]) -> tuple[list[SteamId], list[SteamId]]:
        if self.game is None:
            return [], []

        teams = self.teams()

        gt = self.game.type_short

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug(f"Balancing aborted. No ratings found for {configured_rating_provider_name}.")
            return [], []
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        team_combinations = []

        for combination in itertools.combinations(steam_ids, int(len(steam_ids) / 2)):
            red_steam_ids = list(combination)
            blue_steam_ids = [steam_id for steam_id in steam_ids if steam_id not in red_steam_ids]

            previous_red_team, previous_blue_team = self.previous_teams
            if self.previous_teams is not None and (
                    sorted(red_steam_ids) == sorted(previous_red_team) or
                    sorted(red_steam_ids) == sorted(previous_blue_team)):
                continue

            if self.previous_teams is not None and (
                    sorted(blue_steam_ids) == sorted(previous_red_team) or
                    sorted(blue_steam_ids) == sorted(previous_blue_team)):
                continue

            red_avg = self.team_average(gt, red_steam_ids, rating_provider=configured_rating_provider)
            blue_avg = self.team_average(gt, blue_steam_ids, rating_provider=configured_rating_provider)
            diff = abs(red_avg - blue_avg)

            team_combinations.append((red_steam_ids, blue_steam_ids, diff))

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = self.minimum_suggestion_parameters()
        filtered_combinations = [(red_steam_ids, blue_steam_ids, diff) for (red_steam_ids, blue_steam_ids, diff) in
                                 team_combinations if diff < minimum_suggestion_diff]

        if len(filtered_combinations) > 0:
            red_team, blue_team, diff = random.choice(filtered_combinations)
        elif len(team_combinations) > 0:
            red_team, blue_team, diff = min(team_combinations, key=itemgetter(2))
        else:
            red_team = [player.steam_id for player in teams["red"]]
            blue_team = [player.steam_id for player in teams["blue"]]

        return red_team, blue_team

    def find_large_balanced_teams(self, steam_ids: list[SteamId]) -> tuple[list[SteamId], list[SteamId]]:
        if self.game is None:
            return [], []

        gametype = self.game.type_short

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = self.minimum_suggestion_parameters()

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug(f"Balancing aborted. No ratings found for {configured_rating_provider_name}.")
            return [], []

        configured_rating_provider = self.ratings[configured_rating_provider_name]
        rated_steam_ids = [steam_id for steam_id in steam_ids
                           if steam_id in configured_rating_provider.rated_steam_ids()]
        rated_steam_ids = [steam_id for steam_id in rated_steam_ids if
                           gametype in configured_rating_provider.rated_gametypes_for(steam_id)]
        rated_steam_ids = [steam_id for steam_id in rated_steam_ids if
                           configured_rating_provider.rating_for(steam_id, gametype) > 0]
        rated_steam_ids.sort(key=lambda steam_id: configured_rating_provider.rating_for(steam_id, gametype))
        parked_lowest_steam_id = None
        if len(rated_steam_ids) % 2 == 1:
            if self.last_action != "spec":
                parked_lowest_steam_id = rated_steam_ids[0]
            rated_steam_ids.remove(rated_steam_ids[0])

        red_steam_ids: list[SteamId] = []
        blue_steam_ids: list[SteamId] = []

        while len(rated_steam_ids) > 0:
            player1 = rated_steam_ids.pop()
            player2 = rated_steam_ids.pop()

            option1_red_average = self.team_average(gametype, red_steam_ids + [player1],
                                                    rating_provider=configured_rating_provider)
            option1_blue_average = self.team_average(gametype, blue_steam_ids + [player2],
                                                     rating_provider=configured_rating_provider)
            option1_diff = abs(option1_red_average - option1_blue_average)

            option2_red_average = self.team_average(gametype, red_steam_ids + [player2],
                                                    rating_provider=configured_rating_provider)
            option2_blue_average = self.team_average(gametype, blue_steam_ids + [player1],
                                                     rating_provider=configured_rating_provider)
            option2_diff = abs(option2_red_average - option2_blue_average)

            if option1_diff - option2_diff < minimum_suggestion_diff:
                if random.choice(range(100)) > 50:
                    red_steam_ids.append(player1)
                    blue_steam_ids.append(player2)
                else:
                    red_steam_ids.append(player2)
                    blue_steam_ids.append(player1)
            elif option1_diff < option2_diff:
                red_steam_ids.append(player1)
                blue_steam_ids.append(player2)
            else:
                red_steam_ids.append(player2)
                blue_steam_ids.append(player1)

        if parked_lowest_steam_id is None:
            return red_steam_ids, blue_steam_ids

        option1_red_average = self.team_average(gametype, red_steam_ids + [parked_lowest_steam_id],
                                                rating_provider=configured_rating_provider)
        option1_blue_average = self.team_average(gametype, blue_steam_ids, rating_provider=configured_rating_provider)
        option1_diff = abs(option1_red_average - option1_blue_average)

        option2_red_average = self.team_average(gametype, red_steam_ids, rating_provider=configured_rating_provider)
        option2_blue_average = self.team_average(gametype, blue_steam_ids + [parked_lowest_steam_id],
                                                 rating_provider=configured_rating_provider)
        option2_diff = abs(option2_red_average - option2_blue_average)

        if option1_diff < option2_diff:
            red_steam_ids.append(parked_lowest_steam_id)
        else:
            blue_steam_ids.append(parked_lowest_steam_id)

        return red_steam_ids, blue_steam_ids

    def report_teams(self, red_team: list[SteamId], blue_team: list[SteamId], channel: AbstractChannel) -> None:
        if self.game is None:
            return

        gt = self.game.type_short

        configured_rating_provider_name = self.configured_rating_provider_name()
        if configured_rating_provider_name not in self.ratings:
            self.logger.debug(
                f"No ratings for configured rating provider {configured_rating_provider_name} found. Abandoning.")
            return

        configured_rating_provider = self.ratings[configured_rating_provider_name]

        avg_red = self.team_average(gt, red_team, rating_provider=configured_rating_provider)
        avg_blue = self.team_average(gt, blue_team, rating_provider=configured_rating_provider)
        avg_diff = avg_red - avg_blue

        stddev_red = self.team_stddev(red_team, gt, mu=avg_red, rating_provider=configured_rating_provider)
        stddev_blue = self.team_stddev(blue_team, gt, mu=avg_blue, rating_provider=configured_rating_provider)

        absolute_diff = abs(avg_diff)
        if configured_rating_provider_name.endswith(TRUSKILLS.name):
            if avg_diff >= 0.005:
                channel.reply(
                    f"{configured_rating_provider_name} ratings: ^1{avg_red:.02f} (deviation: {stddev_red:.02f}) "
                    f"^7vs ^4{avg_blue:.02f} (deviation: {stddev_blue:.02f})^7 - DIFFERENCE: ^1{absolute_diff:.02f}")
                return
            if avg_diff <= -0.005:
                channel.reply(
                    f"{configured_rating_provider_name} ratings: ^1{avg_red:.02f} (deviation: {stddev_red:.02f}) "
                    f"^7vs ^4{avg_blue:.02f} (deviation: {stddev_blue:.02f})^7 - "
                    f"DIFFERENCE: ^4{absolute_diff:.02f}")
                return
            channel.reply(
                f"{configured_rating_provider_name} ratings: ^1{avg_red:.02f} (deviation: {stddev_red:.02f}) ^7vs "
                f"^4{avg_blue:.02f} (deviation: {stddev_blue:.02f})^7 - Holy shit!")
            return

        if int(avg_diff) > 0:
            channel.reply(f"{configured_rating_provider_name} ratings: ^1{avg_red:.0f} (deviation: {stddev_red:.0f}) "
                          f"^7vs ^4{avg_blue:.0f} (deviation: {stddev_blue:.0f})^7 - DIFFERENCE: ^1{absolute_diff:.0f}")
            return
        if int(avg_diff) < 0:
            channel.reply(f"{configured_rating_provider_name} ratings: ^1{avg_red:.0f} (deviation: {stddev_red:.0f}) "
                          f"^7vs ^4{avg_blue:.0f} (deviation: {stddev_blue:.0f})^7 - DIFFERENCE: ^4{absolute_diff:.0f}")
            return
        channel.reply(
            f"{configured_rating_provider_name} ratings: ^1{avg_red:.0f} (deviation: {stddev_red:.0f}) ^7vs "
            f"^4{avg_blue:.0f} (deviation: {stddev_blue:.0f})^7 - Holy shit!")

    def configured_rating_provider_name(self) -> str:
        if self.game is not None and self.game.map is not None:
            if self.rating_system == "mapbased-truskills":
                formatted_mapname = self.game.map.lower()
                rating_provider_name = f"{formatted_mapname} {TRUSKILLS.name}"
                return rating_provider_name
        if self.rating_system.endswith("truskills"):
            return TRUSKILLS.name

        if self.rating_system == "b-elo":
            return B_ELO.name

        return A_ELO.name

    def team_average(self, gametype: str, steam_ids: list[SteamId], rating_provider: RatingProvider = None) -> float:
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

        return sum(
            [configured_rating_provider.rating_for(steam_id, gametype) for steam_id in steam_ids]) / len(steam_ids)

    def team_stddev(self, steam_ids: list[SteamId], gametype: str, *,
                    mu: Optional[float] = None, rating_provider: Optional[RatingProvider] = None) -> float:
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

        team_elos = [pow(configured_rating_provider.rating_for(steam_id, gametype) - mu, 2) for steam_id in steam_ids]
        return math.sqrt(sum(team_elos) / len(steam_ids))

    def cmd_last_action(self, _player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        if len(msg) < 2:
            channel.reply(f"^7The current action when teams are uneven is: ^6{self.last_action}^7.")
            return minqlx.RET_NONE

        if msg[1] not in ["spec", "ignore"]:
            return minqlx.RET_USAGE

        self.last_action = msg[1]

        channel.reply(f"^7Action has been succesfully changed to: ^6{msg[1]}^7.")
        return minqlx.RET_NONE

    def cmd_teams(self, player: Player, _msg: str, channel: AbstractChannel) -> Optional[int]:
        if self.game is None:
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            player.tell("This game mode is not supported by the balance plugin.")
            return minqlx.RET_STOP_ALL

        teams = self.teams()
        if self.last_action == "spec" and len(teams["red"]) != len(teams["blue"]):
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
        return minqlx.RET_NONE

    @minqlx.thread
    def collect_suggestions(self, teams: dict[str, list[Player]], gametype: str, channel: AbstractChannel):
        possible_switches = self.filtered_suggestions(teams, gametype)

        if not self.repeat_vetoed_switches and len(self.vetoed_switches) > 0:
            possible_switches = list(filter(lambda suggestion: suggestion not in self.vetoed_switches,
                                            possible_switches))

        if self.unique_player_switches and len(self.switched_players) > 0:
            possible_switches = list(filter(lambda suggestion:
                                            suggestion.red_player.steam_id not in self.switched_players
                                            and suggestion.blue_player.steam_id not in self.switched_players,
                                            possible_switches))
        self.handle_suggestions_collected(possible_switches, channel)

    def filtered_suggestions(self, teams: dict[str, list[Player]], gametype: str) -> list[Suggestion]:
        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = \
            self.minimum_suggestion_parameters()

        avg_red = self.team_average(gametype, [player.steam_id for player in teams["red"]],
                                    rating_provider=configured_rating_provider)
        avg_blue = self.team_average(gametype, [player.steam_id for player in teams["blue"]],
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
                               self.satisfies_minimum_suggestion_parameters(suggestion, stddev_diff),
                               possible_switches))

        return list(filter(
            lambda suggestion: abs(suggestion.avg_diff) < avg_diff and
                    avg_diff - abs(suggestion.avg_diff) >= minimum_suggestion_diff,
                    possible_switches))

    def satisfies_minimum_suggestion_parameters(self, suggestion: Suggestion, stddev_diff: float) -> bool:
        minimum_suggestion_diff, minimum_suggestion_stddev_diff = \
            self.minimum_suggestion_parameters()
        if stddev_diff - abs(suggestion.stddev_diff) < minimum_suggestion_stddev_diff:
            return False

        if abs(suggestion.stddev_diff) > minimum_suggestion_stddev_diff:
            return False

        return abs(suggestion.avg_diff) <= minimum_suggestion_diff

    def minimum_suggestion_parameters(self) -> tuple[Any, Any]:
        if self.game is not None:
            played_rounds = self.game.blue_score + self.game.red_score
        else:
            played_rounds = 0

        filtered_criteria = min(filter(lambda x: played_rounds < x[0], self.minimum_suggestion_diff.items()),
                                key=itemgetter(1))
        minimum_suggestion_diff = itemgetter(1)(filtered_criteria)

        filtered_criteria = min(filter(lambda x: played_rounds < x[0], self.minimum_suggestion_stddev_diff.items()),
                                key=itemgetter(1))
        minimum_suggestion_stddev_diff = itemgetter(1)(filtered_criteria)

        return minimum_suggestion_diff, minimum_suggestion_stddev_diff

    def possible_switches(self, teams: dict[str, list[Player]], gametype: str) -> list[Suggestion]:
        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        minimum_suggestion_diff, minimum_suggestion_stddev_diff = \
            self.minimum_suggestion_parameters()

        switches = []
        for red_p in teams["red"]:
            for blue_p in teams["blue"]:
                r = [player.steam_id for player in teams["red"]
                     if player.steam_id != red_p.steam_id] + [blue_p.steam_id]
                b = [player.steam_id for player in teams["blue"]
                     if player.steam_id != blue_p.steam_id] + [red_p.steam_id]
                avg_red = self.team_average(gametype, r, rating_provider=configured_rating_provider)
                avg_blue = self.team_average(gametype, b, rating_provider=configured_rating_provider)
                diff = avg_red - avg_blue

                if diff <= minimum_suggestion_diff:
                    stddev_red = self.team_stddev(r, gametype, mu=avg_red, rating_provider=configured_rating_provider)
                    stddev_blue = self.team_stddev(b, gametype, mu=avg_blue, rating_provider=configured_rating_provider)
                    stddev_diff = stddev_red - stddev_blue
                    suggestion = Suggestion(red_p, blue_p, diff, stddev_diff)

                    switches.append(suggestion)

        return switches

    def handle_suggestions_collected(self, possible_switches: list[Suggestion], channel: AbstractChannel):
        configured_rating_strategy = self.get_cvar("qlx_balancetwo_ratingStrategy")
        if configured_rating_strategy is None:
            return

        rating_strategy = self.rating_strategy(configured_rating_strategy)
        switch_suggestion_queue = SuggestionQueue(possible_switches, rating_strategy)

        if switch_suggestion_queue and len(switch_suggestion_queue) > 0:
            switch = switch_suggestion_queue.best_suggestion()
            if switch is None:
                self.logger.debug("This should never happen.")
                return

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

    # noinspection PyMethodMayBeStatic
    def rating_strategy(self, _strategy: str) -> SuggestionRatingStrategy:
        return DiffSuggestionRatingStrategy()

    def cmd_do(self, _player: Player, _msg: str, _channel: AbstractChannel):
        if self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.switch_suggestion.execute()

    def cmd_dont(self, _player: Player, _msg: str, _channel: AbstractChannel):
        if not self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.msg("An admin prevented the switch! The switch will be terminated.")
        self.vetoed_switches.append(self.switch_suggestion)
        self.switch_suggestion = None

    def cmd_agree(self, player: Player, _msg: str, _channel: AbstractChannel):
        if self.game is None:
            return

        if self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        if self.switch_suggestion.all_agreed():
            return

        self.switch_suggestion.agree(player)

        if not self.switch_suggestion.all_agreed():
            return

        # If the game's in progress, and we're not in the round countdown, wait for next round.
        if self.game.state == "in_progress" and not self.in_countdown:
            self.msg("The switch will be executed at the start of next round.")
            return

        # Otherwise, switch right away.
        self.execute_suggestion()

    def execute_suggestion(self) -> None:
        if self.switch_suggestion is None:
            return
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

    def cmd_veto(self, player: Player, _msg: str, _channel: AbstractChannel):
        if not self.auto_switch:
            return

        if not self.switch_suggestion:
            return

        self.switch_suggestion.agree(player)

        if not self.switch_suggestion.all_agreed():
            return

        self.msg("Both players vetoed! The switch will be terminated.")
        self.switch_suggestion = None

    def cmd_nokick(self, player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        def dontkick(_steam_id) -> None:
            if _steam_id not in self.kickthreads:
                return

            _kickthread = self.kickthreads[_steam_id]

            _resolved_player = self.player(_steam_id)
            if _resolved_player is None:
                return

            _kickthread.stop()

            del self.kickthreads[_steam_id]

            _resolved_player.unmute()

            channel.reply(f"^7An admin has prevented {_resolved_player.name}^7 from being kicked.")

        if self.kickthreads is None or len(self.kickthreads) == 0:
            player.tell("^6Psst^7: There are no people being kicked right now.")
            return minqlx.RET_STOP_ALL

        if len(self.kickthreads) == 1:
            steam_id = next(iter(self.kickthreads))
            dontkick(steam_id)
            self.exceptions.add(steam_id)
            return minqlx.RET_NONE

        _scheduled_players = []
        for steam_id, kickthread in self.kickthreads.items():
            if not kickthread.is_alive():
                continue

            _player = self.player(steam_id)
            if _player is None:
                continue

            _scheduled_players.append(_player)

        _names = [p.name for p in _scheduled_players]

        if len(msg) < 2:
            formatted_alternatives = "^7 or ^6".join(_names)
            player.tell(f"^6Psst^7: did you mean ^6{formatted_alternatives}^7?")
            return minqlx.RET_STOP_ALL

        matched_players = [_player for _player in _scheduled_players if msg[1] in _player.name]

        if len(matched_players) == 0:
            player.tell(f"^6Psst^7: no players matched '^6{msg[1]}^7'?")
            return minqlx.RET_STOP_ALL

        if len(matched_players) > 1:
            _matched_names = [_player.name for _player in matched_players]
            formatted_alternatives = "^7 or ^6".join(_matched_names)
            player.tell(f"^6Psst^7: did you mean ^6{formatted_alternatives}^7?")
            return minqlx.RET_STOP_ALL

        self.exceptions.add(matched_players[0].steam_id)
        dontkick(matched_players[0].steam_id)
        return minqlx.RET_NONE

    def cmd_switch_privacy_checks(self, _player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 1:
            plugin_status = "enabled" if self.privacy_checks_enabled else "disabled"
            channel.reply(f"^7QLStats policy check is {plugin_status}")
            return minqlx.RET_NONE

        if msg[1] not in ["0", "1"]:
            return minqlx.RET_USAGE

        if msg[1] == "1":
            self.enable_policy_check(channel)
            return minqlx.RET_NONE

        self.disable_policy_check(channel)
        return minqlx.RET_NONE

    def disable_policy_check(self, channel: AbstractChannel) -> None:
        self.privacy_checks_enabled = False
        channel.reply("^7QLStats policy check disabled. Everyone will be able to join.")

    def enable_policy_check(self, channel: AbstractChannel) -> None:
        self.privacy_checks_enabled = True
        channel.reply("^7QLStats policy check enabled.")

        teams = self.teams()
        elo_ratings = self.ratings[A_ELO.name]

        for player in teams["red"] + teams["blue"]:
            if player.steam_id not in elo_ratings:
                player.tell("We couldn't fetch your ratings, yet. You will not be able to play, until we did.")
                player.put("spectator")
                continue

            if elo_ratings.privacy_for(player.steam_id) not in self.allowed_privacy:
                player_privacy = elo_ratings.privacy_for(player.steam_id).lower()
                self.msg(f"{player.name}^7 not allowed to join due to {player_privacy} QLStats.net privacy settings.")
                player.center_print("^3Join not allowed. See instructions in console!")
                player.tell(f"Not allowed to join due to ^6{player_privacy}^7 QLStats.net data.")
                player.tell(self.colored_qlstats_instructions())
                player.put("spectator")

    def cmd_add_exception(self, player: Player, msg: str, _channel: AbstractChannel) -> Optional[int]:
        if len(msg) > 3:
            return minqlx.RET_USAGE

        if len(msg) < 3 and len(msg[1]) == 17:
            return minqlx.RET_USAGE

        if msg[1].isdecimal() and len(msg[1]) == 17:
            target_steam_id = int(msg[1])
            target_name = msg[2]
        else:
            target_players = self.find_target_player(msg[1])

            if target_players is None or len(target_players) == 0:
                if not msg[1].isdecimal():
                    player.tell(f"Sorry, but no players matched your tokens: {msg[1]}.")
                    return minqlx.RET_NONE

                target_steam_id = int(msg[1])
                if self.db is None or not self.db.exists(PLAYER_BASE.format(target_steam_id)):
                    player.tell(f"Sorry, player with steam id {target_steam_id} never played here.")
                    return minqlx.RET_NONE
                target_name = str(target_steam_id)

            elif len(target_players) > 1:
                amount_matched_players = len(target_players)
                player.tell(f"A total of ^6{amount_matched_players}^7 players matched for {msg[1]}:")
                out = ""
                for p in target_players:
                    out += " " * 2
                    out += f"{p.id}^6:^7 {p.name}\n"
                player.tell(out[:-1])
                return minqlx.RET_NONE

            else:
                target_player = target_players.pop()
                target_steam_id = target_player.steam_id
                target_name = msg[2] if len(msg) == 3 else target_player.name

        if self.db is None:
            return minqlx.RET_NONE

        current_exception = self.db.get_flag(target_steam_id, "balancetwo:ratinglimit_exception", default=False)
        if current_exception:
            player.tell(f"^6Psst: ^7This ID is already in the exception list under name ^6{target_name}^7!")
            return minqlx.RET_NONE

        self.db.set_flag(target_steam_id, "balancetwo:ratinglimit_exception", value=True)
        player.tell(f"^6Psst: ^2Succesfully ^7added ^6{target_name} ^7to the exception list.")
        return minqlx.RET_NONE

    def cmd_del_exception(self, player: Player, msg: str, _channel: AbstractChannel) -> Optional[int]:
        if len(msg) != 2:
            return minqlx.RET_USAGE

        if msg[1].isdecimal() and len(msg[1]) == 17:
            target_steam_id = int(msg[1])
        else:
            target_players = self.find_target_player(msg[1])

            if target_players is None or len(target_players) == 0:
                if not msg[1].isdecimal():
                    player.tell(f"Sorry, but no players matched your tokens: {msg[1]}.")
                    return minqlx.RET_NONE

                target_steam_id = int(msg[1])
                if self.db is None or not self.db.exists(PLAYER_BASE.format(target_steam_id)):
                    player.tell(f"Sorry, player with steam id {target_steam_id} never played here.")
                    return minqlx.RET_NONE

            elif len(target_players) > 1:
                amount_matched_players = len(target_players)
                player.tell(f"A total of ^6{amount_matched_players}^7 players matched for {msg[1]}:")
                out = ""
                for p in target_players:
                    out += " " * 2
                    out += f"{p.id}^6:^7 {p.name}\n"
                player.tell(out[:-1])
                return minqlx.RET_STOP_ALL

            else:
                target_player = target_players.pop()
                target_steam_id = target_player.steam_id

        if self.db is None:
            return minqlx.RET_NONE

        current_exception = self.db.get_flag(target_steam_id, "balancetwo:ratinglimit_exception", default=False)
        if not current_exception:
            player.tell(f"^6{msg[1]} was not found in the exception list...")
            return minqlx.RET_NONE

        self.db.set_flag(target_steam_id, "balancetwo:ratinglimit_exception", value=False)
        player.tell(f"^6Player {msg[1]} found and removed!")
        return minqlx.RET_NONE

    def handle_map_change(self, mapname: str, _factory: str) -> None:
        self.vetoed_switches = []
        self.switched_players = []
        self.informed_players = []
        self.previous_ratings = self.ratings
        self.ratings = {}
        self.fetch_and_diff_ratings(mapname)
        self.clean_up_kickthreads()

    @minqlx.thread
    def clean_up_kickthreads(self) -> None:
        dead_threads = []
        for steam_id, thread in self.kickthreads.items():
            if not thread.is_alive():
                dead_threads.append(steam_id)

        for dead_thread in dead_threads:
            del self.kickthreads[dead_thread]

    @minqlx.thread
    def fetch_and_diff_ratings(self, mapname: str) -> None:
        async def _fetch_and_diff_ratings():
            rating_providers_fetched = []
            async_requests = []
            for rating_provider in [TRUSKILLS, A_ELO, B_ELO]:
                if rating_provider.name in self.previous_ratings:
                    rating_providers_fetched.append(rating_provider.name)
                    async_requests.append(
                        rating_provider.fetch_elos(self.previous_ratings[rating_provider.name].rated_steam_ids()))

            if self.previous_map is not None:
                mapbased_rating_provider_name = f"{self.previous_map} {TRUSKILLS.name}"
                if mapbased_rating_provider_name in self.previous_ratings:
                    rating_providers_fetched.append(mapbased_rating_provider_name)
                    async_requests.append(
                        TRUSKILLS.fetch_elos(self.previous_ratings[mapbased_rating_provider_name].rated_steam_ids(),
                                             headers={"X-QuakeLive-Map": self.previous_map}))

            results = await asyncio.gather(*async_requests, return_exceptions=True)
            for rating_provider_name, rating_results in zip(rating_providers_fetched, results):
                if isinstance(rating_results, BaseException):
                    continue
                self.append_ratings(rating_provider_name, rating_results)
                self.rating_diffs[rating_provider_name] = \
                    RatingProvider.from_json(rating_results) - self.previous_ratings[rating_provider_name]

        async def fetch_ratings_from_newmap(_mapname) -> None:
            steam_ids = [player.steam_id for player in self.players()]
            mapbased_rating_provider_name, mapbased_fetching = \
                self.fetch_mapbased_ratings(steam_ids, mapname=_mapname)
            if mapbased_rating_provider_name is None:
                return
            rating_results = await mapbased_fetching
            self.append_ratings(mapbased_rating_provider_name, rating_results)

        asyncio.run(_fetch_and_diff_ratings())
        asyncio.run(fetch_ratings_from_newmap(mapname))

    def handle_player_connect(self, player: Player) -> Optional[str]:
        @minqlx.thread
        def fetch_player_elos(_steam_id) -> None:
            asyncio.run(self.fetch_ratings([_steam_id]))
            self.schedule_kick_for_players_outside_rating_limits([_steam_id])

        if self.get_cvar("qlx_balancetwo_ratingLimit_block", bool):
            connect_check = self.check_player_ratings(player.steam_id)
            if connect_check is not None:
                return connect_check

        if self.get_cvar("qlx_qlstatsPrivacyBlock", bool):
            connect_check = self.check_player_privacy(player.steam_id)
            if connect_check is not None:
                return connect_check

        self.record_join_times(player.steam_id)
        fetch_player_elos(player.steam_id)
        return None

    def check_player_ratings(self, steam_id: SteamId) -> Optional[str]:
        if self.db is None or self.db.get_flag(steam_id, "balancetwo:ratinglimit_exception", default=False):
            return None

        if self.game is None:
            return None

        gametype = self.game.type_short

        for rating_provider_name, min_games in self.ratingLimit_minGames.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                rated_games = self.ratings[rating_provider_name].games_for(steam_id, gametype)
                if rated_games < min_games:
                    return f"You have insufficient rated games ({rated_games}) for {gametype} " \
                           f"to play on this server. At least {min_games} {rating_provider_name} rated games required."

        for rating_provider_name, ratingLimit_min in self.ratingLimit_min.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                if player_ratings < ratingLimit_min:
                    return f"Your {rating_provider_name } skill rating ({player_ratings}) is too low " \
                           f"to play on this server. " \
                           f"{rating_provider_name} rating of at least {ratingLimit_min} required."

        for rating_provider_name, ratingLimit_max in self.ratingLimit_max.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                if player_ratings > ratingLimit_max:
                    return f"Your {rating_provider_name } skill rating ({player_ratings}) is too high " \
                           f"to play on this server. " \
                           f"{rating_provider_name} rating of at most {ratingLimit_max} required."

        for rating_provider_name in set(self.ratingLimit_minGames.keys()) | \
                set(self.ratingLimit_min.keys()) | set(self.ratingLimit_max.keys()):
            threadname = f"{steam_id}_{rating_provider_name}"
            if threadname not in self.connectthreads:
                rating_provider = self.rating_provider_for(rating_provider_name)
                if rating_provider is None:
                    self.logger.debug("Famous 'this should never happen' (tm)")
                    return None
                ct = ConnectThread(steam_id, rating_provider)
                self.connectthreads[threadname] = ct
                ct.start()
                self.remove_thread(threadname)

            ct = self.connectthreads[threadname]
            if ct.is_alive():
                return "Fetching your ratings..."

            if ct.fetched_result is not None:
                self.append_ratings(rating_provider_name, ct.fetched_result)

        for rating_provider_name, min_games in self.ratingLimit_minGames.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                rated_games = self.ratings[rating_provider_name].games_for(steam_id, gametype)
                if rated_games < min_games:
                    return f"You have insufficient rated games ({rated_games}) for {gametype} " \
                           f"to play on this server. At least {min_games} {rating_provider_name} rated games required."

        for rating_provider_name, ratingLimit_min in self.ratingLimit_min.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                if player_ratings < ratingLimit_min:
                    return f"Your {rating_provider_name } skill rating ({player_ratings}) is too low " \
                           f"to play on this server. " \
                           f"{rating_provider_name} rating of at least {ratingLimit_min} required."

        for rating_provider_name, ratingLimit_max in self.ratingLimit_max.items():
            if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                if player_ratings > ratingLimit_max:
                    return f"Your {rating_provider_name } skill rating ({player_ratings}) is too high " \
                           f"to play on this server. " \
                           f"{rating_provider_name} rating of at most {ratingLimit_max} required."

        return None

    def rating_provider_for(self, rating_provider_name: str) -> Optional[SkillRatingProvider]:
        if rating_provider_name.endswith(TRUSKILLS.name):
            return TRUSKILLS

        if rating_provider_name == A_ELO.name:
            return A_ELO

        if rating_provider_name == B_ELO.name:
            return B_ELO

        self.logger.debug("ERROR: Unknown rating provider configured! Please fix immediately.")
        return None

    def check_player_privacy(self, steam_id: SteamId) -> Optional[str]:
        if A_ELO.name in self.ratings and steam_id in self.ratings[A_ELO.name]:
            if not self.is_player_with_allowed_privacy_settings(steam_id, self.ratings[A_ELO.name]):
                return minqlx.Plugin.clean_text(self.colored_qlstats_instructions())
            return None

        threadname = f"{steam_id}_privacy"
        if threadname not in self.connectthreads:
            ct = ConnectThread(steam_id, A_ELO)
            self.connectthreads[threadname] = ct
            ct.start()
            self.remove_thread(threadname)

        ct = self.connectthreads[threadname]
        if ct.is_alive():
            return "Fetching your ratings..."

        if ct.fetched_result is not None:
            self.append_ratings(A_ELO.name, ct.fetched_result)

        rating_provider = self.ratings[A_ELO.name]
        if self.is_player_with_allowed_privacy_settings(steam_id, rating_provider):
            return None

        return minqlx.Plugin.clean_text(self.colored_qlstats_instructions())

    @minqlx.delay(30)
    def remove_thread(self, threadname: str) -> None:
        if threadname in self.connectthreads:
            del self.connectthreads[threadname]

    def record_join_times(self, steam_id: SteamId) -> None:
        current_time = datetime.now()
        if steam_id in self.jointimes:
            if (current_time - self.jointimes[steam_id]) < timedelta(seconds=5):
                return

        self.jointimes[steam_id] = current_time

    def schedule_kick_for_players_outside_rating_limits(self, steam_ids: list[SteamId]) -> None:
        if self.game is None:
            return

        if not self.ratingLimit_kick:
            return

        new_steam_ids_to_kick = []
        for steam_id in steam_ids:
            if self.has_exception_to_play(steam_id):
                continue

            if self.is_player_within_configured_rating_limit(steam_id):
                continue

            if steam_id not in self.kickthreads or not self.kickthreads[steam_id].is_alive():
                new_steam_ids_to_kick.append(steam_id)

        if len(new_steam_ids_to_kick) == 0:
            return

        gametype = self.game.type_short
        for steam_id in new_steam_ids_to_kick:
            kickmsg = None
            for rating_provider_name, min_games in self.ratingLimit_minGames.items():
                if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                    rated_games = self.ratings[rating_provider_name].games_for(steam_id, gametype)
                    if rated_games < min_games:
                        kickmsg = f"You have insufficient rated games ({rated_games}) for {gametype} " \
                                  f"to play on this server. " \
                                  f"At least {min_games} {rating_provider_name} rated games required."

            for rating_provider_name, ratingLimit_min in self.ratingLimit_min.items():
                if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                    player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                    if player_ratings < ratingLimit_min:
                        kickmsg = f"Your {rating_provider_name} skill rating ({player_ratings}) is too low " \
                                  f"to play on this server. " \
                                  f"{rating_provider_name} rating of at least {ratingLimit_min} required."

            for rating_provider_name, ratingLimit_max in self.ratingLimit_max.items():
                if rating_provider_name in self.ratings and steam_id in self.ratings[rating_provider_name]:
                    player_ratings = self.ratings[rating_provider_name].rating_for(steam_id, gametype)
                    if player_ratings > ratingLimit_max:
                        kickmsg = f"Your {rating_provider_name} skill rating ({player_ratings}) is too high " \
                                  f"to play on this server. " \
                                  f"{rating_provider_name} rating of at most {ratingLimit_max} required."

            if kickmsg is None:
                self.logger.debug(f"ERROR: Something went wrong when double-checking player rating limits. "
                                  f"Not kicking {steam_id}")
                continue

            t = KickThread(steam_id, kickmsg)
            t.start()
            self.kickthreads[steam_id] = t

    def has_exception_to_play(self, steam_id: SteamId) -> bool:
        if steam_id in self.exceptions:
            return True

        if self.db is not None and self.db.get_flag(steam_id, "balancetwo:ratinglimit_exception", default=False):
            return True

        return False

    def handle_player_disconnect(self, player: Player, _reason: str) -> None:
        if self.last_new_player_id == player.steam_id:
            self.last_new_player_id = None

        if player.steam_id in self.jointimes:
            del self.jointimes[player.steam_id]

        if player.steam_id in self.exceptions:
            self.exceptions.remove(player.steam_id)

        if player.steam_id in self.join_attempts:
            del self.join_attempts[player.steam_id]

    def handle_team_switch_attempt(self, player: Player, old: str, new: str) -> Optional[int]:
        if not self.game:
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        if new in ["red", "blue", "any"]:
            privacy_check = self.check_privacy_settings(player)
            if privacy_check not in [None, minqlx.RET_NONE]:
                return privacy_check

        if new in ["red", "blue", "any", "free"] and not self.has_exception_to_play(player.steam_id):
            rating_check = self.check_rating_limit(player)
            if rating_check not in [None, minqlx.RET_NONE]:
                return rating_check

        if self.game.state != "in_progress":
            return minqlx.RET_NONE

        return self.try_auto_rebalance(player, old, new)

    def check_privacy_settings(self, player: Player) -> Optional[int]:
        if not self.privacy_checks_enabled:
            return minqlx.RET_NONE

        if A_ELO.name not in self.ratings:
            self.logger.debug(f"No data from qlstats for privacy check available. Letting {player.name} play.")
            return minqlx.RET_NONE

        elo_ratings = self.ratings[A_ELO.name]

        if player.steam_id not in elo_ratings:
            player.tell("We couldn't fetch your ratings, yet. You will not be able to join, until we did.")
            return minqlx.RET_STOP_ALL

        if self.is_player_with_allowed_privacy_settings(player.steam_id, elo_ratings):
            return minqlx.RET_NONE

        player_privacy = elo_ratings.privacy_for(player.steam_id).lower()

        if self.max_num_join_attempts > 0:
            if player.steam_id not in self.join_attempts:
                self.join_attempts[player.steam_id] = self.max_num_join_attempts

            self.join_attempts[player.steam_id] -= 1

            if self.join_attempts[player.steam_id] < 0:
                player.kick(minqlx.Plugin.clean_text(self.colored_qlstats_instructions()))
                return minqlx.RET_STOP_ALL
            self.msg(
                f"{player.name}^7 not allowed to join due to {player_privacy} QLStats.net privacy settings. "
                f"{self.join_attempts[player.steam_id]} join attempts before automatically kicking you.")
            player.tell(
                f"Not allowed to join due to ^6{player_privacy}1^7 QLStats.net data. "
                f"{self.join_attempts[player.steam_id]} join attempts before automatically kicking you.")
        else:
            self.msg(
                f"{player.name}^7 not allowed to join due to {player_privacy} QLStats.net privacy settings.")
            player.tell(f"Not allowed to join due to ^6{player_privacy}^7 QLStats.net data.")

        player.center_print("^3Join not allowed. See instructions in console!")
        player.tell(self.colored_qlstats_instructions())
        return minqlx.RET_STOP_ALL

    def is_player_with_allowed_privacy_settings(self, steam_id: SteamId,
                                                rating_provider: Optional[RatingProvider] = None) -> bool:
        elo_ratings = rating_provider
        if elo_ratings is None:
            elo_ratings = self.ratings[A_ELO.name]

        if steam_id not in elo_ratings:
            return False

        player_privacy = elo_ratings.privacy_for(steam_id).lower()
        return player_privacy in self.allowed_privacy

    def colored_qlstats_instructions(self) -> str:
        formatted_privacy = "^7, ^6".join(self.allowed_privacy)
        return f"Error: Open qlstats.net, click Login/Sign-up, set privacy settings to ^6{formatted_privacy}^7, " \
               f"click save and reconnect!"

    def check_rating_limit(self, player: Player) -> Optional[int]:
        if self.is_player_within_configured_rating_limit(player.steam_id):
            return minqlx.RET_NONE

        if self.ratingLimit_kick:
            kickmsg = "so you'll be kicked shortly..."
        else:
            kickmsg = "but you are free to keep watching."

        player.tell(f"^6You do not meet the skill rating requirements to play on this server, {kickmsg}")
        player.center_print(
            f"^6You do not meet the skill rating requirements to play on this server, {kickmsg}")

        return minqlx.RET_STOP_ALL

    def is_player_within_configured_rating_limit(self, steam_id: SteamId) -> bool:
        if self.game is None:
            return True

        gametype = self.game.type_short
        for limited_rating_provider, min_games in self.ratingLimit_minGames.items():
            if limited_rating_provider not in self.ratings:
                self.logger.debug(f"Ratings not found for {steam_id}. "
                                  f"Allowing player to join: {limited_rating_provider}.")
                return True

            ratings = self.ratings[limited_rating_provider]
            if steam_id not in ratings:
                return False

            if ratings.games_for(steam_id, gametype) < min_games:
                return False

        if not self.is_player_above_lower_rating_limit(steam_id):
            return False

        for limited_rating_provider, ratingLimit_max in self.ratingLimit_max.items():
            if limited_rating_provider not in self.ratings:
                self.logger.debug(f"Ratings not found for {steam_id}. "
                                  f"Allowing player to join: {limited_rating_provider}.")
                return True

            ratings = self.ratings[limited_rating_provider]
            if steam_id not in ratings:
                return False

            player_ratings = ratings.rating_for(steam_id, gametype)
            if player_ratings > ratingLimit_max:
                return False

        return True

    def is_player_above_lower_rating_limit(self, steam_id: SteamId) -> bool:
        if self.game is None:
            return True

        gametype = self.game.type_short

        for limited_rating_provider, ratingLimit_min in self.ratingLimit_min.items():
            if limited_rating_provider not in self.ratings:
                self.logger.debug(f"Ratings not found for {limited_rating_provider}. "
                                  f"Allowing player to join: {steam_id}.")
                return True

            ratings = self.ratings[limited_rating_provider]
            if steam_id not in ratings:
                return False

            player_ratings = ratings.rating_for(steam_id, gametype)
            if player_ratings < ratingLimit_min:
                return False

        return True

    def try_auto_rebalance(self, player: Player, old: str, new: str) -> Optional[int]:
        if not self.auto_rebalance:
            return minqlx.RET_NONE

        if self.last_new_player_id == player.steam_id and new in ["spectator", "free"]:
            self.last_new_player_id = None

        if old not in ["spectator", "free"] or new not in ["red", "blue", "any"]:
            return minqlx.RET_NONE

        if player.steam_id == self.last_new_player_id:
            return minqlx.RET_NONE

        if not self.game:
            return minqlx.RET_NONE

        if self.game.state != "in_progress":
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        teams = self.teams()
        if not self.last_new_player_id and len(teams["red"]) == len(teams["blue"]):
            self.last_new_player_id = player.steam_id
            return minqlx.RET_NONE

        if not self.last_new_player_id:
            return minqlx.RET_NONE

        last_new_player = self.player(self.last_new_player_id)
        if not last_new_player:
            self.last_new_player_id = None
            return minqlx.RET_NONE

        other_than_last_players_team = other_team(last_new_player.team)
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
            formatted_team = format_team(other_than_last_players_team)
            last_new_player.tell(
                f"{last_new_player.clean_name}, you have been moved to {formatted_team} to maintain team balance.")
            last_new_player.put(other_than_last_players_team)
            if new in [last_new_player.team]:
                return minqlx.RET_NONE
            if new not in ["any"]:
                formatted_team = format_team(last_new_player.team)
                player.tell(f"{player.clean_name}, you have been moved to {formatted_team} to maintain team balance.")
            player.put(last_new_player.team)
            return minqlx.RET_STOP_ALL

        if new not in ["any", other_than_last_players_team]:
            formatted_team = format_team(other_than_last_players_team)
            player.tell(f"{player.clean_name}, you have been moved to {formatted_team} to maintain team balance.")
            player.put(other_than_last_players_team)
            return minqlx.RET_STOP_ALL

        return minqlx.RET_NONE

    def calculate_player_average_difference(self, gametype: str, team1: list[Player], team2: list[Player]) -> float:
        team1_steam_ids = [player.steam_id for player in team1]
        team2_steam_ids = [player.steam_id for player in team2]
        configured_rating_provider_name = self.configured_rating_provider_name()
        configured_rating_provider = self.ratings[configured_rating_provider_name]

        team1_avg = self.team_average(gametype, team1_steam_ids, rating_provider=configured_rating_provider)
        team2_avg = self.team_average(gametype, team2_steam_ids, rating_provider=configured_rating_provider)
        return abs(team1_avg - team2_avg)

    def handle_team_switch(self, player: Player, _old_team: str, new_team: str) -> None:
        if not player:
            return

        if new_team not in ["red", "blue", "any"]:
            return

        self.inform_about_rating_changes(player)

    def inform_about_rating_changes(self, player: Player) -> None:
        if player.steam_id in self.informed_players:
            return

        self.informed_players.append(player.steam_id)

        if not self.wants_to_be_informed(player.steam_id):
            return

        changed_ratings = []
        previous_truskills = f"{self.previous_map} {TRUSKILLS.name}"

        for rating_provider_name in [previous_truskills, TRUSKILLS.name, A_ELO.name, B_ELO.name]:
            formatted_diffs = self.format_rating_diffs_for_rating_provider_name_and_player(
                rating_provider_name, player.steam_id)
            if formatted_diffs is not None:
                changed_ratings.append(formatted_diffs)

        if len(changed_ratings) == 0:
            return

        formatted_rating_changes = ", ".join(changed_ratings)
        player.tell(f"Your ratings changed since the last map: {formatted_rating_changes}")

    def format_rating_diffs_for_rating_provider_name_and_player(self, rating_provider_name: str, steam_id: SteamId) \
            -> Optional[str]:
        if rating_provider_name not in self.rating_diffs or steam_id not in self.rating_diffs[rating_provider_name] or \
                self.previous_gametype not in self.rating_diffs[rating_provider_name][steam_id] or \
                rating_provider_name not in self.ratings or steam_id not in self.ratings[rating_provider_name]:
            return None

        current_rating = self.ratings[rating_provider_name].rating_for(steam_id, self.previous_gametype)
        rating_diff = self.rating_diffs[rating_provider_name][steam_id][self.previous_gametype]
        if rating_provider_name.endswith(TRUSKILLS.name):
            if rating_diff < 0.0:
                return f"^3{rating_provider_name}^7: ^4{current_rating:.02f}^7 (^1{rating_diff:+.02f}^7)"

            if rating_diff > 0.0:
                return f"^3{rating_provider_name}^7: ^4{current_rating:.02f}^7 (^2{rating_diff:+.02f}^7)"
            return None

        if rating_diff < 0:
            return f"^3{rating_provider_name}^7: ^4{current_rating:d}^7 (^1{rating_diff:+d}^7)"

        if rating_diff > 0:
            return f"^3{rating_provider_name}^7: ^4{current_rating:d}^7 (^2{rating_diff:+d}^7)"

        return None

    @minqlx.delay(5)
    def handle_game_countdown(self) -> None:
        self.msg("^7Balancing on skill ratings...")
        self.callback_balance(minqlx.CHAT_CHANNEL)
        self.allready()

    def handle_round_countdown(self, _round_number: int) -> None:
        @minqlx.next_frame
        def execute_switch_suggestion():
            self.execute_suggestion()

        if not self.auto_switch and self.switch_suggestion is not None and self.switch_suggestion.all_agreed():
            execute_switch_suggestion()

        if self.auto_switch and self.switch_suggestion is not None and not self.switch_suggestion.all_agreed():
            execute_switch_suggestion()

        self.in_countdown = True

        self.announce_evening_up_teams()

    def announce_evening_up_teams(self) -> None:
        player_movements = self.find_player_movements_to_even_teams()
        result: dict[str, list[str]] = {}
        for player, moved_to in player_movements:
            result.setdefault(moved_to, []).append(player.name)

        message = "^6Uneven teams detected!^7 At round start "
        move_announcements: list[str] = []

        if "red" in result or "blue" in result or "free" in result:
            for moved_to in ["red", "blue", "free"]:
                if moved_to not in result:
                    continue
                move_announcements.append(f"server will move {'^7, '.join(result[moved_to])}^7 to"
                                          f" {format_team(moved_to) }")

        if "spectator" in result:
            move_announcements.append(f"server will auto spec {'^7, '.join(result['spectator'])}^7")

        if len(move_announcements) == 0:
            return

        self.msg(f"{message}{' and '.join(move_announcements)}")

    def identify_player_to_move(self) -> Optional[Player]:
        if self.game is None:
            return None

        teams = self.teams()

        if len(teams["blue"]) > len(teams["red"]):
            bigger_team = teams["blue"]
        elif len(teams["red"]) > len(teams["blue"]):
            bigger_team = teams["red"]
        else:
            self.msg("Cannot pick last player since there are none.")
            return None

        if (self.game.red_score + self.game.blue_score) >= 1:
            self.msg(f"Picking someone to {self.last_action} based on score")
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
                    lowest_player = max(lowest_players2, key=lambda _player: self.find_time(_player.steam_id))
        else:
            self.msg(f"Picking someone to {self.last_action} based on join times.")
            lowest_player = max(bigger_team, key=lambda _player: self.find_time(_player.steam_id))
        self.msg(f"Picked {lowest_player.name} from the {lowest_player.team} team.")
        return lowest_player

    def handle_round_start(self, _round_number: int) -> None:
        self.in_countdown = False
        self.last_new_player_id = None

        self.balance_before_round_start()

    @minqlx.thread
    def balance_before_round_start(self) -> None:
        if self.game is None:
            return

        # noinspection PyUnusedLocal
        countdown = self.get_cvar('g_roundWarmupDelay', int)
        if self.game.type_short == "ft":
            # noinspection PyUnusedLocal
            countdown = self.get_cvar('g_freezeRoundDelay', int)

        # noinspection PyUnreachableCode
        if not True:
            time.sleep(max(countdown / 1000 - 0.8, 0))

        team_movements = self.find_player_movements_to_even_teams()
        for player, moved_to in team_movements:
            if not player:
                self.logger.debug("Something went wrong during balancing. Probably player left while calculating.")
                continue

            self.msg(f"^6Uneven teams action^7: Moved {player.name}^7 "
                     f"from {format_team(player.team)} to {format_team(moved_to)}")
            player.put(moved_to)

    def find_player_movements_to_even_teams(self):
        teams = self.teams()

        self.logger.debug(f"{len(teams['red']) = } {len(teams['blue']) = }")
        if len(teams["red"]) == len(teams["blue"]):
            return []

        if len(teams["red"] + teams["blue"]) == 1:
            return []

        team_diff = len(teams["red"]) - len(teams["blue"])

        amount_players_moved = int(abs(team_diff) / 2)

        if team_diff > 0:
            bigger_team = "red"
        else:
            bigger_team = "blue"

        moved_to = other_team(bigger_team)

        self.logger.debug(f"{team_diff = } {amount_players_moved = } {bigger_team = } {moved_to = }")

        if self.switch_suggestion is not None:
            suggestion = self.switch_suggestion
            relevant_players = [player for player in teams[bigger_team]
                                if player.steam_id not in suggestion.affected_steam_ids() + self.switched_players]
        else:
            relevant_players = [player for player in teams[bigger_team]
                                if player.steam_id not in self.switched_players]

        if (self.game.red_score + self.game.blue_score) < 1:
            sorted_team = sorted(relevant_players, key=lambda _player: self.find_time(_player.steam_id), reverse=True)
            if abs(team_diff) % 2 == 1 and self.last_action == "spec":
                return [(sorted_team[0], "spectator")] + \
                       [(player, moved_to) for player in sorted_team[1:amount_players_moved]]

            return [(player, moved_to) for player in sorted_team[:amount_players_moved]]

        sorted_team = sorted(
            sorted(relevant_players, key=lambda player: player.stats.damage_dealt),
            key=lambda player: max(player.score, 0))

        if abs(team_diff) % 2 == 1 and self.last_action == "spec":
            return [(sorted_team[0], "spectator")] + \
                   [(player, moved_to) for player in sorted_team[1:amount_players_moved]]

        return [(player, moved_to) for player in sorted_team[:amount_players_moved]]

    def handle_game_end(self, data: dict[str, Any]) -> None:
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
            self.twovstwo_iter = RandomIterator(self.twovstwo_combinations)

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
    def record_team_stats(self, gametype: str) -> None:
        if self.game is None:
            return

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

        homepath = self.get_cvar("fs_homepath")
        if homepath is None:
            return

        elostats_filename = os.path.join(homepath, "elostats.txt")
        with open(elostats_filename, "a", encoding="utf-8") as elostats_file:
            elostats_file.write(f"{stats}\n")

    def team_stats(self, team: list[Player], gametype: str) -> dict[SteamId, list[Any]]:
        returned = {}
        for player in team:
            a_elo = 0
            if A_ELO.name in self.ratings and player.steam_id in self.ratings[A_ELO.name]:
                a_elo = self.ratings[A_ELO.name].rating_for(player.steam_id, gametype)
            b_elo = 0
            if B_ELO.name in self.ratings and player.steam_id in self.ratings[B_ELO.name]:
                b_elo = self.ratings[B_ELO.name].rating_for(player.steam_id, gametype)
            truskill = 0
            if TRUSKILLS.name in self.ratings and player.steam_id in self.ratings[TRUSKILLS.name]:
                truskill = self.ratings[TRUSKILLS.name].rating_for(player.steam_id, gametype)
            returned[player.steam_id] = [a_elo, b_elo, truskill]

        return returned


FILTERED_OUT_GAMETYPE_RESPONSES = ["steamid"]


class SkillRatingProvider:
    __slots__ = ("name", "url_base", "balance_api", "timeout")

    def __init__(self, name, url_base, balance_api, timeout=7):
        self.name = name
        self.url_base = url_base
        self.balance_api = balance_api
        self.timeout = timeout

    async def fetch_elos(self, steam_ids: list[SteamId], headers: Optional[dict[str, str]] = None):
        if len(steam_ids) == 0:
            return None

        formatted_steam_ids = "+".join([str(steam_id) for steam_id in steam_ids])
        request_url = f"{self.url_base}{self.balance_api}/{formatted_steam_ids}"
        retry_options = ExponentialRetry(attempts=3, factor=0.1,
                                         statuses={500, 502, 504},
                                         exceptions={aiohttp.ClientResponseError, aiohttp.ClientPayloadError})
        async with RetryClient(raise_for_status=False, retry_options=retry_options,
                               timeout=ClientTimeout(total=5, connect=3, sock_connect=3, sock_read=5)) as retry_client:
            async with retry_client.get(request_url, headers=headers) as result:
                if result.status != 200:
                    return None
                return await result.json()


TRUSKILLS = SkillRatingProvider("Truskill", "http://stats.houseofquake.com/", "elo/map_based")
A_ELO = SkillRatingProvider("Elo", "http://qlstats.net/", "elo", timeout=15)
B_ELO = SkillRatingProvider("B-Elo", "http://qlstats.net/", "elo_b", timeout=15)


class RatingProvider:
    __slots__ = ("jsons", )

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
            except ValueError as e:
                raise TypeError from e

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
            formatted_other_type = type(other).__name__
            raise TypeError(f"Can't subtract '{formatted_other_type}' from a RatingProvider")

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
                gametype_diff = self.rating_for(steam_id, gametype) - other.rating_for(steam_id, gametype)

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
        if steam_id not in self:
            return None

        return self[steam_id]

    def gametype_data_for(self, steam_id, gametype):
        player_data = self.player_data_for(steam_id)
        if player_data is None:
            return None

        if gametype not in player_data:
            return None

        return player_data[gametype]

    def rating_for(self, steam_id, gametype):
        gametype_data = self.gametype_data_for(steam_id, gametype)
        if gametype_data is None:
            return None

        if "elo" not in gametype_data:
            return None
        return gametype_data["elo"]

    def games_for(self, steam_id, gametype):
        gametype_data = self.gametype_data_for(steam_id, gametype)
        if gametype_data is None:
            return 0

        if "games" not in gametype_data:
            return 0

        return gametype_data["games"]

    def rated_gametypes_for(self, steam_id):
        player_data = self[steam_id]

        if player_data is None:
            return []

        return [gametype for gametype in player_data if gametype not in FILTERED_OUT_GAMETYPE_RESPONSES]

    def privacy_for(self, steam_id):
        player_data = self[steam_id]

        if player_data is None:
            return None

        if not hasattr(player_data, "privacy"):
            return "private"

        return player_data.privacy

    def rated_steam_ids(self):
        returned: list[SteamId] = []
        for json_rating in self.jsons:
            if "playerinfo" not in json_rating:
                continue

            returned = returned + [int(steam_id) for steam_id in json_rating["playerinfo"]]

        return list(set(returned))

    def format_elos(self, steam_id):
        result = ""

        for gametype in self.rated_gametypes_for(steam_id):
            if self.games_for(steam_id, gametype) != 0:
                formatted_gametype = gametype.upper()
                elo = self.rating_for(steam_id, gametype)
                games = self.games_for(steam_id, gametype)
                result += f"^2{formatted_gametype}^7: ^4{elo}^7 ({games} games)  "
        return result


class PlayerRating:
    __slots__ = ("ratings", "time", "local")

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
            raise AttributeError(f"'{self.__class__.__name__}' object has no atrribute '{attr}'")

        return self.ratings[attr]


class ConnectThread(threading.Thread):
    __slots__ = ("rating_provider", "_steam_id", "fetched_result")

    def __init__(self, steam_id: SteamId, rating_provider: SkillRatingProvider):
        super().__init__()
        self.rating_provider: SkillRatingProvider = rating_provider
        self._steam_id: SteamId = steam_id
        self.fetched_result: Optional[dict[str, Any]] = None

    def run(self) -> None:
        async def fetch_ratings():
            self.fetched_result = await self.rating_provider.fetch_elos([self._steam_id])

        asyncio.run(fetch_ratings())


class SuggestionRatingStrategy:
    @abstractmethod
    def best_suggestion(self, suggestions: list[Suggestion]) -> Suggestion:
        pass


class DiffSuggestionRatingStrategy(SuggestionRatingStrategy):
    def best_suggestion(self, suggestions: list[Suggestion]) -> Suggestion:
        return min(suggestions, key=lambda suggestion: abs(suggestion.avg_diff))


class SuggestionQueue:
    __slots__ = ("suggestions", "strategy")

    def __init__(self, items: list[Suggestion] = None,
                 strategy: SuggestionRatingStrategy = DiffSuggestionRatingStrategy()):
        self.suggestions = items if items is not None else []
        self.strategy = strategy

    def __str__(self) -> str:
        formatted_suggestion = ", ".join([str(suggestion) for suggestion in self.suggestions])
        return f"[{formatted_suggestion}]"

    def __len__(self) -> int:
        return len(self.suggestions)

    def best_suggestion(self) -> Optional[Suggestion]:
        if len(self.suggestions) == 0:
            return None

        if len(self.suggestions) == 1:
            return self.suggestions[0]

        return self.strategy.best_suggestion(self.suggestions)


class Suggestion:
    __slots__ = ("red_player", "blue_player", "avg_diff", "stddev_diff", "_agreed", "auto_switch")

    def __init__(self, red_player: Player, blue_player: Player, avg_diff: float, stddev_diff: float = 0):
        self.red_player = red_player
        self.blue_player = blue_player
        self.avg_diff = avg_diff
        self.stddev_diff = stddev_diff
        self._agreed: list[SteamId] = []
        self.auto_switch = Plugin.get_cvar("qlx_balancetwo_autoSwitch", bool)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Suggestion):
            return False

        return self.red_player == other.red_player and self.blue_player == other.blue_player and \
            self.avg_diff == other.avg_diff and self.stddev_diff == other.stddev_diff

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        red_player = f"({self.red_player.clean_name}, score: {self.red_player.score}, " \
                     f"dmg: {self.red_player.stats.damage_dealt}, time: {self.red_player.stats.time})"
        blue_player = f"({self.blue_player.clean_name}, score: {self.blue_player.score}, " \
                      f"dmg: {self.blue_player.stats.damage_dealt}, time: {self.blue_player.stats.time})"

        return f"Switch {red_player} with {blue_player}, resulting diff: {self.avg_diff}"

    def announcement(self) -> str:
        if not self.auto_switch:
            return f"SUGGESTION: switch ^6{self.red_player.clean_name}^7 with ^6{self.blue_player.clean_name}^7. " \
                   f"Mentioned players can type ^6!a^7 to agree."

        return f"NOTICE: Server will switch ^6{self.red_player.clean_name}^7 with ^6{self.blue_player.clean_name}^7 " \
               f"at start of next round. Both mentioned players need to type ^6!v^7 to veto the switch."

    def agree(self, player: Player) -> None:
        self._agreed.append(player.steam_id)

    def agreed(self, player: Player) -> bool:
        return player.steam_id in self._agreed

    def all_agreed(self) -> bool:
        return self.agreed(self.red_player) and self.agreed(self.blue_player)

    def affected_steam_ids(self) -> list[SteamId]:
        return [self.red_player.steam_id, self.blue_player.steam_id]

    def execute(self) -> None:
        self.red_player.update()
        self.blue_player.update()

        if self.red_player.team == "spectator":
            raise PlayerMovedToSpecError(self.red_player)

        if self.blue_player.team == "spectator":
            raise PlayerMovedToSpecError(self.blue_player)

        Plugin.switch(self.red_player, self.blue_player)

    @property
    def max_score(self) -> int:
        return max(self.red_player.score, self.blue_player.score)

    @property
    def score_sum(self) -> int:
        return self.red_player.score + self.blue_player.score


class KickThread(threading.Thread):
    __slots__ = ("steam_id", "kickmsg", "go")

    def __init__(self, steam_id: SteamId, kickmsg: str):
        threading.Thread.__init__(self)
        self.steam_id = steam_id
        self.kickmsg = kickmsg
        self.go = True

    def try_msg(self) -> None:
        time.sleep(5)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        Plugin.msg(f"^7Sorry, {player.name} {self.kickmsg}, so you'll be ^6kicked ^7shortly...")

    def try_mute(self) -> None:
        @minqlx.next_frame
        def execute(_player: Player) -> None:
            try:
                _player.mute()
            except ValueError:
                pass

        time.sleep(5)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        execute(player)

    def try_kick(self) -> None:
        @minqlx.next_frame
        def execute(_player: Player) -> None:
            try:
                _player.kick(f"^1GOT KICKED!^7 {self.kickmsg}")
            except ValueError:
                pass

        time.sleep(30)
        player = Plugin.player(self.steam_id)
        if not player:
            return

        if not self.go:
            return

        execute(player)

    def run(self) -> None:
        self.try_mute()
        self.try_msg()
        self.try_kick()

    def stop(self) -> None:
        self.go = False


class PlayerMovedToSpecError(Exception):
    __slots__ = ("player",)

    def __init__(self, player: Player):
        super().__init__()

        self.player = player


T = TypeVar('T')


class RandomIterator:
    __slots__ = ("seq", "random_seq", "iterator")

    def __init__(self, seq: Sequence[T]):
        self.seq = seq
        self.random_seq = random.sample(self.seq, len(self.seq))
        self.iterator = iter(self.random_seq)

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        try:
            return next(self.iterator)
        except StopIteration:
            self.random_seq = random.sample(self.seq, len(self.seq))
            self.iterator = iter(self.random_seq)
            return next(self.iterator)
