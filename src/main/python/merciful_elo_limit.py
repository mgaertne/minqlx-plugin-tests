import time

import minqlx
from minqlx import Plugin, CHAT_CHANNEL

APPLICATION_GAMES_KEY = "minqlx:players:{}:minelo:freegames"
ABOVE_GAMES_KEY = "minqlx:players:{}:minelo:abovegames"

SUPPORTED_GAMETYPES = ("ca", "ctf", "dom", "ft", "tdm", "duel", "ffa")


# noinspection PyPep8Naming
class merciful_elo_limit(Plugin):
    """
    Uses:
    * qlx_merciful_minelo (default: 800) The minimum elo for application games. Players below this limit are tracked.
    * qlx_mercifulelo_applicationgames (default: 10) The amount of application games a player below the minimum elo
    will be able to play
    * qlx_mercifulelo_abovegames (default: 10) The amount of games a player needs to complete in a row with at least
    minimum elo before stopping to track her.
    * qlx_mercifulelo_daysbanned (default: 30) The number of days a low elo player gets banned after using up his
    application games
    """
    def __init__(self):
        super().__init__()
        self.set_cvar_once("qlx_mercifulelo_minelo", "800")
        self.set_cvar_once("qlx_mercifulelo_applicationgames", "10")
        self.set_cvar_once("qlx_mercifulelo_abovegames", "10")
        self.set_cvar_once("qlx_mercifulelo_daysbanned", "30")

        self.min_elo = self.get_cvar("qlx_mercifulelo_minelo", int)
        self.application_games = self.get_cvar("qlx_mercifulelo_applicationgames", int) or 10
        self.above_games = self.get_cvar("qlx_mercifulelo_abovegames", int)
        self.banned_days = self.get_cvar("qlx_mercifulelo_daysbanned", int)

        self.tracked_player_sids = []
        self.announced_player_elos = []

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)

        self.add_command("mercis", self.cmd_mercis, permission=1)

    def handle_map_change(self, _mapname, _factory):
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

        player_ratings = {p.steam_id: gametype for p in players}
        # noinspection PyUnresolvedReferences
        balance_plugin.add_request(player_ratings, self.callback_ratings, CHAT_CHANNEL)  # type: ignore

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
        @minqlx.next_frame
        def ban_player(_player, duration, msg):
            minqlx.COMMANDS.handle_input(DummyOwner(self.logger),
                                         f"!ban {_player.steam_id} {duration} {msg}",
                                         DummyChannel(self.logger))

        if not self.db:
            return

        if self.is_player_in_exception_list(player):
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if elo < self.min_elo:
            application_games_played = self.get_value_from_db_or_zero(APPLICATION_GAMES_KEY.format(player.steam_id))

            if application_games_played > self.application_games:
                ban_player(player, f"{self.banned_days} days",
                           f"Automatically banned after using up {self.application_games} application matches")
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
                self.db.delete(APPLICATION_GAMES_KEY.format(player.steam_id))
                return

            self.warn_lowelo_player(player)

    # noinspection PyMethodMayBeStatic
    def is_player_in_exception_list(self, player):
        if 'mybalance' not in Plugin._loaded_plugins:
            return False

        mybalance_plugin = Plugin._loaded_plugins['mybalance']
        # noinspection PyUnresolvedReferences
        return player.steam_id in mybalance_plugin.exceptions  # type: ignore

    def get_value_from_db_or_zero(self, key):
        if not self.db:
            return 0

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
        # noinspection PyUnresolvedReferences
        ratings = balance_plugin.ratings  # type: ignore

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return None

        return ratings[player.steam_id][gametype]["elo"]

    def warn_lowelo_player(self, player):
        matches_played = self.get_value_from_db_or_zero(APPLICATION_GAMES_KEY.format(player.steam_id))
        remaining_matches = self.application_games - matches_played
        self.blink2(player, f"^1Skill warning, read console! ^3{remaining_matches} ^1matches left.")
        player.tell(
            f"{player.clean_name}, this is a ^1Skill Warning! ^7Your qlstats.net glicko is below {self.min_elo}. "
            f"You have ^3{remaining_matches} ^7of {self.application_games} application matches left, before server "
            f"will automatically ban you for {self.banned_days} days")
        player.tell(
            f"You will get {self.application_games} new application matches after the {self.banned_days} days ban. "
            f"Please improve your skill! Tip: Practice the Elevate and Accelerate training from the Quake Live menu "
            f"and some Free For All on other servers.")
        if player.steam_id not in self.announced_player_elos:
            self.msg(f"{player.clean_name} is below {self.min_elo}, "
                     f"but has ^3{remaining_matches}^7 application matches left.")
            self.announced_player_elos.append(player.steam_id)

    @minqlx.thread
    def blink2(self, player, message, count=12, interval=.12):
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
        if not self.db:
            return

        if self.is_player_in_exception_list(player):
            return

        if player.steam_id in self.tracked_player_sids:
            return

        elo = self.elo_for_player(player)
        if elo is None:
            return

        if elo < self.min_elo:
            self.db.incr(APPLICATION_GAMES_KEY.format(player.steam_id))
            self.tracked_player_sids.append(player.steam_id)

            if self.db.exists(ABOVE_GAMES_KEY.format(player.steam_id)):
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
            return

        if self.db.exists(APPLICATION_GAMES_KEY.format(player.steam_id)):
            self.tracked_player_sids.append(player.steam_id)
            self.db.incr(ABOVE_GAMES_KEY.format(player.steam_id))
            above_games = self.get_value_from_db_or_zero(ABOVE_GAMES_KEY.format(player.steam_id))
            if above_games > self.above_games:
                self.db.delete(ABOVE_GAMES_KEY.format(player.steam_id))
                self.db.delete(APPLICATION_GAMES_KEY.format(player.steam_id))

    def cmd_mercis(self, _player, _msg, channel):
        reply_channel = self.identify_reply_channel(channel)
        players = self.players()

        if not self.db:
            reply_channel.reply("Something went wrong. Consult an admin!")
            return

        reported_players = []
        for player in players:
            if self.db.get(APPLICATION_GAMES_KEY.format(player.steam_id)):
                reported_players.append(player)

        if len(reported_players) == 0:
            return

        reply_channel.reply("Players currently within their application period:")
        for player in reported_players:
            elo = self.elo_for_player(player)
            remaining_matches = self.application_games - int(self.db.get(APPLICATION_GAMES_KEY.format(player.steam_id)))
            if elo > self.min_elo:
                above_games = self.db.get(ABOVE_GAMES_KEY.format(player.steam_id))
                reply_channel.reply(
                    f"{player.clean_name} (elo: {elo}): "
                    f"^3{remaining_matches}^7 application matches left, "
                    f"^2{above_games}^7 matches above {self.min_elo}")
            else:
                reply_channel.reply(f"{player.clean_name} (elo: {elo}): "
                                    f"^3{remaining_matches}^7 application matches left")

    # noinspection PyMethodMayBeStatic
    def identify_reply_channel(self, channel):
        if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                       minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
            return minqlx.CHAT_CHANNEL

        return channel


class DummyChannel(minqlx.AbstractChannel):
    def __init__(self, logger):
        super().__init__("merciful_elo_limit")
        self.logger = logger

    def reply(self, msg, **kwargs):
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

    def tell(self, msg, **_kwargs):
        self.logger.info(msg)
