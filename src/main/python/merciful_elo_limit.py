import minqlx
from minqlx import Plugin, RET_NONE, CHAT_CHANNEL

import time

FREE_GAMES_KEY = "minqlx:players:{}:minelo:freegames"
ABOVE_GAMES_KEY = "minqlx:players:{}:minelo:abovegames"

SUPPORTED_GAMETYPES = ("ca", "ctf", "dom", "ft", "tdm", "duel", "ffa")


class merciful_elo_limit(Plugin):
    """
    Uses:
    * qlx_merciful_minelo (default: 800) The minimum elo for free games. Players below this limit are tracked.
    * qlx_mercifulelo_freegames (default: 10) The amount of free games a player below the minimum elo will be able to
    play
    * qlx_mercifulelo_abovegames (default: 10) The amount of games a player needs to complete in a row with at least
    minimum elo before stopping to track her.
    * qlx_mercifulelo_daysbanned (default: 30) The number of days a low elo player gets banned after using up his
    free games
    """
    def __init__(self):
        super().__init__()
        self.set_cvar_once("qlx_mercifulelo_minelo", "800")
        self.set_cvar_once("qlx_mercifulelo_freegames", "10")
        self.set_cvar_once("qlx_mercifulelo_abovegames", "10")
        self.set_cvar_once("qlx_mercifulelo_daysbanned", "30")

        self.min_elo = self.get_cvar("qlx_mercifulelo_minelo", int)
        self.free_games = self.get_cvar("qlx_mercifulelo_freegames", int)
        self.above_games = self.get_cvar("qlx_mercifulelo_abovegames", int)
        self.banned_days = self.get_cvar("qlx_mercifulelo_daysbanned", int)

        self.tracked_player_sids = []
        self.announced_player_elos = []

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)

    def handle_map_change(self, mapname, factory):
        self.tracked_player_sids = []
        self.announced_player_elos = []
        self.fetch_elos_of_players(Plugin.players())

    def handle_player_connect(self, player):
        self.fetch_elos_of_players([player])

    def fetch_elos_of_players(self, players):
        if not self.game:
            return

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return

        if 'balance' not in Plugin._loaded_plugins:
            self.logger.warning("Balance plugin not found. Merciful elo limits just work with the elos "
                                "from the balance plugin")
            return

        balance_plugin = Plugin._loaded_plugins['balance']

        player_ratings = dict([(p.steam_id, gametype) for p in players])
        balance_plugin.add_request(player_ratings, self.callback_ratings, CHAT_CHANNEL)

    def handle_round_countdown(self, round_number):
        if not self.game:
            return RET_NONE

        teams = Plugin.teams()
        self.fetch_elos_of_players(teams["red"] + teams["blue"])

    def callback_ratings(self, players, channel):
        if not self.game:
            return

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            self.handle_player_after_fetching_ratings(player)

    def handle_player_after_fetching_ratings(self, player):
        @minqlx.next_frame
        def ban_player(player, duration, msg):
            minqlx.COMMANDS.handle_input(DummyOwner(self.logger),
                                         "!ban {} {} {}".format(player.steam_id, duration, msg),
                                         DummyChannel(self.logger))

        if self.is_player_in_exception_list(player):
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if elo < self.min_elo:
            free_games_played = self.get_value_from_db_or_zero(FREE_GAMES_KEY.format(player.steam_id))

            if free_games_played > self.free_games:
                ban_player(player, "30 days",
                           "Automatically banned after using up {} free games".format(self.free_games))
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
                self.db.delete(FREE_GAMES_KEY.format(player.steam_id))
                return

            self.warn_lowelo_player(player)

    def is_player_in_exception_list(self, player):
        if 'mybalance' not in Plugin._loaded_plugins:
            return False

        mybalance_plugin = Plugin._loaded_plugins['mybalance']
        return player.steam_id in mybalance_plugin.exceptions

    def get_value_from_db_or_zero(self, key):
        value = self.db.get(key)
        if value is None:
            return 0
        return int(value)

    def elo_for_player(self, player):
        if not self.game:
            return None

        if 'balance' not in Plugin._loaded_plugins:
            self.logger.warning("Balance plugin not found. Merciful elo limits just work with the elos "
                                "from the balance plugin")
            return None
        balance_plugin = Plugin._loaded_plugins['balance']
        ratings = balance_plugin.ratings

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return None

        return ratings[player.steam_id][gametype]["elo"]

    def warn_lowelo_player(self, player):
        matches_played = self.get_value_from_db_or_zero(FREE_GAMES_KEY.format(player.steam_id))
        remaining_matches = self.free_games - matches_played
        self.blink2(player, "^1Skill warning, read console! ^3{} ^1matches left.".format(remaining_matches))
        player.tell(
            "{}, this is a ^1Skill Warning! ^7Your qlstats.net glicko is below {}. You have ^3{} ^7of {} free matches "
            "left, before server will automatically ban you for {} days"
            .format(player.clean_name, self.min_elo, remaining_matches, self.free_games, self.banned_days))
        player.tell(
            "You will get {} new free matches after the {} days ban. Please improve your skill! "
            "Tip: Practice the Elevate and Accelerate training from the Quake Live menu and some Free For All on other "
            "servers."
            .format(self.free_games, self.banned_days))
        if player.steam_id not in self.announced_player_elos:
            self.msg("Player {} is below {}, but has {} free games left."
                     .format(player.clean_name, self.min_elo, remaining_matches))
            self.announced_player_elos.append(player.steam_id)

    @minqlx.thread
    def blink2(self, player, message, count=12, interval=.12):
        @minqlx.next_frame
        def logic(target, msg):
            target.center_print("^3{}".format(msg))

        for msg_number in range(count):
            logic(player, message)
            time.sleep(interval)
            logic(player, "")
            time.sleep(interval)

    def handle_round_start(self, round_number):
        teams = Plugin.teams()
        for player in teams["red"] + teams["blue"]:
            self.handle_player_at_round_start(player)

    def handle_player_at_round_start(self, player):
        if self.is_player_in_exception_list(player):
            return

        if player.steam_id in self.tracked_player_sids:
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if elo < self.min_elo:
            self.db.incr(FREE_GAMES_KEY.format(player.steam_id))
            self.tracked_player_sids.append(player.steam_id)

            if self.db.exists(ABOVE_GAMES_KEY.format(player.steam_id)):
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
            return

        if self.db.exists(FREE_GAMES_KEY.format(player.steam_id)):
            self.tracked_player_sids.append(player.steam_id)
            self.db.incr(ABOVE_GAMES_KEY.format(player.steam_id))
            above_games = self.get_value_from_db_or_zero(ABOVE_GAMES_KEY.format(player.steam_id))
            if above_games > self.above_games:
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
                self.db.delete(FREE_GAMES_KEY.format(player.steam_id))


class DummyChannel(minqlx.AbstractChannel):
    def __init__(self, logger):
        super().__init__("merciful_elo_limit")
        self.logger = logger

    def reply(self, msg):
        self.logger.info(msg)


class DummyOwner(minqlx.AbstractDummyPlayer):
    def __init__(self, logger):
        super().__init__(name="Owner")
        self.logger = logger

    @property
    def steam_id(self):
        return minqlx.owner()

    @property
    def channel(self):
        return DummyChannel(self.logger)

    def tell(self, msg):
        self.logger.info(msg)
