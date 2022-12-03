# encoding: utf-8
from typing import Union, Optional, Callable, List

__version__ = 'NOT_SET'
DEBUG = False


# Variables with simple values
RET_NONE: int = 0
RET_STOP: int = 1
RET_STOP_EVENT: int = 2
RET_STOP_ALL: int = 3
RET_USAGE: int = 4

PRI_HIGHEST: int = 0
PRI_HIGH: int = 1
PRI_NORMAL: int = 2
PRI_LOW: int = 3
PRI_LOWEST: int = 4

# Cvar flags
CVAR_ARCHIVE: int = 1
CVAR_USERINFO: int = 2
CVAR_SERVERINFO: int = 4
CVAR_SYSTEMINFO: int = 8
CVAR_INIT: int = 16
CVAR_LATCH: int = 32
CVAR_ROM: int = 64
CVAR_USER_CREATED: int = 128
CVAR_TEMP: int = 256
CVAR_CHEAT: int = 512
CVAR_NORESTART: int = 1024

# Privileges
PRIV_NONE: int = 0
PRIV_MOD: int = 1
PRIV_ADMIN: int = 2
PRIV_ROOT: int = 3
PRIV_BANNED: int = 4294967295

# Connection states
CS_FREE: int = 0
CS_ZOMBIE: int = 1
CS_CONNECTED: int = 2
CS_PRIMED: int = 3
CS_ACTIVE: int = 4

# Teams
TEAM_FREE: int = 0
TEAM_RED: int = 1
TEAM_BLUE: int = 2
TEAM_SPECTATOR: int = 3

# Means of death
MOD_UNKNOWN: int = 0
MOD_SHOTGUN: int = 1
MOD_GAUNTLET: int = 2
MOD_MACHINEGUN: int = 3
MOD_GRENADE: int = 4
MOD_GRENADE_SPLASH: int = 5
MOD_ROCKET: int = 6
MOD_ROCKET_SPLASH: int = 7
MOD_PLASMA: int = 8
MOD_PLASMA_SPLASH: int = 9
MOD_RAILGUN: int = 10
MOD_LIGHTNING: int = 11
MOD_BFG: int = 12
MOD_BFG_SPLASH: int = 13
MOD_WATER: int = 14
MOD_SLIME: int = 15
MOD_LAVA: int = 16
MOD_CRUSH: int = 17
MOD_TELEFRAG: int = 18
MOD_FALLING: int = 19
MOD_SUICIDE: int = 20
MOD_TARGET_LASER: int = 21
MOD_TRIGGER_HURT: int = 22
MOD_NAIL: int = 23
MOD_CHAINGUN: int = 24
MOD_PROXIMITY_MINE: int = 25
MOD_KAMIKAZE: int = 26
MOD_JUICED: int = 27
MOD_GRAPPLE: int = 28
MOD_SWITCH_TEAMS: int = 29
MOD_THAW: int = 30
MOD_LIGHTNING_DISCHARGE: int = 31
MOD_HMG: int = 32
MOD_RAILGUN_HEADSHOT: int = 33


# classes
class Vector3(tuple):
    """ A three-dimensional vector. """
    x: int
    y: int
    z: int


class Flight(tuple):
    """ A struct sequence containing parameters for the flight holdable item. """
    fuel: int
    max_fuel: int
    thrust: int
    refuel: int


class Powerups(tuple):
    """ A struct sequence containing all the powerups in the game. """
    quad: int
    battlesuit: int
    haste: int
    invisibility: int
    regeneration: int
    invulnerability: int


class Weapons(tuple):
    """ A struct sequence containing all the weapons in the game. """
    g: int
    mg: int
    sg: int
    gl: int
    rl: int
    lg: int
    rg: int
    pg: int
    bfg: int
    gh: int
    ng: int
    pl: int
    cg: int
    hmg: int
    hands: int


class PlayerInfo(tuple):
    """ Information about a player, such as Steam ID, name, client ID, and whatnot. """

    @property
    def client_id(self) -> int:
        """The player's client ID."""
        return self[0]

    @property
    def name(self) -> str:
        """The player's name."""
        return self[1]

    @property
    def connection_state(self) -> int:
        """The player's connection state."""
        return self[2]

    @property
    def userinfo(self) -> str:
        """The player's userinfo    ."""
        return self[3]

    @property
    def steam_id(self) -> int:
        """The player's 64-bit representation of the Steam ID."""
        return self[4]

    @property
    def team(self) -> int:
        """The player's team."""
        return self[5]

    @property
    def privileges(self) -> int:
        """The player's privileges."""
        return self[6]


class PlayerState(tuple):
    """ Information about a player's state in the game. """

    is_alive: bool
    """Whether the player's alive or not."""

    position: Vector3
    """The player's position."""

    velocity: Vector3
    """The player's velocity."""

    health: int
    """The player's health."""

    armor: int
    """The player's armor."""

    noclip: bool
    """Whether the player has noclip or not."""

    weapon: int
    """The weapon the player is currently using."""

    weapons: Weapons
    """The player's weapons."""

    ammo: Weapons
    """The player's weapon ammo."""

    powerups: Powerups
    """The player's powerups."""

    holdable: int
    """The player's holdable item."""

    flight: Flight
    """A struct sequence with flight parameters."""

    is_frozen: bool
    """Whether the player is frozen(freezetag)."""


class PlayerStats(tuple):
    """ A player's score and some basic stats. """
    score: int
    """The player's primary score."""

    kills: int
    """The player's number of kills."""

    deaths: int
    """The player's number of deaths."""

    damage_dealt: int
    """The player's total damage dealt."""

    damage_taken: int
    """The player's total damage taken."""

    time: int
    """The time in milliseconds the player has on a team since the game started."""

    ping: int
    """The player's ping."""


# functions
def player_info(_client_id: int) -> Optional[PlayerInfo]:
    """ Returns a dictionary with information about a player by ID. """


def players_info() -> List[PlayerInfo]:
    """ Returns a list with dictionaries with information about all the players on the server. """


def get_userinfo(_client_id: int) -> Optional[str]:
    """ Returns a string with a player's userinfo. """


def send_server_command(_client_id: Optional[int], _cmd: str) -> Optional[bool]:
    """ Sends a server command to either one specific client or all the clients. """


def client_command(_client_id: int, _cmd: str) -> Optional[bool]:
    """ Tells the server to process a command from a specific client. """


def console_command(_cmd: str) -> None:
    """ Executes a command as if it was executed from the server console. """


def get_cvar(_cvar: str) -> Optional[str]:
    """ Gets a cvar. """


def set_cvar(_cvar: str, _value: str, _flags: Optional[int] = None) -> bool:
    """ Sets a cvar. """


def set_cvar_limit(_name: str, _value: Union[int, float], _min: Union[int, float], _max: Union[int, float],
                   _flags: int) -> None:
    """ Sets a non-string cvar with a minimum and maximum value. """


def kick(_client_id: int, _reason: Optional[str] = None) -> None:
    """ Kick a player and allowing the admin to supply a reason for it. """


def console_print(_text: str) -> None:
    """ Prints text on the console. If used during an RCON command, it will be printed in the player's console. """


def get_configstring(_config_id: int) -> str:
    """ Get a configstring. """


def set_configstring(_config_id: int, _value: str) -> None:
    """ Sets a configstring and sends it to all the players on the server. """


def force_vote(_pass: bool) -> bool:
    """ Forces the current vote to either fail or pass. """


def add_console_command(_command: str) -> None:
    """ Adds a console command that will be handled by Python code. """


def register_handler(_event: str, _handler: Optional[Callable] = None) -> None:
    """ Register an event handler. Can be called more than once per event, but only the last one will work. """


def player_state(_client_id: int) -> Optional[PlayerState]:
    """ Get information about the player's state in the game. """


def player_stats(_client_id: int) -> Optional[PlayerStats]:
    """ Get some player stats. """


def set_position(_client_id: int, _position: Vector3) -> bool:
    """ Sets a player's position vector. """


def set_velocity(_client_id: int, _velocity: Vector3) -> bool:
    """ Sets a player's velocity vector. """


def noclip(_client_id: int, _activate: bool) -> bool:
    """ Sets noclip for a player. """


def set_health(_client_id: int, _health: int) -> bool:
    """ Sets a player's health. """


def set_armor(_client_id: int, _armor: int) -> bool:
    """ Sets a player's armor. """


def set_weapons(_client_id: int, _weapons: Weapons) -> bool:
    """ Sets a player's weapons. """


def set_weapon(_client_id: int, _weapon: int) -> bool:
    """ Sets a player's current weapon. """


def set_ammo(_client_id: int, _ammo: Weapons) -> bool:
    """ Sets a player's ammo. """


def set_powerups(_client_id: int, _powerups: Powerups) -> bool:
    """ Sets a player's powerups. """


def set_holdable(_client_id: int, _powerup: int) -> bool:
    """ Sets a player's holdable item. """


def drop_holdable(_client_id: int) -> bool:
    """ Drops player's holdable item. """


def set_flight(_client_id: int, _flight: Flight) -> bool:
    """ Sets a player's flight parameters, such as current fuel, max fuel and, so on. """


def set_invulnerability(_client_id: int, _time: int) -> bool:
    """ Makes player invulnerable for limited time. """


def set_score(_client_id: int, _score: int) -> bool:
    """ Sets a player's score. """


def callvote(_vote: str, _vote_display: str, _vote_time: Optional[int] = None) -> None:
    """ Calls a vote as if started by the server and not a player. """


def allow_single_player(_allow: bool) -> None:
    """ Allows or disallows a game with only a single player in it to go on without forfeiting. Useful for race. """


def player_spawn(_client_id: int) -> bool:
    """ Allows or disallows a game with only a single player in it to go on without forfeiting. Useful for race. """


def set_privileges(_client_id: int, _privileges: int) -> bool:
    """ Sets a player's privileges. Does not persist. """


def destroy_kamikaze_timers() -> bool:
    """ Removes all current kamikaze timers. """


def spawn_item(_item_id: int, _x: int, _y: int, _z: int) -> bool:
    """ Spawns item with specified coordinates. """


def remove_dropped_items() -> bool:
    """ Removes all dropped items. """


def slay_with_mod(_client_id: int, _mod: int) -> bool:
    """ Slay player with mean of death. """


def replace_items(_item1: Union[int, str], _item2: Union[int, str]) -> bool:
    """ Replaces target entity's item with specified one. """


def dev_print_items() -> None:
    """ Prints all items and entity numbers to server console. """


def force_weapon_respawn_time(_respawn_time: int) -> bool:
    """ Force all weapons to have a specified respawn time, overriding custom map respawn times set for them. """
