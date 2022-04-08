import random
import math

from typing import NamedTuple, Optional, Callable, Any, Literal
import itertools

import minqlx  # type: ignore
from minqlx import Plugin, Player

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


def determine_means_of_death(means_of_death):
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
    def __init__(self, stats_data: dict[str, Any]):
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


def filter_stats_for_max_value(stats: list[PlayerStatsEntry], func: Callable[[PlayerStatsEntry], Any]) \
        -> list[PlayerStatsEntry]:
    max_value = max(stats, key=func)
    return list(filter(lambda stats_entry: func(stats_entry) == func(max_value), stats))


def most_weapon_hits_announcement(stats: list[PlayerStatsEntry]) -> Optional[str]:
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


def most_accurate_railbitches_announcement(stats: list[PlayerStatsEntry]) -> Optional[str]:
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


def longest_shaftlamers_announcement(stats: list[PlayerStatsEntry]) -> Optional[str]:
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


def most_honorable_haste_pickup_announcement(stats: list[PlayerStatsEntry]) -> Optional[str]:
    hasters = filter_stats_for_max_value(stats, lambda stats_entry: stats_entry.pickups.haste)
    if len(hasters) == 0:
        return None

    if hasters[0].pickups.haste <= 0:
        return None

    if len(hasters) == 1:
        return f"  ^5Haste honor award^7: {hasters[0].name}^7 (^5{hasters[0].pickups.haste}^7 pickups)"

    haste_player_names = "^7, ".join([stats.name for stats in hasters])
    return f"  ^5Haste honor awards^7: {haste_player_names}^7 (^5{hasters[0].pickups.haste}^7 pickups)"


def weird_facts(stats: list[PlayerStatsEntry]) -> Optional[str]:
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


def random_medal_facts(stats: list[PlayerStatsEntry], *, count: int = 1) -> list[str]:
    returned: list[str] = []

    medalstats = list(Medals._fields)
    random.shuffle(medalstats)

    for medalstat in medalstats:
        formatted_fact = formatted_medal_fact(stats, medalstat)
        if formatted_fact is not None and len(formatted_fact) > 0:
            returned.append(formatted_fact)
        if len(returned) == count:
            return returned

    return returned


def formatted_medal_fact(stats: list[PlayerStatsEntry], medal_stat: str) -> str:
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
            return f"{player_names} received {medal_stat_value} {medal_stat} medals"

    return ""


WEAPON_FACTS_LOOKUP: dict[str, dict[str, list[str]]] = {
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
            "{player_names} was ^5humiliated {stats_amount} times^7}"
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
            "{player_names} ^2dealt^7 a total of ^5proximity mine {weapon_name} damage^7"
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
            "{player_names} dropped {stats_amount} lucky nades}"
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
            "for ^5{stats_amount}^7 seconds."
        ],
        "shotgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "grenade_launcher": [
            "{player_names} used the ^5grenade launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5grenade launcher^7 and held it for {stats_amount} seconds",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "rocket_launcher": [
            "{player_names} used the ^5rocket launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5rocket launcher^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5rocket launcher^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "lightninggun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "railgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "plasmagun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "hmg": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "bfg": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "gauntlet": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "nailgun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "proximity_mine_launcher": [
            "{player_names} used the ^5proximity mine launcher^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5proximity mine launcher^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5proximity mine launcher^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "chaingun": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ],
        "grapple": [
            "{player_names} used the ^5{weapon_name}^7 for ^5{stats_amount} seconds^7",
            "{player_names} really liked the ^5{weapon_name}^7 and held it for ^5{stats_amount} seconds^7",
            "{player_names}, in case you're wondering, cuddled with the ^5{weapon_name}^7 "
            "for ^5{stats_amount}^7 seconds."
        ]
    }
}


def format_weapon_fact(weapon_stat: str, player_names: str, weapon_name: str, stats_amount: int) -> str:
    if weapon_stat not in ["deaths", "damage_dealt", "damage_taken", "hits", "kills", "pickups", "time"]:
        return f"{player_names} had ^5{stats_amount} {weapon_name.replace('_', ' ')} {weapon_stat.replace('_', ' ')}^7"

    response_template = random.choice(WEAPON_FACTS_LOOKUP[weapon_stat][weapon_name])
    return response_template.format(player_names=player_names, weapon_name=weapon_name,
                                    stats_amount=format_int(stats_amount))


def random_weapon_stats(stats: list[PlayerStatsEntry], *, count: int = 3) -> list[str]:
    returned: list[str] = []

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


def formatted_weapon_fact(stats: list[PlayerStatsEntry], weapon: str, weapon_fact: str) -> str:
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


# noinspection PyPep8Naming
class weird_stats(Plugin):
    def __init__(self):
        super().__init__()

        self.in_round: bool = False
        self.game_ended: bool = False
        self.means_of_death: dict[SteamId, dict[str, int]] = {}
        self.match_end_announced: bool = False
        self.previous_positions: dict[SteamId, Position] = {}
        self.round_travelled_distances: dict[SteamId, float] = {}
        self.sightseer_awards: dict[SteamId, int] = {}
        self.picnicker_awards: dict[SteamId, int] = {}
        self.player_stats: dict[SteamId, PlayerStatsEntry] = {}
        self.playerstats_announcements: list[Callable[[list[PlayerStatsEntry]], Optional[str]]] = \
            [most_accurate_railbitches_announcement, longest_shaftlamers_announcement,
             most_honorable_haste_pickup_announcement, weird_facts]

        self.add_hook("frame", self.handle_frame)
        self.add_hook("map", self.handle_map_change)
        self.add_hook("new_game", self.handle_new_game)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("death", self.handle_death)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("stats", self.handle_stats)

    def handle_frame(self) -> None:
        if not self.in_round:
            return

        for player in [player for player in self.players() if player.is_alive and player.team in ["red", "blue"]]:
            distance = self.round_travelled_distances.get(player.steam_id, 0.0)
            self.round_travelled_distances[player.steam_id] = distance + self.calculate_player_distance(player)

            self.previous_positions[player.steam_id] = Position(*player.position())

    def calculate_player_distance(self, player: Player) -> float:
        if not player.is_alive:
            return 0.0

        if player.steam_id not in self.previous_positions:
            return 0.0

        return calculate_distance(
            self.previous_positions[player.steam_id],
            Position(*player.position()))

    def handle_map_change(self, _mapname: str, _factory: str) -> None:
        self.reinitialize_game()

    def reinitialize_game(self) -> None:
        self.in_round = False
        self.game_ended = False
        self.means_of_death = {}
        self.match_end_announced = False
        self.player_stats = {}
        self.sightseer_awards = {}
        self.picnicker_awards = {}
        self.previous_positions = {}
        self.round_travelled_distances = {}

    def handle_new_game(self) -> None:
        self.reinitialize_game()

    def handle_round_start(self, _round_number: int) -> None:
        self.in_round = True
        self.game_ended = False
        self.match_end_announced = False
        self.round_travelled_distances = {}
        self.previous_positions = {player.steam_id: Position(*player.position())
                                   for player in self.players() if player.is_alive}

    def handle_death(self, victim: Player, killer: Player, data: dict) -> None:
        if not self.game or self.game.state != "in_progress":
            return

        if data["MOD"] == "SWITCHTEAM":
            return

        if killer is not None and victim is not None and victim.steam_id == killer.steam_id:
            return

        if victim is None:
            return

        means_of_death = determine_means_of_death(data["MOD"])
        if victim.steam_id not in self.means_of_death:
            self.means_of_death[victim.steam_id] = {}
        self.means_of_death[victim.steam_id][means_of_death] = \
            self.means_of_death[victim.steam_id].get(means_of_death, 0) + 1

    def handle_round_end(self, _data: dict) -> None:
        self.in_round = False

        if len(self.round_travelled_distances) == 0:
            return

        farthest_traveller_sid = max(self.round_travelled_distances,
                                     key=self.round_travelled_distances.get)  # type: ignore
        sightseer_awards = self.round_end_award_announcement_for(farthest_traveller_sid, "sightseer")
        if sightseer_awards is not None:
            self.msg(sightseer_awards)

        shortest_travelled_sid = min(self.round_travelled_distances,
                                     key=self.round_travelled_distances.get)  # type: ignore
        picnicker_awards = self.round_end_award_announcement_for(shortest_travelled_sid, "picnicker")

        teams = self.teams()
        if len(teams["red"] + teams["blue"]) == 2:
            return

        if picnicker_awards is not None:
            self.msg(picnicker_awards)

    Awards = Literal["sightseer", "picnicker"]

    def round_end_award_announcement_for(self, steam_id: SteamId, award: Awards) -> Optional[str]:
        if award not in ["sightseer", "picnicker"]:
            return None

        travelled_distance = self.round_travelled_distances[steam_id]
        same_distance_travellers = [_steam_id for
                                    _steam_id, _travelled_distance in self.round_travelled_distances.items()
                                    if _travelled_distance == travelled_distance]

        for _steam_id in same_distance_travellers:
            collected_awards = getattr(self, f"{award}_awards")
            collected_awards[_steam_id] = collected_awards.get(steam_id, 0) + 1

        return f"  ^5{award[0].upper()}{award[1:].lower()} award^7: " \
               f"{self.format_player_names(same_distance_travellers)}^7 " \
               f"^5{format_float(travelled_distance)}^7 units"

    def format_player_names(self, players: list[SteamId]) -> str:
        return "^7, ".join([self.player(steam_id).name for steam_id in players if self.player(steam_id) is not None])

    @minqlx.delay(3)
    def handle_game_end(self, _data: dict) -> None:
        self.game_ended = True
        self.announce_match_end_stats()

    def handle_stats(self, stats: dict) -> None:
        if stats["TYPE"] != "PLAYER_STATS":
            return

        player_stats = PlayerStatsEntry(stats)

        if player_stats.warmup:
            return

        if player_stats.aborted:
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

        for sightseer_award_announcement in self.game_end_awards_announcement_for("sightseer"):
            self.msg(sightseer_award_announcement)

        if len(self.picnicker_awards.keys()) > 2:
            for picnicker_award_announcement in self.game_end_awards_announcement_for("picnicker"):
                self.msg(picnicker_award_announcement)

        most_environmental_deaths_announcement = \
            self.environmental_deaths(self.means_of_death, ["void", "acid", "drowning", "squished"])
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

    def game_end_awards_announcement_for(self, award: Awards) -> list[str]:
        if award not in ["sightseer", "picnicker"]:
            return []

        awards = getattr(self, f"{award}_awards")
        if len(awards) == 0:
            return []

        grouped_awards = itertools.groupby(sorted(awards, key=awards.get, reverse=True), key=awards.get)

        returned = [f"  ^5{award[0].upper()}{award[1:]} awards:"]

        counter = 1
        for award_count, grouped_steam_ids in grouped_awards:
            prefix = f"^5{counter:2}^7."

            for steam_id in grouped_steam_ids:
                counter += 1
                player = self.player(steam_id)
                if player is not None:
                    returned.append(f"  {prefix} {player.name}^7 (^5{award_count}^7 rounds)")
                else:
                    returned.append(f"  {prefix} {steam_id}^7 (^5{award_count}^7 rounds)")

                prefix = "   "

        return returned

    def environmental_deaths(self, means_of_death: dict[SteamId, dict[str, int]], means_of_death_filter: list[str]) \
            -> str:
        filtered_means_of_death: dict[SteamId, int] = {}
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
               f"^5({filtered_means_of_death[most_environmental_deaths]})^7"
