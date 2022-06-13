"""
This is a plugin created by ShiN0
Copyright (c) 2020 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.
"""
import asyncio
from enum import Enum

import requests

import minqlx

from minqlx.database import Redis

import aiohttp

PLAYER_BASE = "minqlx:players:{0}"
IPS_BASE = "minqlx:ips"


# noinspection PyPep8Naming
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

    __slots__ = ("reply_channel", "show_steam_ids", "balance_api", "previous_gametype", "previous_ratings",
                 "ratings", "rating_diffs", "informed_players")

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
        self.add_command("aliases", self.cmd_aliases,
                         permission=self.get_cvar("qlx_elocheckPermission", int),
                         usage="[player or steam_id]")
        self.add_command("eloupdates", self.cmd_switch_elo_changes_notifications, usage="<0/1>")

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_LOWEST)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("game_end", self.handle_game_end)

        self.balance_api = self.get_cvar("qlx_balanceApi")

        self.previous_gametype = None
        self.previous_ratings = {}
        self.ratings = {}
        self.rating_diffs = {}
        self.fetch_elos_from_all_players()

        self.informed_players = []

    @minqlx.thread
    def fetch_elos_from_all_players(self):
        asyncio.run(
            self.fetch_ratings([player.steam_id for player in self.players()])
        )

    def configured_rating_provider(self):
        if self.balance_api == "elo":
            return SkillRatingProviders.A_ELO.value
        return SkillRatingProviders.B_ELO.value

    async def fetch_ratings(self, steam_ids):
        configured_rating_provider = self.configured_rating_provider()

        async_requests = [
            self.fetch_elos(steam_ids, configured_rating_provider),
            self.fetch_elos(steam_ids, SkillRatingProviders.TRUESKILLS.value)]

        results = await asyncio.gather(*async_requests)
        qlstats_result = results[0]
        truskills_result = results[1]

        if qlstats_result is not None:
            if configured_rating_provider.name not in self.ratings:
                self.ratings[configured_rating_provider.name] = RatingProvider.from_json(qlstats_result)
            else:
                self.ratings[configured_rating_provider.name].append_ratings(qlstats_result)

        if truskills_result is not None:
            if SkillRatingProviders.TRUESKILLS.value.name not in self.ratings:
                self.ratings[SkillRatingProviders.TRUESKILLS.value.name] = RatingProvider.from_json(truskills_result)
            else:
                self.ratings[SkillRatingProviders.TRUESKILLS.value.name].append_ratings(truskills_result)

    # noinspection PyMethodMayBeStatic
    async def fetch_elos(self, steam_ids, rating_provider):
        if len(steam_ids) == 0:
            return None

        formatted_steam_ids = '+'.join([str(steam_id) for steam_id in steam_ids])
        request_url = f"{rating_provider.url_base}{rating_provider.balance_api}/{formatted_steam_ids}"
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url) as result:
                if result.status != 200:
                    return None
                return await result.json()

    def handle_map_change(self, _mapname, _factory):
        self.informed_players = []
        self.previous_ratings = self.ratings
        self.ratings = {}
        self.fetch_and_diff_ratings()

    @minqlx.thread
    def fetch_and_diff_ratings(self):
        async def _fetch_and_diff_ratings():
            rating_providers_fetched = []
            async_requests = []

            configured_rating_provider = self.configured_rating_provider()
            if configured_rating_provider.name in self.previous_ratings:
                rating_providers_fetched.append(configured_rating_provider.name)
                async_requests.append(
                    self.fetch_ratings(self.previous_ratings[configured_rating_provider.name].rated_players())
                )
            elif SkillRatingProviders.TRUESKILLS.value.name in self.previous_ratings:
                rating_providers_fetched.append(SkillRatingProviders.TRUESKILLS.value.name)
                async_requests.append(
                    self.fetch_ratings(
                        self.previous_ratings[SkillRatingProviders.TRUESKILLS.value.name].rated_players())
                )
            else:
                async_requests.append(
                    self.fetch_ratings([player.steam_id for player in self.players()])
                )
            await asyncio.gather(*async_requests)

            if configured_rating_provider.name in self.previous_ratings and \
                    configured_rating_provider.name in self.ratings:
                self.rating_diffs[configured_rating_provider.name] = \
                    self.ratings[configured_rating_provider.name] - \
                    self.previous_ratings[configured_rating_provider.name]
            if SkillRatingProviders.TRUESKILLS.value.name in self.previous_ratings and \
                    SkillRatingProviders.TRUESKILLS.value.name in self.ratings:
                self.rating_diffs[SkillRatingProviders.TRUESKILLS.value.name] = \
                    self.ratings[SkillRatingProviders.TRUESKILLS.value.name] - \
                    self.previous_ratings[SkillRatingProviders.TRUESKILLS.value.name]

        asyncio.run(_fetch_and_diff_ratings())

    def handle_player_connect(self, player):
        @minqlx.thread
        def fetch_player_elos(_player):
            self.fetch_ratings([_player.steam_id])

        fetch_player_elos(player)

    def handle_team_switch(self, player, _old, new):
        if new not in ["red", "blue", "any"]:
            return

        if player.steam_id in self.informed_players:
            return

        self.informed_players.append(player.steam_id)

        if not self.wants_to_be_informed(player.steam_id):
            return

        changed_ratings = []
        configured_rating_provider = self.configured_rating_provider()
        if configured_rating_provider.name in self.rating_diffs and \
                player.steam_id in self.rating_diffs[configured_rating_provider.name] and \
                self.previous_gametype in self.rating_diffs[configured_rating_provider.name][player.steam_id] and \
                configured_rating_provider.name in self.ratings and \
                player.steam_id in self.ratings[configured_rating_provider.name].rated_players():
            current_elo = self.ratings[configured_rating_provider.name]\
                .rating_for(player.steam_id, self.previous_gametype)
            elo_diff = self.rating_diffs[configured_rating_provider.name][player.steam_id][self.previous_gametype]
            if elo_diff < 0:
                changed_ratings.append(
                    f"^3{configured_rating_provider.name}^7: ^4{current_elo:d}^7 (^1{elo_diff:+d}^7)")
            elif elo_diff > 0:
                changed_ratings.append(
                    f"^3{configured_rating_provider.name}^7: ^4{current_elo:d}^7 (^2{elo_diff:+d}^7)")

        if SkillRatingProviders.TRUESKILLS.value.name in self.rating_diffs and \
                player.steam_id in self.rating_diffs[SkillRatingProviders.TRUESKILLS.value.name] and \
                self.previous_gametype in \
                self.rating_diffs[SkillRatingProviders.TRUESKILLS.value.name][player.steam_id] and \
                SkillRatingProviders.TRUESKILLS.value.name in self.ratings and \
                player.steam_id in self.ratings[SkillRatingProviders.TRUESKILLS.value.name].rated_players():
            current_truskill = \
                self.ratings[SkillRatingProviders.TRUESKILLS.value.name]\
                    .rating_for(player.steam_id, self.previous_gametype)
            truskill_diff = \
                self.rating_diffs[SkillRatingProviders.TRUESKILLS.value.name][player.steam_id][self.previous_gametype]
            if truskill_diff < 0:
                changed_ratings.append(
                    f"^3{SkillRatingProviders.TRUESKILLS.value.name}^7: ^4{current_truskill:.02f}^7 "
                    f"(^1{truskill_diff:+.02f}^7)")
            elif truskill_diff > 0:
                changed_ratings.append(
                    f"^3{SkillRatingProviders.TRUESKILLS.value.name}^7: ^4{current_truskill:.02f}^7 "
                    f"(^2{truskill_diff:+.02f}^7)")

        if len(changed_ratings) == 0:
            return

        formatted_rating_changes = ", ".join(changed_ratings)
        player.tell(f"Your ratings changed since the last map: {formatted_rating_changes}")

    def wants_to_be_informed(self, steam_id):
        return self.db.get_flag(steam_id, "elocheck:rating_changes", default=False)

    def handle_game_end(self, data):
        if not self.game or bool(data["ABORTED"]):
            return

        self.previous_gametype = data["GAME_TYPE"].lower()

    def cmd_elocheck(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.do_elocheck(player, msg[1], channel)
        return minqlx.RET_NONE

    @minqlx.thread
    def do_elocheck(self, player: minqlx.Player, target: str, channel: minqlx.AbstractChannel):
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
                player.tell(f"A total of ^6{len(target_players)}^7 players matched for {target}:")
                out = ""
                for p in target_players:
                    out += " " * 2
                    out += f"{p.id}^6:^7 {p.name}\n"
                player.tell(out[:-1])
                return

            if len(target_players) == 1:
                target_steam_id = target_players.pop().steam_id

            reply_func = self.reply_func(player, channel)

            used_steam_ids = self.used_steam_ids_for(target_steam_id)
            aliases = self.fetch_aliases(used_steam_ids)

            async_requests = [
                self.fetch_elos(used_steam_ids, SkillRatingProviders.A_ELO.value),
                self.fetch_elos(used_steam_ids, SkillRatingProviders.B_ELO.value),
                self.fetch_elos(used_steam_ids, SkillRatingProviders.TRUESKILLS.value)
            ]

            results = await asyncio.gather(*async_requests)

            a_elo = RatingProvider.from_json(results[0])
            b_elo = RatingProvider.from_json(results[1])
            true_skill = RatingProvider.from_json(results[2])

            if target_steam_id in aliases:
                target_player_elos = self.format_player_elos(a_elo, b_elo, true_skill, target_steam_id,
                                                             aliases=aliases[target_steam_id])
            else:
                target_player_elos = self.format_player_elos(a_elo, b_elo, true_skill, target_steam_id)
            reply_func(f"{target_player_elos}^7")

            alternative_steam_ids = used_steam_ids[:]
            alternative_steam_ids.remove(target_steam_id)
            if len(alternative_steam_ids) == 0:
                return

            reply_func("Players from the same IPs:\n")
            for steam_id in used_steam_ids:
                if steam_id in aliases:
                    player_elos = self.format_player_elos(a_elo, b_elo, true_skill, steam_id, aliases=aliases[steam_id])
                else:
                    player_elos = self.format_player_elos(a_elo, b_elo, true_skill, steam_id)
                reply_func(f"{player_elos}^7")

        asyncio.run(_async_elocheck())

    def used_steam_ids_for(self, steam_id):
        if not self.db.exists(PLAYER_BASE.format(steam_id) + ":ips"):
            return [steam_id]

        ips = self.db.smembers(PLAYER_BASE.format(steam_id) + ":ips")

        used_steam_ids = set()
        for ip in ips:
            if not self.db.exists(IPS_BASE + f":{ip}"):
                continue

            used_steam_ids = used_steam_ids | self.db.smembers(IPS_BASE + f":{ip}")

        return [int(_steam_id) for _steam_id in used_steam_ids]

    def format_player_elos(self, a_elo, b_elo, true_skill, steam_id, indent=0, aliases=None):
        result = " " * indent + f"{self.format_player_name(steam_id)}^7\n"
        if aliases is not None:
            if len(aliases) <= 5:
                result += " " * indent + f"Aliases used: {'^7, '.join(aliases[:5])}^7\n"
            else:
                result += " " * indent + f"Aliases used: {'^7, '.join(aliases[:5])}^7, ... " \
                                         f"(^4!aliases <player>^7 to list all)\n"
        formatted_a_elos = self.format_elos(a_elo, steam_id)
        if a_elo is not None and len(formatted_a_elos) > 0:
            result += " " * indent + "  " + f"Elos: {formatted_a_elos}\n"
        formatted_b_elos = self.format_elos(b_elo, steam_id)
        if b_elo is not None and len(formatted_b_elos) > 0:
            result += " " * indent + "  " + f"B-Elos: {formatted_b_elos}\n"
        formatted_trueskills = self.format_elos(true_skill, steam_id)
        if true_skill is not None and len(formatted_trueskills) > 0:
            result += " " * indent + "  " + f"True-Skills: {formatted_trueskills}\n"
        return result

    def format_player_name(self, steam_id):
        result = ""

        player = self.player(steam_id)
        if player is not None:
            result += f"{player.name}^7"
        elif self.db.exists(PLAYER_BASE.format(steam_id) + ":last_used_name"):
            result += f"{self.db[PLAYER_BASE.format(steam_id) + ':last_used_name']}^7"
        else:
            result += "unknown"

        if self.show_steam_ids:
            result += f" ({steam_id})"

        return result

    # noinspection PyMethodMayBeStatic
    def format_elos(self, rating_provider, steam_id):
        result = ""

        for gametype in rating_provider.rated_gametypes_for(steam_id):
            if rating_provider.games_for(steam_id, gametype) != 0:
                result += f"^2{gametype.upper()}^7: " \
                          f"^4{rating_provider.rating_for(steam_id, gametype)}^7 " \
                          f"({rating_provider.games_for(steam_id, gametype)} games)  "
        return result

    def fetch_aliases(self, steam_ids):
        url_template = "http://qlstats.net/aliases/{}.json"

        try:
            result = requests.get(url_template.format("+".join([str(steam_id) for steam_id in steam_ids])), timeout=7)
        except requests.RequestException as exception:
            self.logger.debug(f"request exception: {exception}")
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

    # noinspection PyMethodMayBeStatic
    def identify_reply_channel(self, channel):
        if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                       minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
            return minqlx.CHAT_CHANNEL

        return channel

    def cmd_aliases(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.do_aliases(player, msg[1], channel)
        return minqlx.RET_NONE

    @minqlx.thread
    def do_aliases(self, player: minqlx.Player, target: str, channel: minqlx.AbstractChannel):
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
            player.tell(f"A total of ^6{len(target_players)}^7 players matched for {target}:")
            out = ""
            for p in target_players:
                out += " " * 2
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])
            return

        if len(target_players) == 1:
            target_steam_id = target_players.pop().steam_id

        reply_func = self.reply_func(player, channel)

        aliases = self.fetch_aliases([target_steam_id])

        reply_func(f"{self.format_player_aliases(target_steam_id, aliases[target_steam_id])}^7")

    def format_player_aliases(self, steam_id, aliases):
        result = f"{self.format_player_name(steam_id)}^7\n"
        result += f"Aliases used: {'^7, '.join(aliases)}"
        return result

    def cmd_switch_elo_changes_notifications(self, player, _msg, _channel):
        flag = self.wants_to_be_informed(player.steam_id)
        self.db.set_flag(player, "elocheck:rating_changes", not flag)

        command_prefix = self.get_cvar("qlx_commandPrefix")
        if flag:
            player.tell(
                f"Notifications for elo and truskill changes have been disabled. "
                f"Use ^6{command_prefix}eloupdates^7 to enable them again.")
        else:
            player.tell(
                f"Notifications for elo and truskill changes have been enabled. "
                f"Use ^6{command_prefix}eloupdates^7 to disable them again.")

        return minqlx.RET_STOP_ALL


FILTERED_OUT_GAMETYPE_RESPONSES = ["steamid"]


class SkillRatingProvider:
    def __init__(self, name, url_base, balance_api):
        self.name = name
        self.url_base = url_base
        self.balance_api = balance_api


class SkillRatingProviders(Enum):
    A_ELO = SkillRatingProvider("Elo", "http://qlstats.net/", "elo")
    B_ELO = SkillRatingProvider("B-Elo", "http://qlstats.net/", "elo_b")
    TRUESKILLS = SkillRatingProvider("True-Skill", "http://stats.houseofquake.com/", "elo")


class RatingProvider:
    def __init__(self, json):
        self.jsons = [json]

    def __sub__(self, other):
        returned = {}

        if not isinstance(other, RatingProvider):
            raise TypeError(f"Can't subtract '{type(other).__name__}' from a RatingProvider")

        for steam_id in self.rated_players():
            if steam_id not in other.rated_players():
                returned[steam_id] = {gametype: self.gametype_data_for(steam_id, gametype)
                                      for gametype in self.rated_gametypes_for(steam_id)}
                continue

            returned[steam_id] = {}
            for gametype in self.rated_gametypes_for(steam_id):
                if gametype not in other.rated_gametypes_for(steam_id):
                    returned[steam_id][gametype] = self.gametype_data_for(steam_id, gametype)
                    continue
                gametype_diff = \
                    self.gametype_data_for(steam_id, gametype)["elo"] - \
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
        for json_rating in reversed(self.jsons):
            if "playerinfo" not in json_rating:
                continue

            if str(steam_id) not in json_rating["playerinfo"]:
                continue

            return json_rating["playerinfo"][str(steam_id)]

        return None

    def gametype_data_for(self, steam_id, gametype):
        player_data = self.player_data_for(steam_id)

        if player_data is None:
            return None

        if "ratings" not in player_data:
            return None

        if gametype not in player_data["ratings"]:
            return None

        return player_data["ratings"][gametype]

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
            return None

        if "games" not in gametype_data:
            return None

        return gametype_data["games"]

    def rated_gametypes_for(self, steam_id):
        player_data = self.player_data_for(steam_id)

        if player_data is None:
            return []

        if "ratings" not in player_data:
            return []

        return [gametype for gametype in player_data["ratings"] if gametype not in FILTERED_OUT_GAMETYPE_RESPONSES]

    def privacy_for(self, steam_id):
        player_data = self.player_data_for(steam_id)

        if player_data is None:
            return None

        if "privacy" not in player_data:
            return "private"

        return player_data["privacy"]

    def rated_players(self):
        returned = []
        for json_rating in self.jsons:
            if "playerinfo" not in json_rating:
                continue

            returned = returned + [int(steam_id) for steam_id in json_rating["playerinfo"]]

        return list(set(returned))
