import time
from datetime import datetime, timedelta
import threading
import requests
from requests import RequestException, Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore

import minqlx
from minqlx import Plugin, CHAT_CHANNEL
from minqlx.database import Redis

APPLICATION_GAMES_KEY = "minqlx:players:{}:minelo:games"

SUPPORTED_GAMETYPES = ("ca", "ctf", "dom", "ft", "tdm", "duel", "ffa")


def requests_retry_session(
    retries=3,
    backoff_factor=0.1,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def identify_reply_channel(channel):
    if channel in [
        minqlx.RED_TEAM_CHAT_CHANNEL,
        minqlx.BLUE_TEAM_CHAT_CHANNEL,
        minqlx.SPECTATOR_CHAT_CHANNEL,
        minqlx.FREE_CHAT_CHANNEL,
    ]:
        return minqlx.CHAT_CHANNEL

    return channel


def is_player_in_exception_list(player):
    # noinspection PyProtectedMember
    if "mybalance" in Plugin._loaded_plugins:
        # noinspection PyProtectedMember
        mybalance_plugin = Plugin._loaded_plugins["mybalance"]
        # noinspection PyUnresolvedReferences
        return player.steam_id in mybalance_plugin.exceptions

    # noinspection PyProtectedMember
    if "balancetwo" in Plugin._loaded_plugins:
        # noinspection PyProtectedMember
        balancetwo_plugin = Plugin._loaded_plugins["balancetwo"]
        # noinspection PyUnresolvedReferences
        return player.steam_id in balancetwo_plugin.exceptions

    return False


# noinspection PyPep8Naming
class merciful_elo_limit(Plugin):
    """
    Uses:
    * qlx_merciful_minelo (default: 800) The minimum elo for application games. Players below this limit are tracked.
    * qlx_mercifulelo_applicationgames (default: 10) The amount of application games a player below the minimum elo
    will be able to play
    * qlx_mercifulelo_daysbanned (default: 30) The number of days a low elo player gets banned after using up his
    application games
    """

    database = Redis

    def __init__(self):
        super().__init__()
        self.set_cvar_once("qlx_mercifulelo_minelo", "800")
        self.set_cvar_once("qlx_mercifulelo_applicationgames", "10")
        self.set_cvar_once("qlx_mercifulelo_daysbanned", "30")

        self.min_elo = self.get_cvar("qlx_mercifulelo_minelo", int) or 800
        self.application_games = self.get_cvar("qlx_mercifulelo_applicationgames", int) or 10
        self.banned_days = self.get_cvar("qlx_mercifulelo_daysbanned", int) or 30

        self.tracked_player_sids = set()
        self.announced_player_elos = set()

        # Collection of threads looking up elo of players {steam_id: thread }
        self.connectthreads = {}

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect, priority=minqlx.PRI_HIGHEST)
        self.add_hook("player_loaded", self.handle_player_loaded, priority=minqlx.PRI_HIGHEST)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)

        self.add_command("mercis", self.cmd_mercis, permission=1)
        self.add_command("merci", self.cmd_merci, permission=2, usage="[player]")

    def handle_map_change(self, _mapname, _factory):
        self.tracked_player_sids = set()
        self.announced_player_elos = set()
        self.fetch_elos_of_players(Plugin.players())

    def handle_player_connect(self, player):
        if is_player_in_exception_list(player):
            return minqlx.RET_NONE

        if not self.game:
            return minqlx.RET_NONE

        if not self.player_has_been_tracked(player.steam_id):
            return minqlx.RET_NONE

        # If want to block, check for a lookup thread. Else create one
        if player.steam_id not in self.connectthreads:
            ct = ConnectThread(player.steam_id, self.get_cvar("qlx_balanceApi"))
            self.connectthreads[player.steam_id] = ct
            ct.start()
            self.remove_thread(player.steam_id)  # remove it after a while

        # Check if thread is ready or not
        ct = self.connectthreads[player.steam_id]
        if not ct.is_parsed():
            return "Fetching your skill rating..."

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        elo = ct.elo_for(gametype)
        if not elo:
            return minqlx.RET_NONE

        if int(elo) > self.min_elo:
            return minqlx.RET_NONE

        if self.player_has_application_games_left(player.steam_id):
            return minqlx.RET_NONE

        next_game_available_at = self.next_game_available_at(player.steam_id)
        if next_game_available_at is None:
            return minqlx.RET_NONE
        return (
            f"You used up all your below {self.application_games} elo application matches. "
            f"Next application game available at {next_game_available_at}"
        )

    def player_has_been_tracked(self, steam_id):
        return self.db.exists(APPLICATION_GAMES_KEY.format(steam_id))

    def gaming_period_start(self):
        current_time = datetime.now()
        delta = timedelta(days=self.banned_days)

        gaming_period_start = current_time - delta

        return gaming_period_start.timestamp()

    def player_has_application_games_left(self, steam_id):
        games_in_period = self.application_games_of_player(steam_id)

        return len(games_in_period) < self.application_games

    def application_games_of_player(self, steam_id):
        return self.db.zrangebyscore(APPLICATION_GAMES_KEY.format(steam_id), self.gaming_period_start(), "+INF")

    def next_game_available_at(self, steam_id):
        games_in_period = self.application_games_of_player(steam_id)

        timestamped_games = [float(timestamp) for timestamp in games_in_period]
        if len(timestamped_games) == 0:
            return None
        min_game = min(timestamped_games)

        next_game_available = datetime.fromtimestamp(min_game) + timedelta(days=self.banned_days)

        return next_game_available.strftime("%Y-%m-%d %H:%M:%S")

    def fetch_elos_of_players(self, players):
        if not self.game:
            return

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return

        # noinspection PyProtectedMember
        if "balancetwo" in Plugin._loaded_plugins:
            self.callback_ratings([], CHAT_CHANNEL)
            return

        # noinspection PyProtectedMember
        if "balance" not in Plugin._loaded_plugins:
            self.logger.warning(
                "Balance plugin not found. Merciful elo limits just work with the elos from the balance plugin"
            )
            return

        # noinspection PyProtectedMember
        balance_plugin = Plugin._loaded_plugins["balance"]

        player_ratings = {p.steam_id: gametype for p in players}
        # noinspection PyUnresolvedReferences
        balance_plugin.add_request(player_ratings, self.callback_ratings, CHAT_CHANNEL)

    def handle_player_loaded(self, player):
        self.handle_player_after_fetching_ratings(player)

    def handle_round_countdown(self, _round_number):
        if not self.game:
            return

        teams = Plugin.teams()
        self.fetch_elos_of_players(teams["red"] + teams["blue"])

    def callback_ratings(self, _players, _channel):
        if not self.game:
            return

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            self.handle_player_after_fetching_ratings(player)

    def handle_player_after_fetching_ratings(self, player):
        if is_player_in_exception_list(player):
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if player.steam_id in self.tracked_player_sids:
            return

        if elo < self.min_elo:
            if not self.player_has_application_games_left(player.steam_id):
                next_game_available_at = self.next_game_available_at(player.steam_id)
                if next_game_available_at is not None:
                    if player.connection_state != "active":
                        return

                    player.kick(
                        f"You used up your {self.application_games} application games. "
                        f"Next game will be available at {next_game_available_at}"
                    )
                    return

            self.warn_lowelo_player(player)

    def elo_for_player(self, player):
        if not self.game:
            return None

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return None

        # noinspection PyProtectedMember
        if "balance" not in Plugin._loaded_plugins and "balancetwo" not in Plugin._loaded_plugins:
            self.logger.warning(
                "Balance plugin not found. Merciful elo limits just work with the elos from the balance plugin"
            )
            return None

        # noinspection PyProtectedMember
        if "balancetwo" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember
            balancetwo_plugin = Plugin._loaded_plugins["balancetwo"]
            balance_api = self.get_cvar("qlx_balanceApi")
            # noinspection PyUnresolvedReferences
            ratings = balancetwo_plugin.ratings["Elo"] if balance_api == "elo" else balancetwo_plugin.ratings["B-Elo"]
            if player.steam_id not in ratings:
                return None

            return ratings.rating_for(player.steam_id, gametype)

        # noinspection PyProtectedMember
        balance_plugin = Plugin._loaded_plugins["balance"]
        # noinspection PyUnresolvedReferences
        ratings = balance_plugin.ratings

        if player.steam_id not in ratings:
            return None

        return ratings[player.steam_id][gametype]["elo"]

    def warn_lowelo_player(self, player):
        remaining_matches = self.remaining_application_games_for_player(player.steam_id)
        next_game_available_at = self.next_game_available_at(player.steam_id)
        if next_game_available_at is None:
            return
        self.blink2(
            player,
            f"^1Skill warning, read console! ^3{remaining_matches} ^1matches left.",
        )
        player.tell(
            f"{player.clean_name}, this is a ^1Skill Warning! ^7Your qlstats.net glicko is below {self.min_elo}. "
            f"You have ^3{remaining_matches} ^7of {self.application_games} "
            f"application matches left, next application game will become available on {next_game_available_at}."
        )
        player.tell(
            "Tip: Practice the Elevate and Accelerate training from the Quake Live menu and some Free For All on other "
            "servers."
        )
        if player.steam_id not in self.announced_player_elos:
            self.msg(
                f"{player.clean_name} is below {self.min_elo}, "
                f"but has ^3{remaining_matches}^7 application matches left."
            )
            self.announced_player_elos.add(player.steam_id)

    @minqlx.thread
    def blink2(self, player, message, count=12, interval=0.12):
        @minqlx.next_frame
        def logic(target, msg):
            target.center_print(f"^3{msg}")

        for msg_number in range(count):
            logic(player, message)
            time.sleep(interval)
            logic(player, "")
            time.sleep(interval)

    def handle_round_start(self, _round_number):
        teams = Plugin.teams()
        for player in teams["red"] + teams["blue"]:
            self.handle_player_at_round_start(player)

    def handle_player_at_round_start(self, player):
        if is_player_in_exception_list(player):
            return

        if player.steam_id in self.tracked_player_sids:
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if elo < self.min_elo:
            self.tracked_player_sids.add(player.steam_id)

            timestamp = datetime.now().timestamp()
            self.db.zremrangebyscore(
                APPLICATION_GAMES_KEY.format(player.steam_id),
                "-INF",
                self.gaming_period_start(),
            )
            self.db.zadd(APPLICATION_GAMES_KEY.format(player.steam_id), timestamp, timestamp)
            return

    def cmd_mercis(self, _player, _msg, channel):
        reply_channel = identify_reply_channel(channel)

        reported_players = []
        for reported_player in self.players():
            elo = self.elo_for_player(reported_player)

            if elo is None or elo > self.min_elo:
                continue

            remaining_matches = self.remaining_application_games_for_player(reported_player.steam_id)

            if remaining_matches >= self.application_games:
                continue

            if self.player_has_been_tracked(reported_player.steam_id):
                reported_players.append(reported_player)

        if len(reported_players) == 0:
            reply_channel.reply("There is currently no player within their application period connected.")
            return

        reply_channel.reply("Players currently within their application period:")
        for merci_player in reported_players:
            elo = self.elo_for_player(merci_player)
            if elo is None:
                continue

            remaining_matches = self.remaining_application_games_for_player(merci_player.steam_id)
            reply_channel.reply(
                f"{merci_player.clean_name} (elo: {elo}): ^3{remaining_matches}^7 application matches left"
            )

    def cmd_merci(self, player, msg, channel):
        reply_channel = identify_reply_channel(channel)

        if len(msg) != 2:
            return minqlx.RET_USAGE

        steam_id = self.find_player_sid(player, msg[1])

        if steam_id is None:
            return minqlx.RET_NONE

        games = self.application_games_of_player(steam_id)

        self.db.zrem(APPLICATION_GAMES_KEY.format(steam_id), games[len(games) - 1])

        granted_player = self.player(steam_id)
        reply_channel.reply(f"{granted_player.clean_name}^7 has been granted another application game")
        return minqlx.RET_NONE

    def remaining_application_games_for_player(self, steam_id):
        remaining_matches = self.application_games - len(self.application_games_of_player(steam_id))
        return remaining_matches

    @minqlx.delay(600)  # 10 minutes
    def remove_thread(self, sid):
        if sid in self.connectthreads:
            del self.connectthreads[sid]

    def find_player_sid(self, player, target):
        # Tell a player which players matched
        def list_alternatives(players, indent=2):
            player.tell(f"A total of ^6{len(players)}^7 players matched for {target}:")
            out = ""
            for p in players:
                out += " " * indent
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])

        try:
            player_id = int(target)

            if player_id > 64:
                return player_id

            target_player = self.player(player_id)
            return target_player.steam_id

        except ValueError:
            pass

        target_players = list(self.find_player(target))

        # If there were absolutely no matches
        if not target_players:
            player.tell(f"Sorry, but no players matched your tokens: {target}.")
            return None

        # If there were more than 1 matches
        if len(target_players) > 1:
            list_alternatives(target_players)
            return None

        # By now there can only be one person left
        return target_players.pop().steam_id


class ConnectThread(threading.Thread):
    def __init__(self, steam_id, balance_api):
        super().__init__(name="merciful")
        self._balance_api = balance_api
        self._steam_id = steam_id
        self._elo = None
        self._is_parsed = threading.Event()

    def is_parsed(self):
        return self._is_parsed.is_set()

    def elo_for(self, gametype):
        if not self._is_parsed.is_set():
            return None
        if not self._elo:
            return None

        return self._elo[gametype]["elo"]

    def run(self):
        url = f"http://qlstats.net/{self._balance_api}/{self._steam_id}"
        logger = minqlx.get_logger("merciful_elo_limit")
        try:
            result = requests_retry_session(retries=10).get(url, timeout=15)
        except RequestException as exception:
            logger.debug(f"request exception: {exception}")
            return

        if result is None or result.status_code != requests.codes.ok:
            logger.debug("MericfulEloLimitError: Invalid response code from qlstats.net.")
            return
        js = result.json()

        if "players" not in js:
            logger.debug("MericfulEloLimitError: Invalid response content from qlstats.net.")
            return

        player_entry = [entry for entry in js["players"] if entry["steamid"] == str(self._steam_id)]

        if len(player_entry) <= 0:
            logger.debug(
                "MericfulEloLimitError: Response from qlstats.net did not include data for the requested player."
            )
            return
        self._elo = player_entry[0]
        self._is_parsed.set()
