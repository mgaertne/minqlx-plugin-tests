from collections import Counter


import minqlx
from minqlx import Plugin, NonexistentPlayerError

COLLECTED_SOULZ_KEY = "minqlx:players:{}:soulz"
REAPERZ_KEY = "minqlx:players:{}:reaperz"
_name_key = "minqlx:players:{}:last_used_name"

SPECIAL_KILLERS = [
    "lava",
    "void",
    "acid",
    "drowning",
    "squished",
    "unknown",
    "grenade",
    "grenade_splash",
    "rocket",
    "rocket_splash",
    "telefrag",
]


# noinspection PyPep8Naming
class frag_stats(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_fragstats_toplimit", "10")

        self.toplimit = self.get_cvar("qlx_fragstats_toplimit", int) or 10

        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("death", self.handle_death)

        self.add_command("mapsoulz", self.cmd_mapsoulz)
        self.add_command("mapreaperz", self.cmd_mapreaperz)
        self.add_command(
            ("soulz", "reaperz", "soulzbalance", "fragbalance"), self.cmd_soulzbalance
        )

        self.frag_log = []

    def handle_player_disconnect(self, player, _reason):
        if self.db is None:
            return
        self.db.set(_name_key.format(player.steam_id), player.name)

    def handle_game_countdown(self):
        self.frag_log = []

    def handle_death(self, victim, killer, data):
        if not self.game or self.game.state != "in_progress":
            return

        if data["MOD"] == "SWITCHTEAM":
            return

        if (
            killer is not None
            and victim is not None
            and victim.steam_id == killer.steam_id
        ):
            return
        if victim is None:
            return

        recorded_killer = self.determine_killer(killer, data["MOD"])

        self.record_frag(recorded_killer, victim.steam_id)
        if data["MOD"] == "TELEFRAG":
            self.record_frag(recorded_killer, "telefrag")
            self.record_frag("telefrag", victim.steam_id)

    def record_frag(self, recorded_killer, victim):
        self.frag_log.append((recorded_killer, victim))

        if self.db is None:
            return

        self.db.zincrby(
            COLLECTED_SOULZ_KEY.format(recorded_killer), value=str(victim), amount=1
        )
        self.db.zincrby(
            REAPERZ_KEY.format(victim), value=str(recorded_killer), amount=1
        )

    # noinspection PyMethodMayBeStatic
    def determine_killer(self, killer, means_of_death):
        if killer is not None:
            return killer.steam_id

        if means_of_death == "HURT":
            return "void"

        if means_of_death == "SLIME":
            return "acid"

        if means_of_death == "WATER":
            return "drowning"

        if means_of_death == "CRUSH":
            return "squished"

        return means_of_death.lower()

    def cmd_mapsoulz(self, player, msg, channel):
        if len(msg) == 1:
            fragger_name, fragger_identifier = self.identify_target(player, player)
        else:
            fragger_name, fragger_identifier = self.identify_target(player, msg[1])
            if fragger_name is None and fragger_identifier is None:
                return

        fragged_statistics = self.mapfrag_statistics_for(fragger_identifier)

        reply_channel = self.identify_reply_channel(channel)
        if len(fragged_statistics) == 0:
            reply_channel.reply(f"{fragger_name}^7 didn't reap any soulz, yet.")
            return

        formatted_stats = ", ".join(
            f"{victim}^7 ({kill_count})"
            for victim, kill_count in fragged_statistics.most_common(self.toplimit)
        )
        reply_channel.reply(
            f"Top {self.toplimit} reaped soulz for {fragger_name}^7: {formatted_stats}"
        )

    def identify_target(self, player, target):
        if isinstance(target, minqlx.Player):
            return target.name, target.steam_id

        if isinstance(target, str) and target in [
            "!lava",
            "!void",
            "!acid",
            "!drowning",
            "!squished",
            "!unknown",
            "!grenade",
            "!grenade_splash",
            "!rocket",
            "!rocket_splash",
            "!telefrag",
        ]:
            return target[1:], target[1:]

        try:
            steam_id = int(target)
            if self.db is not None and self.db.exists(_name_key.format(steam_id)):
                return self.resolve_player_name(steam_id), steam_id
        except ValueError:
            pass

        fragging_player = self.find_target_player_or_list_alternatives(player, target)
        if fragging_player is None:
            return None, None

        return fragging_player.name, fragging_player.steam_id

    def mapfrag_statistics_for(self, fragger_identifier):
        player_fragged_log = [
            killed for killer, killed in self.frag_log if killer == fragger_identifier
        ]

        resolved_fragged_log = self.resolve_player_names(player_fragged_log)
        return Counter(resolved_fragged_log)

    def cmd_mapreaperz(self, player, msg, channel):
        if len(msg) == 1:
            fragged_name, fragged_identifier = self.identify_target(player, player)
        else:
            fragged_name, fragged_identifier = self.identify_target(player, msg[1])

        fragged_statistics = self.mapfraggers_of(fragged_identifier)

        reply_channel = self.identify_reply_channel(channel)
        if len(fragged_statistics) == 0:
            reply_channel.reply(
                f"{fragged_name}^7's soul was not reaped by anyone, yet."
            )
            return

        formatted_stats = ", ".join(
            f"{victim}^7 ({kill_count})"
            for victim, kill_count in fragged_statistics.most_common(self.toplimit)
        )
        reply_channel.reply(
            f"Top {self.toplimit} reaperz of {fragged_name}^7's soul: {formatted_stats}"
        )

    def mapfraggers_of(self, fragged_identifier):
        player_fragged_log = [
            killer for killer, killed in self.frag_log if killed == fragged_identifier
        ]

        resolved_fragged_log = self.resolve_player_names(player_fragged_log)
        return Counter(resolved_fragged_log)

    def resolve_player_names(self, entries):
        if len(entries) == 0:
            return []
        if isinstance(entries[0], tuple):
            return {
                self.resolve_player_name(steam_id): int(value)
                for steam_id, value in entries
            }
        return [self.resolve_player_name(item) for item in entries]

    def resolve_player_name(self, item):
        if not str(item).isdigit():
            return str(item)

        steam_id = int(item)

        try:
            player = self.player(steam_id)
        except NonexistentPlayerError:
            player = None

        if player is not None:
            return player.name

        if self.db is not None and self.db.exists(_name_key.format(steam_id)):
            return self.db.get(_name_key.format(steam_id))

        return str(item)

    def find_target_player_or_list_alternatives(self, player, target):
        # Tell a player which players matched
        def list_alternatives(players, indent=2):
            player.tell(f"A total of ^6{len(players)}^7 players matched for {target}:")
            out = ""
            for p in players:
                out += " " * indent
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])

        try:
            steam_id = int(target)

            target_player = self.player(steam_id)
            if target_player:
                return target_player

        except ValueError:
            pass
        except minqlx.NonexistentPlayerError:
            pass

        target_players = self.find_player(str(target))

        # If there were absolutely no matches
        if not target_players:
            player.tell(f"Sorry, but no players matched your tokens: {target}.")
            return None

        # If there were more than 1 matches
        if len(target_players) > 1:
            list_alternatives(target_players)
            return None

        # By now there can only be one person left
        return target_players.pop()

    def overall_frag_statistics_for(self, fragger_identifier):
        if self.db is None:
            return Counter([])
        player_fragged_log = self.db.zrevrangebyscore(
            COLLECTED_SOULZ_KEY.format(fragger_identifier),
            "+INF",
            "-INF",
            withscores=True,
        )

        resolved_fragged_log = self.resolve_player_names(player_fragged_log)
        return Counter(resolved_fragged_log)

    def overall_fraggers_of(self, fragger_identifier):
        if self.db is None:
            return Counter([])
        player_fragger_log = self.db.zrevrangebyscore(
            REAPERZ_KEY.format(fragger_identifier),
            "+INF",
            "-INF",
            withscores=True,
        )

        resolved_fragger_log = self.resolve_player_names(player_fragger_log)
        return Counter(resolved_fragger_log)

    # noinspection PyMethodMayBeStatic
    def identify_reply_channel(self, channel):
        if channel in [
            minqlx.RED_TEAM_CHAT_CHANNEL,
            minqlx.BLUE_TEAM_CHAT_CHANNEL,
            minqlx.SPECTATOR_CHAT_CHANNEL,
            minqlx.FREE_CHAT_CHANNEL,
        ]:
            return minqlx.CHAT_CHANNEL

        return channel

    def cmd_soulzbalance(self, player, msg, channel):
        if len(msg) == 1:
            self.report_top_soulzbalance(player, channel)
            return

        self.report_single_soulzbalance(player, msg[1], channel)

    @minqlx.thread
    def report_top_soulzbalance(self, player, channel):
        reply_channel = self.identify_reply_channel(channel)

        fragger_name, fragger_identifier = self.identify_target(player, player)
        if fragger_identifier is None:
            return

        fragged_statistics = self.overall_frag_statistics_for(fragger_identifier)
        reaper_statistics = self.overall_fraggers_of(fragger_identifier)

        soulz_statistics = fragged_statistics.copy()
        soulz_statistics.subtract(reaper_statistics)
        reaped_statistics = reaper_statistics.copy()
        reaped_statistics.subtract(fragged_statistics)

        for reaper in SPECIAL_KILLERS:
            del soulz_statistics[reaper]
            del reaped_statistics[reaper]

        if len(soulz_statistics) == 0:
            reply_channel.reply(
                f"{fragger_name}^7 didn't reap any soulz, and {fragger_name}^7's soul wasn't reaped, yet."
            )
            return

        formatted_souls = ", ".join(
            f"{self.resolve_player_name(victim)}^7({self.color_coded_balance_diff(soulz_statistics[victim])})"
            f"({fragged_statistics[victim]}/{reaper_statistics[victim]})"
            for victim, kill_count in soulz_statistics.most_common(self.toplimit // 2)
        )
        reply_channel.reply(
            f"Best {self.toplimit // 2} soul balance for {fragger_name}^7: {formatted_souls}"
        )

        formatted_reapers = ", ".join(
            f"{self.resolve_player_name(victim)}^7({self.color_coded_balance_diff(soulz_statistics[victim])})"
            f"({fragged_statistics[victim]}/{reaper_statistics[victim]})"
            for victim, kill_count in reaped_statistics.most_common(self.toplimit // 2)
        )
        reply_channel.reply(
            f"Worst {self.toplimit // 2} soul balance for {fragger_name}^7: {formatted_reapers}"
        )

    @minqlx.thread
    def report_single_soulzbalance(self, player, opponent, channel):
        reply_channel = self.identify_reply_channel(channel)

        fragger_name, fragger_identifier = self.identify_target(player, player)

        opponent_name, opponent_identifier = self.identify_target(player, opponent)
        if opponent_name is None and opponent_identifier is None:
            return

        soulz = self.db.zscore(
            COLLECTED_SOULZ_KEY.format(fragger_identifier), opponent_identifier
        )
        soulz = int(soulz) if soulz is not None else 0
        reapz = self.db.zscore(
            REAPERZ_KEY.format(fragger_identifier), opponent_identifier
        )
        reapz = int(reapz) if reapz is not None else 0

        if soulz > reapz:
            reply_message = (
                f"{fragger_name}^7 leads by ^2{soulz - reapz}^7 soulz vs. "
                f"{opponent_name}^7 ({soulz}/{reapz})"
            )
        elif reapz > soulz:
            reply_message = (
                f"{opponent_name}^7 leads by ^1{reapz - soulz}^7 soulz vs. "
                f"{fragger_name}^7 ({reapz}/{soulz})"
            )
        else:
            reply_message = (
                f"{fragger_name}^7 is even with {opponent_name}^7 ({soulz}/{reapz})"
            )

        reply_channel.reply(reply_message)

    # noinspection PyMethodMayBeStatic
    def color_coded_balance_diff(self, balance_diff):
        if balance_diff < 0:
            return f"^1{balance_diff:+}^7"

        return f"^2{balance_diff:+}^7"
