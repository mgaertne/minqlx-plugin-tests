from datetime import datetime, timezone, timedelta

import humanize

from minqlx import Plugin, thread, parse_variables
from minqlx.database import Redis

TIMESTAMP_FORMAT = "%Y%m%d%H%M%S%z"


# noinspection PyPep8Naming
class last_played(Plugin):
    database = Redis

    def __init__(self):
        super().__init__()

        self.long_map_names_lookup = {}
        self.add_hook("stats", self.handle_stats)
        self.add_hook("game_end", self.handle_game_end)

        self.add_command("lastplayed", self.cmd_last_played, usage="[mapname]")

    def handle_stats(self, data):
        if data["TYPE"] == "MATCH_REPORT":
            self.log_played_map(data["DATA"])

        if data["TYPE"] == "PLAYER_STATS":
            self.log_player_map(data["DATA"])

    @thread
    def log_played_map(self, data):
        if data["ABORTED"]:
            return

        now = datetime.now(timezone.utc)
        timestamp = now.strftime(TIMESTAMP_FORMAT)
        mapname = data["MAP"].lower()
        self.db.set(f"minqlx:maps:{mapname}:last_played", timestamp)

    @thread
    def log_player_map(self, data):
        if data["ABORTED"]:
            return

        if data["WARMUP"]:
            return

        if self.game is None:
            return

        now = datetime.now(timezone.utc)
        timestamp = now.strftime(TIMESTAMP_FORMAT)
        mapname = self.game.map.lower()
        steam_id = data["STEAM_ID"]
        self.db.hset(f"minqlx:players:{steam_id}:last_played", mapname, timestamp)

    def handle_game_end(self, _data):
        if not self.game:
            return

        if self.game.roundlimit not in [self.game.red_score, self.game.blue_score]:
            return

        nextmaps = self.get_nextmaps()
        long_mapnames = (self.long_mapname_for(mapname) for mapname in nextmaps)
        now = datetime.now(timezone.utc)
        last_played_timestamps = (self.get_map_last_played_timestamp(mapname) for mapname in nextmaps)

        display_strs = []
        for index, (mapname, long_mapname, last_played_timestamp) in enumerate(
            zip(nextmaps, long_mapnames, last_played_timestamps), start=1
        ):
            if long_mapname is not None and last_played_timestamp is not None:
                display_strs.append(
                    f"^3{index}: ^5{long_mapname} ^7(^5{mapname}^7, "
                    f"last played {humanize.naturaldelta(now - last_played_timestamp)} ago)"
                )
            elif long_mapname is not None and last_played_timestamp is None:
                display_strs.append(f"^3{index}: ^5{long_mapname} ^7(^5{mapname}^7)")
            elif long_mapname is None and last_played_timestamp is not None:
                display_strs.append(
                    f"^3{index}: ^5{mapname} ^7(last played {humanize.naturaldelta(now - last_played_timestamp)} ago)"
                )
            else:
                display_strs.append(f"^3{index}: ^5{mapname}")

        self.msg("^1▬▬ ^5CONSOLE VOTE (type vote ^31-3) ^1▬▬")
        self.msg(" ".join(display_strs))

    def get_nextmaps(self):
        nextmaps = parse_variables(self.get_cvar("nextmaps"))
        return nextmaps["map_0"], nextmaps["map_1"], nextmaps["map_2"]

    def long_mapname_for(self, mapname):
        if len(self.long_map_names_lookup) == 0 and self.db.exists("minqlx:maps:longnames"):
            self.long_map_names_lookup = self.db.hgetall("minqlx:maps:longnames")

        if mapname not in self.long_map_names_lookup or mapname.lower() == self.long_map_names_lookup[mapname].lower():
            return None

        return self.long_map_names_lookup[mapname]

    def get_map_last_played_timestamp(self, mapname):
        if not self.db.exists(f"minqlx:maps:{mapname}:last_played"):
            return None

        last_played_db_entry = self.db.get(f"minqlx:maps:{mapname}:last_played")
        return datetime.strptime(last_played_db_entry, TIMESTAMP_FORMAT)

    def cmd_last_played(self, player, msg, channel):
        if self.game is None:
            return

        mapname = self.game.map.lower() if len(msg) == 1 else " ".join(msg[1:])
        long_mapname = self.long_mapname_for(mapname)

        mapname_str = f"^3{long_mapname}^7 (^3{mapname}^7)" if long_mapname is not None else f"^3{mapname}^7"

        last_played_timestamp = self.get_map_last_played_timestamp(mapname)
        if last_played_timestamp is None:
            channel.reply(f"I don't know when map {mapname_str} was played the last time.")
            return

        last_played_str = humanize.naturaldelta(datetime.now(timezone.utc) - last_played_timestamp)

        player_last_played = None
        if self.db.exists(f"minqlx:players:{player.steam_id}:last_played"):
            player_last_played = self.db.hget(f"minqlx:players:{player.steam_id}:last_played", mapname)

        if player_last_played is None:
            channel.reply(f"Map {mapname_str} was last played {last_played_str} ago here.")
            return

        player_last_played_timestamp = datetime.strptime(player_last_played, TIMESTAMP_FORMAT)
        if last_played_timestamp - player_last_played_timestamp < timedelta(seconds=10):
            channel.reply(f"Map {mapname_str} was last played {last_played_str} ago here. So did you.")
            return

        player_last_played_str = humanize.naturaldelta(datetime.now(timezone.utc) - player_last_played_timestamp)
        channel.reply(
            f"Map {mapname_str} was last played {last_played_str} ago here. "
            f"You played on it {player_last_played_str} ago."
        )
