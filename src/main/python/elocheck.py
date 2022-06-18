"""
This is a plugin created by ShiN0
Copyright (c) 2020 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.
"""
from __future__ import annotations

import asyncio
from typing import Optional, Any, Callable

import minqlx
from minqlx import Player, AbstractChannel, Plugin
from minqlx.database import Redis

import aiohttp
from requests import Session, RequestException, codes
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore


SteamId = int


PLAYER_BASE = "minqlx:players:{0}"
IPS_BASE = "minqlx:ips"


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
    if text.endswith("^7"):
        return remove_trailing_color_code(text[:-2])

    return text


# noinspection PyPep8Naming
class elocheck(Plugin):
    """
    Checks qlstats for the elos of a player given as well as checking the elos of potentially aliases of the player
    by looking for connection from the same IP as the player has connected from locally.

    Uses:
    * qlx_elocheckPermission (default: "0") The permission for issuing the elocheck
    * qlx_elocheckReplyChannel (default: "public") The reply channel where the elocheck output is put to.
        Possible values: "public" or "private". Any other value leads to public announcements
    * qlx_elocheckShowSteamids (default: "0") Also lists the steam ids of the players checked
    """

    database = Redis  # type: ignore

    __slots__ = ("reply_channel", "show_steam_ids", "balance_api", "previous_gametype", "previous_map",
                 "previous_ratings", "ratings", "rating_diffs", "informed_players")

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_elocheckPermission", "0")
        self.set_cvar_once("qlx_elocheckReplyChannel", "public")
        self.set_cvar_once("qlx_elocheckShowSteamids", "0")

        self.reply_channel: str = self.get_cvar("qlx_elocheckReplyChannel")
        if self.reply_channel != "private":
            self.reply_channel = "public"
        self.show_steam_ids: bool = self.get_cvar("qlx_elocheckShowSteamids", bool)

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

        self.balance_api: str = self.get_cvar("qlx_balanceApi")

        self.previous_map: Optional[str] = None
        self.previous_gametype: Optional[str] = None
        self.previous_ratings: dict[str, RatingProvider] = {}
        self.ratings: dict[str, RatingProvider] = {}
        self.rating_diffs: dict[str, dict[SteamId, Any]] = {}
        self.fetch_elos_from_all_players()

        self.informed_players: list[SteamId] = []

    @minqlx.thread
    def fetch_elos_from_all_players(self):
        asyncio.run(
            self.fetch_ratings([player.steam_id for player in self.players()])
        )

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

        results = await asyncio.gather(*async_requests)

        for rating_provider_name, rating_results in zip(fetched_rating_providers, results):
            self.append_ratings(rating_provider_name, rating_results)

    def fetch_mapbased_ratings(self, steam_ids: list[SteamId], mapname: str = None):
        if mapname is None and (self.game is None or self.game.map is None):
            return None, None

        if mapname is None:
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

    def handle_map_change(self, mapname, _factory):
        async def fetch_ratings_from_newmap(_mapname) -> None:
            steam_ids = [player.steam_id for player in self.players()]
            mapbased_rating_provider_name, mapbased_fetching = \
                self.fetch_mapbased_ratings(steam_ids, mapname=_mapname)
            if mapbased_rating_provider_name is None:
                return
            rating_results = await mapbased_fetching
            self.append_ratings(mapbased_rating_provider_name, rating_results)

        self.informed_players = []
        self.previous_ratings = self.ratings
        self.ratings = {}
        self.fetch_and_diff_ratings()

        asyncio.run(fetch_ratings_from_newmap(mapname.lower()))

    @minqlx.thread
    def fetch_and_diff_ratings(self) -> None:
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

            results = await asyncio.gather(*async_requests)
            for rating_provider_name, rating_results in zip(rating_providers_fetched, results):
                self.append_ratings(rating_provider_name, rating_results)
                self.rating_diffs[rating_provider_name] = \
                    RatingProvider.from_json(rating_results) - self.previous_ratings[rating_provider_name]

        asyncio.run(_fetch_and_diff_ratings())

    def handle_player_connect(self, player):
        @minqlx.thread
        def fetch_player_elos(_player):
            asyncio.run(self.fetch_ratings([_player.steam_id]))

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

        if self.previous_gametype is None:
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

    def wants_to_be_informed(self, steam_id):
        return self.db.get_flag(steam_id, "elocheck:rating_changes", default=False)

    def handle_game_end(self, data):
        if not self.game or bool(data["ABORTED"]):
            return

        self.previous_map = data["MAP"].lower()
        self.previous_gametype = data["GAME_TYPE"].lower()

    def cmd_elocheck(self, player: Player, msg: str, channel: AbstractChannel) -> Optional[int]:
        if len(msg) > 2:
            return minqlx.RET_USAGE

        if len(msg) == 1:
            target = player.steam_id
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

            results = await asyncio.gather(*async_requests)

            truskill = RatingProvider.from_json(results[0])
            a_elo = RatingProvider.from_json(results[1])
            b_elo = RatingProvider.from_json(results[2])
            map_based_truskill = None
            if self.game is not None and self.game.map is not None:
                map_based_truskill = RatingProvider.from_json(results[3])

            if target_steam_id in aliases:
                target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                             target_steam_id, aliases=aliases[target_steam_id])
            else:
                target_player_elos = self.format_player_elos(a_elo, b_elo, truskill, map_based_truskill,
                                                             target_steam_id)
            reply_func(f"{target_player_elos}^7")

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
                reply_func(f"{player_elos}^7")

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
        result = " " * indent + f"{formatted_player_name}^7\n"
        if aliases is not None:
            displayed_aliases = aliases[:]
            if display_name in displayed_aliases:
                displayed_aliases.remove(display_name)
            if len(displayed_aliases) != 0:
                formatted_aliases = "^7, ".join(displayed_aliases[:5])
                if len(displayed_aliases) <= 5:
                    result += " " * indent + f"Aliases used: {formatted_aliases}^7\n"
                else:
                    result += " " * indent + \
                              f"Aliases used: {formatted_aliases}^7, ... (^4!aliases <player>^7 to list all)\n"

        if map_based_truskill is not None:
            formatted_map_based_truskills = map_based_truskill.format_elos(steam_id)
            if formatted_map_based_truskills is not None and len(formatted_map_based_truskills) > 0:
                formatted_mapname = self.game.map.lower()
                result += " " * indent + "  " + f"{formatted_mapname} Truskills: {formatted_map_based_truskills}\n"

        formatted_truskills = truskill.format_elos(steam_id)
        if formatted_truskills is not None and len(formatted_truskills) > 0:
            result += " " * indent + "  " + f"Truskills: {formatted_truskills}\n"

        formatted_a_elos = a_elo.format_elos(steam_id)
        if formatted_a_elos is not None and len(formatted_a_elos) > 0:
            result += " " * indent + "  " + f"Elos: {formatted_a_elos}\n"

        formatted_b_elos = b_elo.format_elos(steam_id)
        if formatted_b_elos is not None and len(formatted_b_elos) > 0:
            result += " " * indent + "  " + f"B-Elos: {formatted_b_elos}\n"

        return result

    def format_player_name(self, steam_id: SteamId) -> str:
        result = ""

        player_name = self.resolve_player_name(steam_id)
        result += f"{player_name}^7"

        if self.show_steam_ids:
            result += f" ({steam_id})"

        return result

    def resolve_player_name(self, steam_id: SteamId) -> str:
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

                if not self.db.exists(PLAYER_BASE.format(target_steam_id)):
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

    def cmd_switch_elo_changes_notifications(self, player: Player, _msg: str, _channel: AbstractChannel) \
            -> Optional[int]:
        flag = self.wants_to_be_informed(player.steam_id)
        self.db.set_flag(player, "elocheck:rating_changes", not flag)

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


FILTERED_OUT_GAMETYPE_RESPONSES = ["steamid"]


class SkillRatingProvider:
    __slots__ = ("name", "url_base", "balance_api", "timeout")

    def __init__(self, name: str, url_base: str, balance_api: str, timeout: int = 7):
        self.name: str = name
        self.url_base: str = url_base
        self.balance_api: str = balance_api
        self.timeout: int = timeout

    async def fetch_elos(self, steam_ids: list[SteamId], *, headers: Optional[dict[str, str]] = None):
        if len(steam_ids) == 0:
            return None

        formatted_steam_ids = "+".join([str(steam_id) for steam_id in steam_ids])
        request_url = f"{self.url_base}{self.balance_api}/{formatted_steam_ids}"
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, headers=headers) as result:
                if result.status != 200:
                    return None
                return await result.json()


TRUSKILLS = SkillRatingProvider("Truskill", "http://stats.houseofquake.com/", "elo/map_based")
A_ELO = SkillRatingProvider("Elo", "http://qlstats.net/", "elo", timeout=15)
B_ELO = SkillRatingProvider("B-Elo", "http://qlstats.net/", "elo_b", timeout=15)


class RatingProvider:
    __slots__ = ("jsons",)

    def __init__(self, json):
        self.jsons = [json]

    def __iter__(self):
        return iter(self.rated_steam_ids())

    def __contains__(self, item) -> bool:
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
    def from_json(json_response) -> RatingProvider:
        return RatingProvider(json_response)

    def append_ratings(self, json_response) -> None:
        self.jsons.append(json_response)

    def player_data_for(self, steam_id: SteamId):
        if steam_id not in self:
            return None

        return self[steam_id]

    def gametype_data_for(self, steam_id: SteamId, gametype: str):
        player_data = self.player_data_for(steam_id)
        if player_data is None:
            return None

        if gametype not in player_data:
            return None

        return player_data[gametype]

    def rating_for(self, steam_id: SteamId, gametype: str) -> Optional[int | float]:
        gametype_data = self.gametype_data_for(steam_id, gametype)
        if gametype_data is None:
            return None

        if "elo" not in gametype_data:
            return None
        return gametype_data["elo"]

    def games_for(self, steam_id: SteamId, gametype: str) -> int:
        gametype_data = self.gametype_data_for(steam_id, gametype)
        if gametype_data is None:
            return 0

        if "games" not in gametype_data:
            return 0

        return gametype_data["games"]

    def rated_gametypes_for(self, steam_id: SteamId) -> list[str]:
        player_data = self[steam_id]

        if player_data is None:
            return []

        return [gametype for gametype in player_data if gametype not in FILTERED_OUT_GAMETYPE_RESPONSES]

    def privacy_for(self, steam_id: SteamId) -> Optional[str]:
        player_data = self[steam_id]

        if player_data is None:
            return None

        if not hasattr(player_data, "privacy"):
            return "private"

        return player_data.privacy

    def rated_steam_ids(self) -> list[SteamId]:
        returned: list[SteamId] = []
        for json_rating in self.jsons:
            if "playerinfo" not in json_rating:
                continue

            returned = returned + [int(steam_id) for steam_id in json_rating["playerinfo"]]

        return list(set(returned))

    def format_elos(self, steam_id: SteamId) -> str:
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

    def __init__(self, ratings, _time: int = -1, local: bool = False):
        self.ratings = ratings
        self.time: int = _time
        self.local: bool = local

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
