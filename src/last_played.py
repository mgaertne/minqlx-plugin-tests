from datetime import datetime, timezone, timedelta

import humanize

from minqlx import Plugin, thread
from minqlx.database import Redis

TIMESTAMP_FORMAT = "%Y%m%d%H%M%S%z"


# noinspection PyPep8Naming
class last_played(Plugin):
    database = Redis

    def __init__(self):
        super().__init__()

        self.long_map_names_lookup = {}
        self.add_hook("stats", self.handle_stats)
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

    def cmd_last_played(self, player, msg, channel):
        if self.game is None:
            return

        mapname = self.game.map.lower() if len(msg) == 1 else " ".join(msg[1:])
        if len(self.long_map_names_lookup) == 0 and self.db.exists(
            "minqlx:maps:longnames"
        ):
            self.long_map_names_lookup = self.db.hgetall("minqlx:maps:longnames")

        if (
            mapname in self.long_map_names_lookup
            and mapname.lower() != self.long_map_names_lookup[mapname].lower()
        ):
            mapname_str = f"^3{self.long_map_names_lookup[mapname]}^7 (^3{mapname}^7)"
        else:
            mapname_str = f"^3{mapname}^7"

        if not self.db.exists(f"minqlx:maps:{mapname}:last_played"):
            channel.reply(
                f"I don't know when map {mapname_str} was played the last time."
            )
            return

        last_played_db_entry = self.db.get(f"minqlx:maps:{mapname}:last_played")
        last_played_timestamp = datetime.strptime(
            last_played_db_entry, TIMESTAMP_FORMAT
        )
        last_played_str = humanize.naturaldelta(
            datetime.now(timezone.utc) - last_played_timestamp
        )

        player_last_played = None
        if self.db.exists(f"minqlx:players:{player.steam_id}:last_played"):
            player_last_played = self.db.hget(
                f"minqlx:players:{player.steam_id}:last_played", mapname
            )

        if player_last_played is None:
            channel.reply(
                f"Map {mapname_str} was last played {last_played_str} ago here."
            )
            return

        player_last_played_timestamp = datetime.strptime(
            player_last_played, TIMESTAMP_FORMAT
        )
        if last_played_timestamp - player_last_played_timestamp < timedelta(seconds=10):
            channel.reply(
                f"Map {mapname_str} was last played {last_played_str} ago here. So did you."
            )
            return

        player_last_played_str = humanize.naturaldelta(
            datetime.now(timezone.utc) - player_last_played_timestamp
        )
        channel.reply(
            f"Map {mapname_str} was last played {last_played_str} ago here. "
            f"You played on it {player_last_played_str} ago."
        )
