import random
import math

from typing import NamedTuple, Optional, Callable, Any, Union, List, Tuple, Dict
import itertools
from operator import itemgetter

import statistics

from datetime import datetime, timedelta

import redis

import minqlx
from minqlx import Plugin, Player, AbstractChannel

SteamId = int


class Position(NamedTuple):
    x: int
    y: int
    z: int


def calculate_distance(previous: Position, current: Position) -> float:
    return math.sqrt(
        (current.x - previous.x) ** 2 +
        (current.y - previous.y) ** 2 +
        (current.z - previous.z) ** 2)


def format_float(value: float) -> str:
    return f"{value:,.02f}".replace(",", ";").replace(".", ",").replace(";", ".")


def format_int(value: int) -> str:
    return f"{value:,d}".replace(",", ".")


def convert_units_to_meters(units: float) -> float:
    # source for the conversion: https://www.quake3world.com/forum/viewtopic.php?f=10&t=50384
    return 0.3048 * units / 8  # 8 units equal one inch, one inch equals 30,48cm


def determine_means_of_death(means_of_death: str) -> str:
    if means_of_death == "HURT":
        return "void"

    if means_of_death == "SLIME":
        return "acid"

    if means_of_death == "WATER":
        return "drowning"

    if means_of_death == "CRUSH":
        return "squished"

    return means_of_death.lower()


class WeaponStats(NamedTuple):
    name: str
    deaths: int
    damage_dealt: int
    damage_taken: int
    hits: int
    kills: int
    pickups: int
    shots: int
    time: int

    @property
    def accuracy(self) -> float:
        if self.shots == 0:
            return 0.0

        return self.hits / self.shots * 100

    @property
    def shortname(self) -> str:
        if self.name == "MACHINEGUN":
            return "mg"
        if self.name == "SHOTGUN":
            return "sg"
        if self.name == "GRENADE":
            return "gl"
        if self.name == "ROCKET":
            return "rl"
        if self.name == "LIGHTNING":
            return "lg"
        if self.name == "RAILGUN":
            return "rg"
        if self.name == "PLASMA":
            return "pg"
        if self.name == "HMG":
            return "hmg"
        if self.name == "BFG":
            return "bfg"
        if self.name == "GAUNTLET":
            return "g"
        if self.name == "NAILGUN":
            return "ng"
        if self.name == "PROXMINE":
            return "pl"
        if self.name == "CHAINGUN":
            return "cg"
        return "other"


class Damage(NamedTuple):
    dealt: int
    taken: int


class Medals(NamedTuple):
    accuracy: int
    assists: int
    captures: int
    combokill: int
    defends: int
    excellent: int
    firstfrag: int
    headshot: int
    humiliation: int
    impressive: int
    midair: int
    perfect: int
    perforated: int
    quadgod: int
    rampage: int
    revenge: int


class Pickups(NamedTuple):
    ammo: int
    armor: int
    armor_regen: int
    battlesuit: int
    doubler: int
    flight: int
    green_armor: int
    guard: int
    haste: int
    health: int
    invisibility: int
    invulnerability: int
    kamikaze: int
    medkit: int
    mega_health: int
    other_holdable: int
    other_powerup: int
    portal: int
    quad: int
    red_armor: int
    regeneration: int
    scout: int
    teleporter: int
    yellow_armor: int


class Weapons(NamedTuple):
    machinegun: WeaponStats
    shotgun: WeaponStats
    grenade_launcher: WeaponStats
    rocket_launcher: WeaponStats
    lightninggun: WeaponStats
    railgun: WeaponStats
    plasmagun: WeaponStats
    hmg: WeaponStats
    bfg: WeaponStats
    gauntlet: WeaponStats
    nailgun: WeaponStats
    proximity_mine_launcher: WeaponStats
    chaingun: WeaponStats
    other: WeaponStats


class PlayerStatsEntry:
    def __init__(self, stats_data: Dict[str, Any]):
        if "TYPE" not in stats_data:
            raise ValueError("Unknown stats_data")

        if stats_data["TYPE"] != "PLAYER_STATS":
            raise ValueError("Invalid stats type")

        if "DATA" not in stats_data:
            raise ValueError("stats contain no data")

        self.stats_data = [stats_data]

    def __repr__(self) -> str:
        return f"{self.stats_data}"

    @property
    def steam_id(self) -> SteamId:
        return int(self.stats_data[-1]["DATA"].get("STEAM_ID", "-1"))

    @property
    def aborted(self) -> bool:
        for stats_entry in self.stats_data:
            if "ABORTED" in stats_entry["DATA"] and stats_entry["DATA"].get("ABORTED", False):
                return True

        return False

    def _sum_entries(self, entry: str) -> int:
        returned = 0
        for stats_entry in self.stats_data:
            if "DATA" not in stats_entry:
                continue

            returned += stats_entry["DATA"].get(entry, 0)

        return returned

    @property
    def blue_flag_pickups(self) -> int:
        return self._sum_entries("BLUE_FLAG_PICKUPS")

    @property
    def damage(self) -> Damage:
        returned = Damage(0, 0)
        for stats_entry in self.stats_data:
            if "DAMAGE" not in stats_entry["DATA"]:
                continue

            damage_entry = Damage(stats_entry["DATA"]["DAMAGE"].get("DEALT", 0),
                                  stats_entry["DATA"]["DAMAGE"].get("TAKEN", 0))
            returned = Damage(returned.dealt + damage_entry.dealt,
                              returned.taken + damage_entry.taken)

        return returned

    @property
    def deaths(self) -> int:
        return self._sum_entries("DEATHS")

    @property
    def holy_shits(self) -> int:
        return self._sum_entries("HOLY_SHITS")

    @property
    def kills(self) -> int:
        return self._sum_entries("KILLS")

    @property
    def lose(self) -> int:
        return self._sum_entries("LOSE")

    @property
    def match_guid(self) -> int:
        return self.stats_data[-1]["DATA"].get("MATCH_GUID", "")

    @property
    def max_streak(self) -> int:
        max_streaks = [stats_entry["DATA"].get("MAX_STREAK", 0) for stats_entry in self.stats_data]
        return max(max_streaks)

    @property
    def medals(self) -> Medals:
        returned = Medals(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        for stats_entry in self.stats_data:
            if "MEDALS" not in stats_entry["DATA"]:
                continue

            medal_entry = Medals(stats_entry["DATA"]["MEDALS"].get("ACCURACY", 0),
                                 stats_entry["DATA"]["MEDALS"].get("ASSISTS", 0),
                                 stats_entry["DATA"]["MEDALS"].get("CAPTURES", 0),
                                 stats_entry["DATA"]["MEDALS"].get("COMBOKILL", 0),
                                 stats_entry["DATA"]["MEDALS"].get("DEFENDS", 0),
                                 stats_entry["DATA"]["MEDALS"].get("EXCELLENT", 0),
                                 stats_entry["DATA"]["MEDALS"].get("FIRSTFRAG", 0),
                                 stats_entry["DATA"]["MEDALS"].get("HEADSHOT", 0),
                                 stats_entry["DATA"]["MEDALS"].get("HUMILIATION", 0),
                                 stats_entry["DATA"]["MEDALS"].get("IMPRESSIVE", 0),
                                 stats_entry["DATA"]["MEDALS"].get("MIDAIR", 0),
                                 stats_entry["DATA"]["MEDALS"].get("PERFECT", 0),
                                 stats_entry["DATA"]["MEDALS"].get("PERFORATED", 0),
                                 stats_entry["DATA"]["MEDALS"].get("QUADGOD", 0),
                                 stats_entry["DATA"]["MEDALS"].get("RAMPAGE", 0),
                                 stats_entry["DATA"]["MEDALS"].get("REVENGE", 0))

            returned = Medals(
                returned.accuracy + medal_entry.accuracy,
                returned.assists + medal_entry.assists,
                returned.captures + medal_entry.captures,
                returned.combokill + medal_entry.combokill,
                returned.defends + medal_entry.defends,
                returned.excellent + medal_entry.excellent,
                returned.firstfrag + medal_entry.firstfrag,
                returned.headshot + medal_entry.headshot,
                returned.humiliation + medal_entry.humiliation,
                returned.impressive + medal_entry.impressive,
                returned.midair + medal_entry.midair,
                returned.perfect + medal_entry.perfect,
                returned.perforated + medal_entry.perforated,
                returned.quadgod + medal_entry.quadgod,
                returned.rampage + medal_entry.rampage,
                returned.revenge + medal_entry.revenge)

        return returned

    @property
    def model(self) -> str:
        return self.stats_data[-1]["DATA"].get("MODEL", "")

    @property
    def name(self) -> str:
        return self.stats_data[-1]["DATA"].get("NAME", "")

    @property
    def neutral_flag_pickups(self) -> int:
        return self._sum_entries("NEUTRAL_FLAG_PICKUPS")

    @property
    def pickups(self) -> Pickups:
        returned = Pickups(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        for stats_entry in self.stats_data:
            if "PICKUPS" not in stats_entry["DATA"]:
                continue

            pickup_entry = Pickups(
                stats_entry["DATA"]["PICKUPS"].get("AMMO", 0),
                stats_entry["DATA"]["PICKUPS"].get("ARMOR", 0),
                stats_entry["DATA"]["PICKUPS"].get("ARMOR_REGEN", 0),
                stats_entry["DATA"]["PICKUPS"].get("BATTLESUIT", 0),
                stats_entry["DATA"]["PICKUPS"].get("DOUBLER", 0),
                stats_entry["DATA"]["PICKUPS"].get("FLIGHT", 0),
                stats_entry["DATA"]["PICKUPS"].get("GREEN_ARMOR", 0),
                stats_entry["DATA"]["PICKUPS"].get("GUARD", 0),
                stats_entry["DATA"]["PICKUPS"].get("HASTE", 0),
                stats_entry["DATA"]["PICKUPS"].get("HEALTH", 0),
                stats_entry["DATA"]["PICKUPS"].get("INVIS", 0),
                stats_entry["DATA"]["PICKUPS"].get("INVULNERABILITY", 0),
                stats_entry["DATA"]["PICKUPS"].get("KAMIKAZE", 0),
                stats_entry["DATA"]["PICKUPS"].get("MEDKIT", 0),
                stats_entry["DATA"]["PICKUPS"].get("MEGA_HEALTH", 0),
                stats_entry["DATA"]["PICKUPS"].get("OTHER_HOLDABLE", 0),
                stats_entry["DATA"]["PICKUPS"].get("OTHER_POWERUP", 0),
                stats_entry["DATA"]["PICKUPS"].get("PORTAL", 0),
                stats_entry["DATA"]["PICKUPS"].get("QUAD", 0),
                stats_entry["DATA"]["PICKUPS"].get("RED_ARMOR", 0),
                stats_entry["DATA"]["PICKUPS"].get("REGEN", 0),
                stats_entry["DATA"]["PICKUPS"].get("SCOUT", 0),
                stats_entry["DATA"]["PICKUPS"].get("TELEPORTER", 0),
                stats_entry["DATA"]["PICKUPS"].get("YELLOW_ARMOR", 0))

            returned = Pickups(
                returned.ammo + pickup_entry.ammo,
                returned.armor + pickup_entry.armor,
                returned.armor_regen + pickup_entry.armor_regen,
                returned.battlesuit + pickup_entry.battlesuit,
                returned.doubler + pickup_entry.doubler,
                returned.flight + pickup_entry.flight,
                returned.green_armor + pickup_entry.green_armor,
                returned.guard + pickup_entry.guard,
                returned.haste + pickup_entry.haste,
                returned.health + pickup_entry.health,
                returned.invisibility + pickup_entry.invisibility,
                returned.invulnerability + pickup_entry.invulnerability,
                returned.kamikaze + pickup_entry.kamikaze,
                returned.medkit + pickup_entry.medkit,
                returned.mega_health + pickup_entry.mega_health,
                returned.other_holdable + pickup_entry.other_holdable,
                returned.other_powerup + pickup_entry.other_powerup,
                returned.portal + pickup_entry.portal,
                returned.quad + pickup_entry.quad,
                returned.red_armor + pickup_entry.red_armor,
                returned.regeneration + pickup_entry.regeneration,
                returned.scout + pickup_entry.scout,
                returned.teleporter + pickup_entry.teleporter,
                returned.yellow_armor + pickup_entry.yellow_armor)

        return returned

    @property
    def play_time(self) -> int:
        return self._sum_entries("PLAY_TIME")

    @property
    def quit(self) -> int:
        return self._sum_entries("QUIT")

    @property
    def red_flag_pickups(self) -> int:
        return self._sum_entries("RED_FLAG_PICKUPS")

    @property
    def score(self) -> int:
        return self._sum_entries("SCORE")

    @property
    def warmup(self) -> bool:
        return self.stats_data[-1]["DATA"].get("WARMUP", False)

    @property
    def weapons(self) -> Weapons:
        return Weapons(
            self._sum_weapon("MACHINEGUN"),
            self._sum_weapon("SHOTGUN"),
            self._sum_weapon("GRENADE"),
            self._sum_weapon("ROCKET"),
            self._sum_weapon("LIGHTNING"),
            self._sum_weapon("RAILGUN"),
            self._sum_weapon("PLASMA"),
            self._sum_weapon("HMG"),
            self._sum_weapon("BFG"),
            self._sum_weapon("GAUNTLET"),
            self._sum_weapon("NAILGUN"),
            self._sum_weapon("PROXMINE"),
            self._sum_weapon("CHAINGUN"),
            self._sum_weapon("OTHER_WEAPON"))

    def _sum_weapon(self, weapon_name: str) -> WeaponStats:
        returned = WeaponStats(weapon_name, 0, 0, 0, 0, 0, 0, 0, 0)
        for stats_entry in self.stats_data:
            if "WEAPONS" not in stats_entry["DATA"]:
                continue

            if weapon_name not in stats_entry["DATA"]["WEAPONS"]:
                continue

            weapon_entry = WeaponStats(weapon_name,
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("D", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("DG", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("DR", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("H", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("K", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("P", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("S", 0),
                                       stats_entry["DATA"]["WEAPONS"][weapon_name].get("T", 0))

            returned = WeaponStats(weapon_name,
                                   returned.deaths + weapon_entry.deaths,
                                   returned.damage_dealt + weapon_entry.damage_dealt,
                                   returned.damage_taken + weapon_entry.damage_taken,
                                   returned.hits + weapon_entry.hits,
                                   returned.kills + weapon_entry.kills,
                                   returned.pickups + weapon_entry.pickups,
                                   returned.shots + weapon_entry.shots,
                                   returned.time + weapon_entry.time)

        return returned

    @property
    def win(self) -> int:
        return self._sum_entries("WIN")

    def combine(self, other: object) -> None:
        if not isinstance(other, PlayerStatsEntry):
            raise ValueError("Unknown combination element given")

        if other.match_guid != self.match_guid:
            raise ValueError("Cannot combine stats from different match_guids")

        if other.warmup != self.warmup:
            raise ValueError("Cannot combine stats from warmup and real game")

        if other.steam_id != self.steam_id:
            raise ValueError("Cannot combine stats for two different players")

        for stats_entry in other.stats_data:
            self.stats_data.append(stats_entry)


def filter_stats_for_max_value(stats: List[PlayerStatsEntry], func: Callable[[PlayerStatsEntry], Any]) \
        -> List[PlayerStatsEntry]:
    max_value = max(stats, key=func)
    return list(filter(lambda stats_entry: func(stats_entry) == func(max_value), stats))


def most_weapon_hits_announcement(stats: List[PlayerStatsEntry]) -> Optional[str]:
    returned = ""

    for announcement, filter_func in [
        ("Gauntleteer", lambda stats_entry: stats_entry.weapons.gauntlet.hits),
        ("Machinist", lambda stats_entry: stats_entry.weapons.machinegun.hits),
        ("Shotgunner", lambda stats_entry: stats_entry.weapons.shotgun.hits),
        ("Nader", lambda stats_entry: stats_entry.weapons.grenade_launcher.hits),
        ("Rocketeer", lambda stats_entry: stats_entry.weapons.rocket_launcher.hits),
        ("Shafter", lambda stats_entry: stats_entry.weapons.lightninggun.hits),
        ("Railer", lambda stats_entry: stats_entry.weapons.railgun.hits),
        ("Plasmagunner", lambda stats_entry: stats_entry.weapons.plasmagun.hits),
        ("Heavy Machinist", lambda stats_entry: stats_entry.weapons.hmg.hits),
        ("BFGer", lambda stats_entry: stats_entry.weapons.bfg.hits),
        ("Nailer", lambda stats_entry: stats_entry.weapons.nailgun.hits),
        ("Miner", lambda stats_entry: stats_entry.weapons.proximity_mine_launcher.hits),
        ("Chainer", lambda stats_entry: stats_entry.weapons.chaingun.hits),
        ("Grappler", lambda stats_entry: stats_entry.weapons.other.hits)

    ]:
        most_effective_players = filter_stats_for_max_value(stats, filter_func)
        if len(most_effective_players) > 0 and filter_func(most_effective_players[0]) > 0:
            most_effective_player_names = "^7, ".join([_stats.name for _stats in most_effective_players])
            if len(most_effective_players) == 1:
                returned += f"^5{announcement}^7: {most_effective_player_names}^7 " \
                            f"(^5{format_int(filter_func(most_effective_players[0]))}^7 hits) "
            else:
                returned += f"^5{announcement}s^7: {most_effective_player_names}^7 " \
                            f"(^5{format_int(filter_func(most_effective_players[0]))}^7 hits) "
    if len(returned.strip()) == 0:
        return None

    return f"  Players with most hits per weapon: {returned}"


def most_accurate_railbitches_announcement(stats: List[PlayerStatsEntry]) -> Optional[str]:
    railbitches = filter_stats_for_max_value(stats, lambda stats_entry: stats_entry.weapons.railgun.accuracy)
    if len(railbitches) == 0:
        return None

    if railbitches[0].weapons.railgun.accuracy < 0.01:
        return None

    if len(railbitches) == 1:
        return f"  ^5Railbitch award^7: {railbitches[0].name}^7 " \
               f"(^5{railbitches[0].weapons.railgun.accuracy:.02f}^7 percent accuracy)"

    railbitch_player_names = "^7, ".join([stats.name for stats in railbitches])
    return f"  ^5Railbitch awards^7: {railbitch_player_names}^7 " \
           f"(^5{railbitches[0].weapons.railgun.accuracy:.02f}^7 percent accuracy)"


def longest_shaftlamers_announcement(stats: List[PlayerStatsEntry]) -> Optional[str]:
    shaftlamers = filter_stats_for_max_value(stats, lambda stats_entry: stats_entry.weapons.lightninggun.time)
    if len(shaftlamers) == 0:
        return None

    if shaftlamers[0].weapons.lightninggun.time <= 0:
        return None

    if len(shaftlamers) == 1:
        return f"  ^5Shaftlamer award^7: {shaftlamers[0].name}^7 " \
               f"(^5{shaftlamers[0].weapons.lightninggun.time}^7 seconds)"

    shaftlamer_player_names = "^7, ".join([stats.name for stats in shaftlamers])

    return f"  ^5Shaftlamer awards^7: {shaftlamer_player_names}^7 " \
           f"(^5{shaftlamers[0].weapons.lightninggun.time}^7 seconds)"


def most_honorable_haste_pickup_announcement(stats: List[PlayerStatsEntry]) -> Optional[str]:
    hasters = filter_stats_for_max_value(stats, lambda stats_entry: stats_entry.pickups.haste)
    if len(hasters) == 0:
        return None

    if hasters[0].pickups.haste <= 0:
        return None

    if len(hasters) == 1:
        return f"  ^5Haste honor award^7: {hasters[0].name}^7 (^5{hasters[0].pickups.haste}^7 pickups)"

    haste_player_names = "^7, ".join([stats.name for stats in hasters])
    return f"  ^5Haste honor awards^7: {haste_player_names}^7 (^5{hasters[0].pickups.haste}^7 pickups)"


def weird_facts(stats: List[PlayerStatsEntry]) -> Optional[str]:
    medal_facts = random_medal_facts(stats)
    formatted_weird_facts = medal_facts[0]
    if len(medal_facts) > 1:
        for medal_fact in medal_facts[1:]:
            formatted_weird_facts += random_conjunction()
            formatted_weird_facts += medal_fact

    for weapon_fact in random_weapon_stats(stats):
        formatted_weird_facts += random_conjunction()
        formatted_weird_facts += weapon_fact

    return f"Some weird facts: {formatted_weird_facts}"


def random_conjunction() -> str:
    return random.choice([", and ", ", but ", ", while "])


def random_medal_facts(stats: List[PlayerStatsEntry], *, count: int = 1) -> List[str]:
    returned: List[str] = []

    medalstats = list(Medals._fields)
    random.shuffle(medalstats)

    for medalstat in medalstats:
        formatted_fact = formatted_medal_fact(stats, medalstat)
        if formatted_fact is not None and len(formatted_fact) > 0:
            returned.append(formatted_fact)
        if len(returned) == count:
            return returned

    return returned


def formatted_medal_fact(stats: List[PlayerStatsEntry], medal_stat: str) -> str:
    most_medaled_stats = \
        filter_stats_for_max_value(stats, lambda stats_entry: getattr(stats_entry.medals, medal_stat))

    if len(most_medaled_stats) > 0:
        medal_stat_value: int = getattr(most_medaled_stats[0].medals, medal_stat)
        if medal_stat_value > 0:
            if len(most_medaled_stats) == 1:
                player_names = most_medaled_stats[0].name
            else:
                player_names = "^7, ".join([stats.name for stats in most_medaled_stats[:-1]]) + \
                               "^7 and " + most_medaled_stats[-1].name
            return f"{player_names} received ^5{medal_stat_value} {medal_stat} medals^7"

    return ""


WEAPON_FACTS_LOOKUP: Dict[str, Dict[str, List[str]]] = {
    "deaths": {
        "machinegun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} was ^5machinegunned^7 ^5{stats_amount} times^7"
        ],
        "shotgun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} chewed on ^5{stats_amount} boomsticks^7",
            "{player_names} ate ^5{stats_amount} loads of buckshots^7",
            "{player_names} was ^5gunned down^7 ^5{stats_amount} times^7"
        ],
        "grenade_launcher": [
            "{player_names} died from a ^5nade^7 ^5{stats_amount} times^7",
            "{player_names} ate ^5{stats_amount} pineapples^7",
            "{player_names} was shredded by ^5{stats_amount} shrapnels^7"
        ],
        "rocket_launcher": [
            "{player_names} died from a ^5rocket^7 ^5{stats_amount} times^7",
            "{player_names} caught ^5{stats_amount} lethal rockets^7 successfully",
            "{player_names} donated his body to ^5rocket science^7 ^5{stats_amount} times^7",
            "{player_names} rode ^5{stats_amount} rockets^7"
        ],
        "lightninggun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} accepted ^5{stats_amount} shafts^7",
            "{player_names} was ^5electrocuted^7 ^5{stats_amount} times^7"
        ],
        "railgun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "plasmagun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "hmg": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "bfg": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "gauntlet": [
            "{player_names} was ^5pummeled {stats_amount} times^7",
            "{player_names} was ^5humiliated {stats_amount} times^7"
        ],
        "nailgun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} was ^5nailed {stats_amount} times^7",
            "{player_names} was ^5punctured {stats_amount} times^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} died from a ^5proximity mine^7 ^5{stats_amount} times^7",
            "{player_names} was too close to ^5{stats_amount} proximity mines^7"
        ],
        "chaingun": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} got ^5lead poisining^7 ^5{stats_amount} times^7"
        ],
        "grapple": [
            "{player_names} died from a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ]
    },
    "damage_dealt": {
        "machinegun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "shotgun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "grenade_launcher": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} nade damage^7"
        ],
        "rocket_launcher": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} rocket damage^7",
            "{player_names} spammed a total of ^5{stats_amount} rocket damage^7"
        ],
        "lightninggun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "railgun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "plasmagun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "hmg": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "bfg": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "gauntlet": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "nailgun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} proximity mine damage^7"
        ],
        "chaingun": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "grapple": [
            "{player_names} ^2dealt^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ]
    },
    "damage_taken": {
        "machinegun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "shotgun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "grenade_launcher": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} grenade damage^7"
        ],
        "rocket_launcher": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} rocket damage^7"
        ],
        "lightninggun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "railgun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "plasmagun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "hmg": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "bfg": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "gauntlet": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "nailgun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} proximity mine damage^7"
        ],
        "chaingun": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ],
        "grapple": [
            "{player_names} ^1received^7 a total of ^5{stats_amount} {weapon_name} damage^7"
        ]
    },
    "hits": {
        "machinegun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "shotgun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "grenade_launcher": [
            "{player_names} hit with the ^5grenade launcher^7 ^5{stats_amount} times^7",
            "{stats_amount} of {player_names}'s lost nades have been found",
            "{player_names} dropped {stats_amount} lucky nades"
        ],
        "rocket_launcher": [
            "{player_names} hit with the ^5rocket launcher^7 ^5{stats_amount} times^7"
        ],
        "lightninggun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "railgun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7",
            "{player_names} camped successfully to hit ^5{stats_amount} rails^7"
        ],
        "plasmagun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "hmg": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "bfg": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "gauntlet": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "nailgun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} hit with the ^5proximity mine launcher^7 ^5{stats_amount} times^7"
        ],
        "chaingun": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "grapple": [
            "{player_names} hit with the ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ]
    },
    "kills": {
        "machinegun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "shotgun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "grenade_launcher": [
            "{player_names} killed ^5{stats_amount} enemies^7 with ^5nades^7"
        ],
        "rocket_launcher": [
            "{player_names} killed ^5{stats_amount} enemies^7 with ^5rockets^7",
            "{player_names} donated ^5{stats_amount}^7 enemy bodies to ^5rocket science^7"
        ],
        "lightninggun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "railgun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "plasmagun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "hmg": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "bfg": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "gauntlet": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "nailgun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} killed ^5{stats_amount} enemies^7 with ^5proximity mines^7"
        ],
        "chaingun": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ],
        "grapple": [
            "{player_names} killed ^5{stats_amount} enemies^7 with the ^5{weapon_name}^7"
        ]
    },
    "pickups": {
        "machinegun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "shotgun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "grenade_launcher": [
            "{player_names} picked up a ^5grenade launcher^7 ^5{stats_amount} times^7"
        ],
        "rocket_launcher": [
            "{player_names} picked up a ^5rocket launcher^7 ^5{stats_amount} times^7"
        ],
        "lightninggun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "railgun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "plasmagun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "hmg": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "bfg": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "gauntlet": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "nailgun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "proximity_mine_launcher": [
            "{player_names} picked up a ^5proximity mine launcher^7 ^5{stats_amount} times^7"
        ],
        "chaingun": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ],
        "grapple": [
            "{player_names} picked up a ^5{weapon_name}^7 ^5{stats_amount} times^7"
        ]
    },
    "time": {
        "machinegun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "shotgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "grenade_launcher": [
            "{player_names} used the ^5grenade launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5grenade launcher^7 and held it for {stats_amount} seconds",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "rocket_launcher": [
            "{player_names} used the ^5rocket launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5rocket launcher^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5rocket launcher^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "lightninggun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "railgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "plasmagun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "hmg": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "bfg": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "gauntlet": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "nailgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "proximity_mine_launcher": [
            "{player_names} used the ^5proximity mine launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5proximity mine launcher^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5proximity mine launcher^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "chaingun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ],
        "grapple": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds"
        ]
    }
}


def format_weapon_fact(weapon_stat: str, player_names: str, weapon_name: str, stats_amount: int) -> str:
    if weapon_stat not in ["deaths", "damage_dealt", "damage_taken", "hits", "kills", "pickups", "time"]:
        return f"{player_names} had ^5{stats_amount} {weapon_name.replace('_', ' ')} {weapon_stat.replace('_', ' ')}^7"

    response_template = random.choice(WEAPON_FACTS_LOOKUP[weapon_stat][weapon_name])
    return response_template.format(player_names=player_names, weapon_name=weapon_name,
                                    stats_amount=format_int(stats_amount))


def random_weapon_stats(stats: List[PlayerStatsEntry], *, count: int = 3) -> List[str]:
    returned: List[str] = []

    weaponstats = [field for field in WeaponStats._fields if field not in ["name"]]
    randomized_weapon_stats = list(itertools.product(Weapons._fields, weaponstats))
    random.shuffle(randomized_weapon_stats)
    for weapon, weapon_fact in randomized_weapon_stats:
        formatted_fact = formatted_weapon_fact(stats, weapon, weapon_fact)
        if formatted_weapon_fact is not None and len(formatted_fact) > 0:
            returned.append(formatted_fact)

        if len(returned) == count:
            return returned

    return returned


def formatted_weapon_fact(stats: List[PlayerStatsEntry], weapon: str, weapon_fact: str) -> str:
    most_weaponed_stats = filter_stats_for_max_value(
        stats, lambda stats_entry: getattr(getattr(stats_entry.weapons, weapon), weapon_fact))

    if len(most_weaponed_stats) > 0:
        if len(most_weaponed_stats) == 1:
            player_names = most_weaponed_stats[0].name
        else:
            player_names = "^7, ".join([stats.name for stats in most_weaponed_stats[:-1]]) + \
                           "^7 and " + most_weaponed_stats[-1].name
        stats_amount = getattr(getattr(most_weaponed_stats[0].weapons, weapon), weapon_fact)
        if stats_amount > 0:
            return format_weapon_fact(weapon_fact, player_names,
                                      weapon.replace('other', 'grapple'), stats_amount)

    return ""


LAST_USED_NAME_KEY: str = "minqlx:players:{}:last_used_name"
PLAYER_TOP_SPEEDS: str = "minqlx:players:{}:topspeed"
MAP_TOP_SPEEDS: str = "minqlx:maps:{}:topspeed"
MAP_SPEED_LOG: str = "minqlx:maps:{}:speedlog"


# noinspection PyPep8Naming
class weird_stats(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_weirdstats_playtime_fraction", "0.75")
        self.set_cvar_once("qlx_weirdstats_topdisplay", "3")
        self.set_cvar_once("qlx_weirdstats_fastestmaps_display_ingame", "10")
        self.set_cvar_once("qlx_weirdstats_fastestmaps_display_warmup", "30")

        self.stats_play_time_fraction: float = self.get_cvar("qlx_weirdstats_playtime_fraction", float)  # type: ignore
        self.stats_top_display: int = self.get_cvar("qlx_weirdstats_topdisplay", int)  # type: ignore
        if self.stats_top_display < 0:
            self.stats_top_display = 666
        self.fastestmaps_display_ingame: int = \
            self.get_cvar("qlx_weirdstats_fastestmaps_display_ingame", int)  # type: ignore
        self.fastestmaps_display_warmup: int = \
            self.get_cvar("qlx_weirdstats_fastestmaps_display_warmup", int)  # type: ignore

        self.game_start_time: Optional[datetime] = None
        self.join_times: Dict[SteamId, datetime] = {}
        self.play_times: Dict[SteamId, float] = {}

        self.in_round: bool = False
        self.game_ended: bool = False
        self.match_end_announced: bool = False

        self.means_of_death: Dict[SteamId, Dict[str, int]] = {}

        self.round_start_datetime: Optional[datetime] = None
        self.fastest_death: Tuple[SteamId, float] = -1, -1
        self.alive_times: Dict[SteamId, float] = {}
        self.previous_positions: Dict[SteamId, Position] = {}
        self.travelled_distances: Dict[SteamId, float] = {}

        self.player_stats: Dict[SteamId, PlayerStatsEntry] = {}
        self.playerstats_announcements: List[Callable[[List[PlayerStatsEntry]], Optional[str]]] = \
            [most_accurate_railbitches_announcement, longest_shaftlamers_announcement,
             most_honorable_haste_pickup_announcement, weird_facts]

        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("frame", self.handle_frame)
        self.add_hook("map", self.handle_map_change)
        self.add_hook("game_start", self.handle_game_start)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("death", self.handle_death)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("stats", self.handle_stats)

        self.add_command("speeds", self.cmd_player_speeds)

        self.add_command("topspeeds", self.cmd_player_top_speeds, usage="[NAME]")
        self.add_command("maptopspeeds", self.cmd_map_top_speeds, usage="[NAME]")
        self.add_command(("fastestmaps", "slowestmaps"), self.cmd_fastest_maps)

    def handle_team_switch(self, player: Player, old_team: str, new_team: str):
        if not player:
            return

        if not self.game:
            return

        if self.game.state in ["warmup", "countdown"]:
            return

        if player.steam_id in self.join_times:
            if new_team in ["spectator"]:
                self.play_times[player.steam_id] = \
                    (datetime.now() - self.join_times[player.steam_id]).total_seconds() + \
                    self.play_times.get(player.steam_id, 0.0)
            return

        if new_team not in ["red", "blue"]:
            return

        if old_team not in "spectator":
            return

        self.join_times[player.steam_id] = datetime.now()

    def handle_frame(self) -> None:
        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            if not player.is_alive:
                if player.steam_id in self.previous_positions:
                    del self.previous_positions[player.steam_id]
                continue

            distance = self.travelled_distances.get(player.steam_id, 0.0)
            moved_distance = self.calculate_player_distance(player)

            if self.in_round and moved_distance < 800.0:
                self.travelled_distances[player.steam_id] = distance + moved_distance

            self.previous_positions[player.steam_id] = Position(*player.position())

    def calculate_player_distance(self, player: Player) -> float:
        if not player.is_alive:
            return 0.0

        if player.steam_id not in self.previous_positions:
            return 0.0

        return calculate_distance(self.previous_positions[player.steam_id], Position(*player.position()))

    def handle_map_change(self, _mapname: str, _factory: str) -> None:
        self.reinitialize_game()

    def reinitialize_game(self) -> None:
        self.game_start_time = None
        self.join_times = {}
        self.play_times = {}
        self.alive_times = {}
        self.in_round = False
        self.game_ended = False
        self.means_of_death = {}
        self.match_end_announced = False
        self.round_start_datetime = None
        self.player_stats = {}
        self.previous_positions = {}
        self.travelled_distances = {}
        self.fastest_death = -1, -1

    @minqlx.delay(3)
    def handle_game_start(self, _data) -> None:
        teams = self.teams()
        self.game_start_time = datetime.now()
        self.join_times = {player.steam_id: self.game_start_time for player in teams["red"] + teams["blue"]}

    def handle_round_start(self, _round_number: int) -> None:
        self.in_round = True
        self.game_ended = False
        self.match_end_announced = False
        self.round_start_datetime = datetime.now()

        teams = self.teams()
        self.previous_positions = {player.steam_id: Position(*player.position())
                                   for player in teams["red"] + teams["blue"]}

    def handle_death(self, victim: Player, killer: Player, data: dict) -> None:
        self.record_means_of_death(victim, killer, data["MOD"])

        if self.in_round:
            self.record_alive_time(victim)

    def record_means_of_death(self, victim: Player, killer: Player, means_of_death: str) -> None:
        if not self.game or self.game.state != "in_progress":
            return

        if means_of_death == "SWITCHTEAM":
            return

        if killer is not None and victim is not None and victim.steam_id == killer.steam_id:
            return

        if victim is None:
            return

        means_of_death = determine_means_of_death(means_of_death)
        if victim.steam_id not in self.means_of_death:
            self.means_of_death[victim.steam_id] = {}
        self.means_of_death[victim.steam_id][means_of_death] = \
            self.means_of_death[victim.steam_id].get(means_of_death, 0) + 1

    def record_alive_time(self, *players: Player) -> None:
        if not self.game or self.game.state != "in_progress":
            return

        if self.round_start_datetime is None:
            return

        player_alive_timedelta: timedelta = datetime.now() - self.round_start_datetime
        player_alive_time: float = player_alive_timedelta.total_seconds()

        for player in players:
            if self.fastest_death == (-1, -1) or self.fastest_death[1] > player_alive_time:
                self.fastest_death = player.steam_id, player_alive_time
            self.alive_times[player.steam_id] = self.alive_times.get(player.steam_id, 0.0) + player_alive_time

    def handle_round_end(self, _data: dict) -> None:
        self.in_round = False

        teams = self.teams()
        surviving_players = [player for player in teams["red"] + teams["blue"] if
                             player.is_alive and player.health > 0]
        self.record_alive_time(*surviving_players)

        self.round_start_datetime = None

    @minqlx.delay(3)
    def handle_game_end(self, _data: dict) -> None:
        self.game_ended = True

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            if player.steam_id not in self.join_times:
                continue
            self.play_times[player.steam_id] = \
                (datetime.now() - self.join_times[player.steam_id]).total_seconds() + \
                self.play_times.get(player.steam_id, 0.0)

        self.announce_match_end_stats()

    def handle_stats(self, stats: dict) -> None:
        if stats["TYPE"] != "PLAYER_STATS":
            return

        player_stats = PlayerStatsEntry(stats)

        if player_stats.warmup:
            return

        if player_stats.steam_id not in self.player_stats:
            self.player_stats[player_stats.steam_id] = player_stats
        else:
            self.player_stats[player_stats.steam_id].combine(player_stats)

        self.announce_match_end_stats()

    def announce_match_end_stats(self) -> None:
        if self.match_end_announced:
            return

        if not self.game_ended:
            return

        if not self.stats_from_all_players_collected():
            return

        self.match_end_announced = True

        announcements = self.player_speeds_announcements(top_entries=self.stats_top_display,
                                                         match_end_announcements=True)
        if len(announcements) > 0:
            self.msg(f"  ^5Top {self.stats_top_display} player speeds^7 {announcements[0]}")
            for msg in announcements[1:]:
                self.msg(msg)

        quickest_death_announcement = self.quickest_deaths()
        if quickest_death_announcement is not None and len(quickest_death_announcement) > 0:
            self.msg(quickest_death_announcement)
        most_environmental_deaths_announcement = \
            self.environmental_deaths(self.means_of_death, ["void", "lava", "acid", "drowning", "squished"])
        if most_environmental_deaths_announcement is not None and len(most_environmental_deaths_announcement) > 0:
            self.msg(most_environmental_deaths_announcement)

        for announcer in self.playerstats_announcements:
            stats_announcement: Optional[str] = announcer(list(self.player_stats.values()))
            if stats_announcement is not None and len(stats_announcement) > 0:
                self.msg(stats_announcement)

    def stats_from_all_players_collected(self) -> bool:
        steam_ids_in_stats = self.player_stats.keys()

        teams = self.teams()
        steam_ids_in_teams = [player.steam_id for player in teams["red"] + teams["blue"]]

        for steam_id in steam_ids_in_teams:
            if steam_id not in steam_ids_in_stats:
                return False

        return True

    def player_speeds_announcements(self, *, top_entries: int = -1, match_end_announcements: bool = False) -> List[str]:
        player_speeds: Dict[SteamId, float] = self.determine_player_speeds()
        if len(player_speeds) == 0:
            return []

        if not self.game:
            return []

        if match_end_announcements:
            self.record_speeds(self.game.map.lower(), player_speeds)

        grouped_speeds = itertools.groupby(
            sorted(player_speeds, key=player_speeds.get, reverse=True),  # type: ignore
            key=player_speeds.get)

        average_speed = statistics.mean(player_speeds.values())
        returned = [f"(avg: ^5{format_float(average_speed)} km/h^7)"]

        for counter, (speed, steam_ids) in enumerate(grouped_speeds, start=1):
            if 0 < top_entries < len(returned):
                return returned

            prefix = f"^5{counter:2}^7."

            if speed is None:
                continue

            for steam_id in steam_ids:
                player = self.player(steam_id)
                if player is None:
                    continue
                alive_time = self.alive_time_of(steam_id)
                if match_end_announcements:
                    dmg_per_second = self.player_stats[steam_id].damage.dealt / alive_time
                elif steam_id in self.player_stats:
                    dmg_per_second = (player.stats.damage_dealt + self.player_stats[steam_id].damage.dealt) \
                                     / alive_time
                else:
                    dmg_per_second = player.stats.damage_dealt / alive_time
                returned.append(
                    f"  {prefix} {player.name}^7 (^5{format_float(speed)} km/h^7, "
                    f"^5{format_float(dmg_per_second)} dmg/sec.^7)")

                prefix = "   "

        return returned

    def determine_current_play_times(self):
        current_play_times = self.play_times.copy()
        if self.game and self.game.state == "in_progress":
            current_datetime = datetime.now()
            teams = self.teams()
            for _player in teams["red"] + teams["blue"]:
                if _player.steam_id not in self.join_times:
                    continue
                current_play_times[_player.steam_id] = \
                    current_play_times.get(_player.steam_id, 0.0) + \
                    (current_datetime - self.join_times[_player.steam_id]).total_seconds()
        return current_play_times

    def determine_player_speeds(self) -> Dict[SteamId, float]:
        if len(self.travelled_distances) == 0 or len(self.alive_times) == 0:
            return {}

        current_play_times = self.determine_current_play_times()

        if len(current_play_times) == 0:
            return {}

        longest_join_time = max(current_play_times.values())

        player_speeds: Dict[SteamId, float] = {}
        for steam_id, alive_time in self.alive_times.items():
            player_units = self.travelled_distances.get(steam_id, 0.0)
            player_alive_time = self.alive_time_of(steam_id)
            if player_alive_time == 0.0:
                continue
            player_distance = convert_units_to_meters(player_units)

            if current_play_times.get(steam_id, 0.0) < self.stats_play_time_fraction * longest_join_time:
                continue

            player_speed = 3.6 * player_distance / player_alive_time

            player_speeds[steam_id] = round(player_speed, 2)

        return player_speeds

    def quickest_deaths(self) -> str:
        steam_id, alive_time = self.fastest_death

        if steam_id == -1:
            return ""

        alive_time_delta = timedelta(seconds=alive_time)
        player = self.player(steam_id)
        if player is None:
            quickest_death_name = str(steam_id)
        else:
            quickest_death_name = player.name

        return f"  ^5Quickest death^7: {quickest_death_name} (^5{alive_time_delta.total_seconds():.02f} seconds^7)"

    def environmental_deaths(self, means_of_death: Dict[SteamId, Dict[str, int]], means_of_death_filter: List[str]) \
            -> str:
        filtered_means_of_death: Dict[SteamId, int] = {}
        for steam_id, death_data in means_of_death.items():
            for mod in means_of_death_filter:
                filtered_means_of_death[steam_id] = \
                    filtered_means_of_death.get(steam_id, 0) + death_data.get(mod, 0)

        most_environmental_deaths = max(filtered_means_of_death, key=filtered_means_of_death.get)  # type: ignore
        if filtered_means_of_death[most_environmental_deaths] == 0:
            return ""
        most_entrironmental_deaths_steam_ids = [steam_id for steam_id, deaths in filtered_means_of_death.items()
                                                if deaths == filtered_means_of_death[most_environmental_deaths]]

        most_environmental_deaths_names = []
        for steam_id in most_entrironmental_deaths_steam_ids:
            player = self.player(steam_id)
            if player is None:
                most_environmental_deaths_names.append(str(steam_id))
            else:
                most_environmental_deaths_names.append(player.name)

        formatted_names = "^7, ".join(most_environmental_deaths_names)

        return f"  ^5Most environmental deaths^7: {formatted_names} " \
               f"(^5{filtered_means_of_death[most_environmental_deaths]}^7)"

    @minqlx.thread
    def record_speeds(self, mapname: str, speeds: Dict[SteamId, float]) -> None:
        if self.db is None:
            return

        top_map_speeds = self.map_speed_log(mapname)
        top_map_speeds_dict = dict(top_map_speeds)

        for steam_id, speed in speeds.items():
            self.record_personal_speed(mapname, steam_id, speed)
            if top_map_speeds_dict.get(steam_id, -1.0) < speed:
                # noinspection PyUnresolvedReferences
                if redis.VERSION >= (3, ):
                    self.db.zadd(PLAYER_TOP_SPEEDS.format(steam_id), {mapname: speed})
                    self.db.zadd(PLAYER_TOP_SPEEDS.format(mapname), {steam_id: speed})
                else:
                    self.db.zadd(PLAYER_TOP_SPEEDS.format(steam_id), speed, mapname)
                    self.db.zadd(MAP_TOP_SPEEDS.format(mapname), speed, steam_id)
            self.db.rpush(MAP_SPEED_LOG.format(mapname), speed)

    def record_personal_speed(self, mapname: str, steam_id: SteamId, speed: float) -> None:
        if self.db is None:
            return

        if speed == 0:
            return

        previous_top_speeds = self.db_get_top_speed_for_player(steam_id)

        previous_map_player_top_speeds = [topspeed for _mapname, topspeed in previous_top_speeds if mapname == _mapname]
        previous_map_player_top_speeds.sort(reverse=True)

        if len(previous_map_player_top_speeds) > 0 and previous_map_player_top_speeds[0] >= speed:
            return

        # noinspection PyUnresolvedReferences
        if redis.VERSION >= (3, ):
            self.db.zadd(PLAYER_TOP_SPEEDS.format(steam_id), {mapname: speed})
        else:
            self.db.zadd(PLAYER_TOP_SPEEDS.format(steam_id), speed, mapname)

    def cmd_player_speeds(self, _player: Player, _msg: str, _channel: AbstractChannel) -> None:
        announcements = self.player_speeds_announcements(top_entries=self.stats_top_display)
        if len(announcements) == 0:
            return

        self.msg(f"  ^5Top {self.stats_top_display} player speeds^7 {announcements[0]}")
        for announcement in announcements[1:]:
            self.msg(announcement)

    def cmd_player_top_speeds(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel) -> None:
        reply_channel = self.identify_reply_channel(channel)

        if len(msg) == 1:
            topspeed_name, topspeed_steam_id = self.identify_target(player, player)
        else:
            topspeed_name, topspeed_steam_id = self.identify_target(player, msg[1])
            if topspeed_name is None and topspeed_steam_id is None:
                return

        self.collect_and_report_player_top_speeds(reply_channel, topspeed_steam_id)

    @staticmethod
    def identify_reply_channel(channel: minqlx.AbstractChannel) -> minqlx.AbstractChannel:
        if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                       minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
            return minqlx.CHAT_CHANNEL

        return channel

    def identify_target(self, player: minqlx.Player, target: Union[str, int, minqlx.Player]):
        if isinstance(target, minqlx.Player):
            return target.name, target.steam_id

        try:
            steam_id = int(target)
            if self.db is not None and self.db.exists(LAST_USED_NAME_KEY.format(steam_id)):
                return self.resolve_player_name(steam_id), steam_id
        except ValueError:
            pass

        _player = self.find_target_player_or_list_alternatives(player, target)
        if _player is None:
            return None, None

        return _player.name, _player.steam_id

    def find_target_player_or_list_alternatives(self, player: minqlx.Player, target: Union[str, int]) \
            -> Optional[minqlx.Player]:
        def find_players(query: str) -> List[minqlx.Player]:
            players = []
            for p in self.find_player(query):
                if p not in players:
                    players.append(p)
            return players

        # Tell a player which players matched
        def list_alternatives(players: List[minqlx.Player], indent: int = 2) -> None:
            amount_alternatives = len(players)
            player.tell(f"A total of ^6{amount_alternatives}^7 players matched for {target}:")
            out = ""
            for p in players:
                out += " " * indent
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])

        # Get the list of matching players on name
        target_players = find_players(str(target))

        # even if we get only 1 person, we need to check if the input was meant as an ID
        # if we also get an ID we should return with ambiguity
        try:
            i = int(target)
            target_player = self.player(i)
            if not (0 <= i < 64) or not target_player:
                raise ValueError
            # Add the found ID if the player was not already found
            if target_player not in target_players:
                target_players.append(target_player)
        except ValueError:
            pass

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

    def resolve_player_name(self, item: Union[int, str]):
        if isinstance(item, str):
            if not item.isdigit():
                return item

        steam_id = int(item)

        player = self.player(steam_id)

        if player is not None:
            return player.name

        if self.db is not None and self.db.exists(LAST_USED_NAME_KEY.format(steam_id)):
            return self.db.get(LAST_USED_NAME_KEY.format(steam_id))

        return item

    @minqlx.thread
    def collect_and_report_player_top_speeds(self, channel: minqlx.AbstractChannel, steam_id: int) -> None:
        player_name = self.resolve_player_name(steam_id)
        top_speeds = self.db_get_top_speed_for_player(steam_id)
        if len(top_speeds) < 1:
            channel.reply(
                f"^7Player ^2{player_name}^7 has no entries in the TopSpeeds database table.")
            return

        reply = ""
        for mapname, speed in top_speeds:
            reply += f"[^5{mapname}^7-^3{speed:.2f} km/h^7] "

        channel.reply(
            f"^7Player ^2{player_name}^7's recorded top speeds: {reply}")

    def db_get_top_speed_for_player(self, steam_id: int) -> List[Tuple[str, float]]:
        if self.db is None:
            return []

        player_top_speeds = \
            self.db.zrevrangebyscore(PLAYER_TOP_SPEEDS.format(steam_id), "+INF", "-INF", withscores=True)
        interim_player_top_speeds = [(mapname, float(speed)) for mapname, speed in player_top_speeds]

        if len(player_top_speeds) == 0:
            return []

        interim_player_top_speeds.sort(key=lambda map_speed: map_speed[1], reverse=True)

        return interim_player_top_speeds[0:9]

    def cmd_map_top_speeds(self, _player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel) -> None:
        reply_channel = self.identify_reply_channel(channel)

        if len(msg) == 1:
            if not self.game:
                return
            mapname = self.game.map.lower()
        else:
            mapname = msg[1]
        self.collect_and_report_map_top_speeds(reply_channel, mapname)

    @minqlx.thread
    def collect_and_report_map_top_speeds(self, channel: minqlx.AbstractChannel, mapname: str) -> None:
        map_speed_statistics = self.map_speed_log(mapname)

        if len(map_speed_statistics) == 0:
            channel.reply(f"^7No records found for map ^6{mapname}^7.")
            return

        formatted_speeds = "^7] [".join([
                f"{self.resolve_player_name(steam_id)}-^5{speed:.2f} km/h" for steam_id, speed in
                map_speed_statistics[0:10]])
        channel.reply(f"^7All-time top 10 speeds for ^6{mapname}^7: ")
        channel.reply(f"^7[{formatted_speeds}^7].")

    def cmd_fastest_maps(self, _player: minqlx.Player, _msg: str, channel: minqlx.AbstractChannel) -> None:
        reply_channel = self.identify_reply_channel(channel)

        self.collect_and_report_fastest_maps(reply_channel)

    @minqlx.thread
    def collect_and_report_fastest_maps(self, channel: minqlx.AbstractChannel) -> None:
        if self.db is None:
            return

        all_avg_speeds: Dict[str, float] = {}
        for map_speed_key in self.db.keys(MAP_SPEED_LOG.format("*")):
            mapname = \
                map_speed_key[
                    len(MAP_SPEED_LOG.split('{', maxsplit=1)[0]):-len(MAP_SPEED_LOG.split('}', maxsplit=1)[1])
                ]
            raw_map_speeds = self.db.lrange(MAP_SPEED_LOG.format(mapname), 0, -1)
            if len(raw_map_speeds) == 0:
                continue

            map_speeds = [float(speed) for speed in raw_map_speeds]
            all_avg_speeds[mapname] = statistics.mean(map_speeds)

        if len(all_avg_speeds) == 0:
            channel.reply("^7No records yet. Please play more matches!")
            return

        if not self.game or self.game.state != "warmup":
            upper_limit = self.fastestmaps_display_ingame
        else:
            upper_limit = self.fastestmaps_display_warmup

        sorted_mapnames = sorted(all_avg_speeds, key=all_avg_speeds.get, reverse=True)  # type:ignore
        formatted_speeds = "^7] [".join([
                f"^6{mapname}-^5{all_avg_speeds[mapname]:.2f} km/h^7"
                for mapname in sorted_mapnames[0:upper_limit]])
        channel.reply(f"Top {upper_limit} fastest maps by average player speed:")
        channel.reply(f"^7[{formatted_speeds}^7].")

        sorted_mapnames.reverse()
        formatted_speeds = "^7] [".join([
                f"^6{mapname}-^5{all_avg_speeds[mapname]:.2f} km/h^7"
                for mapname in sorted_mapnames[0:upper_limit]])
        channel.reply(f"Top {upper_limit} slowest maps by average player speed:")
        channel.reply(f"^7[{formatted_speeds}^7].")

    def map_speed_log(self, mapname: str) -> List[Tuple[int, float]]:
        if self.db is None:
            return []

        map_damages = self.db.zrevrangebyscore(MAP_TOP_SPEEDS.format(mapname), "+INF", "-INF", withscores=True)
        interim_map_speeds = [(int(entry), float(value)) for entry, value in map_damages]
        interim_map_speeds.sort(key=itemgetter(1), reverse=True)

        return interim_map_speeds

    def alive_time_of(self, steam_id: SteamId) -> float:
        player = self.player(steam_id)

        player_alive_time = self.alive_times.get(steam_id, 0.0)
        if not self.in_round or self.round_start_datetime is None or not player or not player.is_alive:
            return player_alive_time

        current_datetime = datetime.now()
        player_alive_timedelta: timedelta = current_datetime - self.round_start_datetime
        return self.alive_times.get(steam_id, 0.0) + player_alive_timedelta.total_seconds()
