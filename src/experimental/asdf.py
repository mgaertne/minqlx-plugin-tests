import math

from typing import Union

import minqlx  # type: ignore
from minqlx import AbstractChannel, Player, Plugin

WEAPON_STATS_KEY = "minqlx:{}:weaponstats"
_name_key = "minqlx:players:{}:last_used_name"

SteamId = int


def identify_reply_channel(channel: AbstractChannel) -> AbstractChannel:
    if channel in [
        minqlx.RED_TEAM_CHAT_CHANNEL,
        minqlx.BLUE_TEAM_CHAT_CHANNEL,
        minqlx.SPECTATOR_CHAT_CHANNEL,
        minqlx.FREE_CHAT_CHANNEL,
    ]:
        return minqlx.CHAT_CHANNEL

    return channel


# noinspection PyPep8Naming
class asdf(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_asdf_minammo_rate", "0.25")

        self.add_hook("stats", self.handle_stats)

        self.add_hook("player_spawn", self.handle_player_spawn)

        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)

        self.add_command("weaponstats", self.cmd_weaponstats, usage="[player or id]")

        self.stats_snapshot = {}
        self.red_overall_damage: int = 0
        self.blue_overall_damage: int = 0

        self.min_ammo_rate: float = (
            self.get_cvar("qlx_asdf_minammo_rate", float) or 0.25
        )

    def handle_player_spawn(self, player: Player):
        if not self.game or self.game.state != "in_progress":
            return

        if self.game.type_short not in ["ca", "midair"]:
            return

        if not player.is_alive:
            return

        if abs(self.game.red_score - self.game.blue_score) < 3:
            return

        teams = self.teams()
        if len(teams["red"]) == 1 or len(teams["blue"]) == 1:
            return

        leading_team = "red"
        if self.game.blue_score > self.game.red_score:
            leading_team = "blue"

        if player.team != leading_team:
            return

        self.adjust_ammo_for_player(player)

    @minqlx.thread
    def adjust_ammo_for_player(self, player: Player):
        weapon_stats = self.weapon_stats_for(player.steam_id)

        total_team_damage = (
            self.red_overall_damage
            if player.team == "red"
            else self.blue_overall_damage
        )
        self.logger.debug(f"total_team_damage: {total_team_damage}")

        if total_team_damage == 0.0:
            total_team_damage = player.stats.damage_dealt
        damage_factor = 1.0 - float(player.stats.damage_dealt) / float(
            total_team_damage
        )

        if damage_factor > 0.9:
            return

        filtered_weapon_stats = [
            weapon_entry
            for weapon_entry in weapon_stats.values()
            if weapon_entry.accuracy() > 25.0
        ]
        sorted_weapon_stats = sorted(
            filtered_weapon_stats, key=lambda entry: entry.time
        )
        ammo_settings = {}
        ammo_info = ""

        current_ammo = player.state.ammo

        for weapon_entry in sorted_weapon_stats:
            if getattr(current_ammo, weapon_entry.weapon.ammo_type()) == -1:
                continue

            starting_ammo = getattr(current_ammo, weapon_entry.weapon.ammo_type())
            accuracy_factor = (100.0 - weapon_entry.accuracy()) / 100.0
            adjusted_starting_ammo = math.ceil(
                starting_ammo * accuracy_factor * damage_factor
            )
            adjusted_starting_ammo = max(
                starting_ammo * self.min_ammo_rate, adjusted_starting_ammo
            )
            ammo_settings[weapon_entry.weapon.ammo_type()] = adjusted_starting_ammo
            formatted_ammo_type = weapon_entry.weapon.ammo_type().upper()
            ammo_info = (
                ammo_info
                + f" ^1{formatted_ammo_type}^7: ^4{starting_ammo}^3->^4{adjusted_starting_ammo}^7"
            )

        if len(ammo_settings) == 0:
            return

        self.logger.debug(f"Adjusted ammo settings for {player.name}: {ammo_settings}")

        player.ammo(**ammo_settings)
        player.tell(
            f"{player.name}, your team is dominating right now. Some of your ammo was reduced:{ammo_info}"
        )

    def handle_stats(self, stats: dict):
        if stats["TYPE"] != "PLAYER_STATS":
            return

        if stats["DATA"]["WARMUP"]:
            return

        if stats["DATA"]["ABORTED"]:
            return

        if "WEAPONS" not in stats["DATA"]:
            return

        self.store_weapon_stats(stats)

    @minqlx.thread
    def store_weapon_stats(self, stats: dict):
        if not self.db:
            return

        steam_id = stats["DATA"]["STEAM_ID"]
        for weapon in stats["DATA"]["WEAPONS"]:
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "deaths",
                stats["DATA"]["WEAPONS"][weapon]["D"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "damage_dealt",
                stats["DATA"]["WEAPONS"][weapon]["DG"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "damage_received",
                stats["DATA"]["WEAPONS"][weapon]["DR"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "hits",
                stats["DATA"]["WEAPONS"][weapon]["H"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "kills",
                stats["DATA"]["WEAPONS"][weapon]["K"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "pickups",
                stats["DATA"]["WEAPONS"][weapon]["P"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "shots",
                stats["DATA"]["WEAPONS"][weapon]["S"],
            )
            self.db.hincrby(
                WEAPON_STATS_KEY.format(steam_id) + f":{weapon}",
                "time",
                stats["DATA"]["WEAPONS"][weapon]["T"],
            )

    def handle_game_countdown(self):
        self.stats_snapshot = {}
        self.red_overall_damage = 0
        self.blue_overall_damage = 0

    def handle_round_start(self, _round_number: int):
        teams = self.teams()
        self.stats_snapshot = {
            player.steam_id: player.stats.damage_dealt
            for player in teams["red"] + teams["blue"]
        }

    def handle_round_end(self, _data: dict):
        if self.game is None:
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        self.calculate_team_round_damages()

    def calculate_team_round_damages(self):
        deltas = self.calculate_damage_deltas()

        teams = self.teams()

        red_diff = sum(
            deltas[player.steam_id]
            for player in teams["red"]
            if player.steam_id in deltas
        )
        self.red_overall_damage += red_diff

        blue_diff = sum(
            deltas[player.steam_id]
            for player in teams["blue"]
            if player.steam_id in deltas
        )
        self.blue_overall_damage += blue_diff

        self.logger.debug(f"red_diff: {red_diff} blue_diff: {blue_diff}")

    def calculate_damage_deltas(self):
        returned = {}

        for steam_id in self.stats_snapshot:
            minqlx_player = self.player(steam_id)

            if minqlx_player is None:
                continue

            returned[steam_id] = (
                minqlx_player.stats.damage_dealt - self.stats_snapshot[steam_id]
            )

        return returned

    def cmd_weaponstats(self, player: Player, msg: str, channel: AbstractChannel):
        if len(msg) == 1:
            player_name, player_identifier = self.identify_target(player, player)
        else:
            player_name, player_identifier = self.identify_target(player, msg[1])
            if player_name is None and player_identifier is None:
                return

        reply_channel = identify_reply_channel(channel)

        weapon_stats = self.weapon_stats_for(player_identifier)
        stats_strings = []
        for weapon in [
            "MACHINEGUN",
            "HMG",
            "SHOTGUN",
            "GRENADE",
            "ROCKET",
            "LIGHTNING",
            "RAILGUN",
            "PLASMA",
            "BFG",
            "NAILGUN",
            "PROXMINE",
            "CHAINGUN",
        ]:
            if weapon not in weapon_stats:
                continue
            accuracy = weapon_stats[weapon].accuracy()
            if accuracy != 0:
                stats_strings.append(
                    f"^1{weapon_stats[weapon].name}^7: ^4{accuracy:.0f}^7"
                )

        if len(stats_strings) == 0:
            return
        stats_string = ", ".join(stats_strings)
        reply_channel.reply(
            f"Weapon statistics for player {player_name}^7: {stats_string}"
        )

    def weapon_stats_for(self, steam_id: SteamId):
        if not self.db:
            return {}

        returned = {}
        for key in self.db.keys(WEAPON_STATS_KEY.format(steam_id) + ":*"):
            weapon_stats = self.db.hgetall(key)
            weapon = key.split(":")[-1]
            if int(weapon_stats["shots"]) != 0 and int(weapon_stats["hits"]) != 0:
                returned[weapon] = WeaponStatsEntry(
                    Weapon(weapon),
                    int(weapon_stats["kills"]),
                    int(weapon_stats["deaths"]),
                    int(weapon_stats["damage_dealt"]),
                    int(weapon_stats["damage_received"]),
                    int(weapon_stats["shots"]),
                    int(weapon_stats["hits"]),
                    int(weapon_stats["pickups"]),
                    int(weapon_stats["time"]),
                )

        return returned

    def identify_target(self, player: Player, target: Union[SteamId, str, Player]):
        if isinstance(target, Player):
            return target.name, target.steam_id

        try:
            steam_id = int(target)
            if self.db and self.db.exists(_name_key.format(steam_id)):
                return self.resolve_player_name(steam_id), steam_id
        except ValueError:
            pass

        target_player = self.find_target_player_or_list_alternatives(player, target)
        if target_player is None:
            return None, None

        return target_player.name, target_player.steam_id

    def resolve_player_name(self, item: Union[SteamId, str]):
        if not isinstance(item, int) and not item.isdigit():
            return item

        steam_id = int(item)

        player = self.player(steam_id)

        if player is not None:
            return player.name

        if self.db and self.db.exists(_name_key.format(steam_id)):
            return self.db.get(_name_key.format(steam_id))

        return item

    def find_target_player_or_list_alternatives(
        self, player: Player, target: Union[int, str]
    ):
        # Tell a player which players matched
        def list_alternatives(players: list[Player], indent: int = 2):
            amount_alternatives = len(players)
            player.tell(
                f"A total of ^6{amount_alternatives}^7 players matched for {target}:"
            )
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


class Weapon:
    def __init__(self, name):
        self.name = name

    def weapon_name(self):
        return self.ammo_type().upper()

    def ammo_type(self):
        weapon_name = self.name.upper()
        if weapon_name == "MACHINEGUN":
            return "mg"
        if weapon_name == "SHOTGUN":
            return "sg"
        if weapon_name == "GRENADE":
            return "gl"
        if weapon_name == "ROCKET":
            return "rl"
        if weapon_name == "LIGHTNING":
            return "lg"
        if weapon_name == "RAILGUN":
            return "rg"
        if weapon_name == "PLASMA":
            return "pg"
        if weapon_name == "HMG":
            return "hmg"
        if weapon_name == "BFG":
            return "bfg"
        if weapon_name == "GAUNTLET":
            return "g"
        if weapon_name == "NAILGUN":
            return "ng"
        if weapon_name == "PROXMINE":
            return "pl"
        if weapon_name == "CHAINGUN":
            return "cg"
        return "other"


class WeaponStatsEntry:
    def __init__(
        self,
        weapon,
        kills,
        deaths,
        damage_dealt,
        damage_received,
        shots,
        hits,
        pickups,
        time,
    ):
        self.weapon = weapon
        self.kills = kills
        self.deaths = deaths
        self.damage_dealt = damage_dealt
        self.damage_received = damage_received
        self.shots = shots
        self.hits = hits
        self.pickups = pickups
        self.time = time

    def __repr__(self):
        formatted_ammo_type = self.weapon.ammo_type().upper()
        return (
            f"[{formatted_ammo_type}: K:{self.kills} D:{self.deaths} DG:{self.damage_dealt} "
            f"DR:{self.damage_received} S:{self.shots} H:{self.hits} P:{self.pickups} T:{self.time}]"
        )

    def accuracy(self):
        if self.shots == 0:
            return 0
        return self.hits / self.shots * 100

    @property
    def name(self):
        return self.weapon.weapon_name()
