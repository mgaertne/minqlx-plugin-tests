# encoding: utf-8

# Variables with simple values

CS_ACTIVE = 4
CS_CONNECTED = 2
CS_FREE = 0
CS_PRIMED = 3
CS_ZOMBIE = 1

CVAR_ARCHIVE = 1
CVAR_CHEAT = 512
CVAR_INIT = 16
CVAR_LATCH = 32
CVAR_NORESTART = 1024
CVAR_ROM = 64
CVAR_SERVERINFO = 4
CVAR_SYSTEMINFO = 8
CVAR_TEMP = 256
CVAR_USERINFO = 2

CVAR_USER_CREATED = 128

DEBUG = False

MOD_BFG = 12

MOD_BFG_SPLASH = 13

MOD_CHAINGUN = 24
MOD_CRUSH = 17
MOD_FALLING = 19
MOD_GAUNTLET = 2
MOD_GRAPPLE = 28
MOD_GRENADE = 4

MOD_GRENADE_SPLASH = 5

MOD_HMG = 32
MOD_JUICED = 27
MOD_KAMIKAZE = 26
MOD_LAVA = 16
MOD_LIGHTNING = 11

MOD_LIGHTNING_DISCHARGE = 31

MOD_MACHINEGUN = 3
MOD_NAIL = 23
MOD_PLASMA = 8

MOD_PLASMA_SPLASH = 9

MOD_PROXIMITY_MINE = 25

MOD_RAILGUN = 10

MOD_RAILGUN_HEADSHOT = 33

MOD_ROCKET = 6

MOD_ROCKET_SPLASH = 7

MOD_SHOTGUN = 1
MOD_SLIME = 15
MOD_SUICIDE = 20

MOD_SWITCH_TEAMS = 29

MOD_TARGET_LASER = 21

MOD_TELEFRAG = 18
MOD_THAW = 30

MOD_TRIGGER_HURT = 22

MOD_UNKNOWN = 0
MOD_WATER = 14

PRIV_ADMIN = 2
PRIV_BANNED = 4294967295
PRIV_MOD = 1
PRIV_NONE = 0
PRIV_ROOT = 3

PRI_HIGH = 1
PRI_HIGHEST = 0
PRI_LOW = 3
PRI_LOWEST = 4
PRI_NORMAL = 2

RET_NONE = 0
RET_STOP = 1

RET_STOP_ALL = 3
RET_STOP_EVENT = 2

RET_USAGE = 4

TEAM_BLUE = 2
TEAM_FREE = 0
TEAM_RED = 1
TEAM_SPECTATOR = 3

__version__ = 'NOT_SET'

# functions

def add_console_command(*args, **kwargs): # real signature unknown
    """ Adds a console command that will be handled by Python code. """
    pass

def allow_single_player(*args, **kwargs): # real signature unknown
    """ Allows or disallows a game with only a single player in it to go on without forfeiting. Useful for race. """
    pass

def callvote(*args, **kwargs): # real signature unknown
    """ Calls a vote as if started by the server and not a player. """
    pass

def client_command(*args, **kwargs): # real signature unknown
    """ Tells the server to process a command from a specific client. """
    pass

def console_command(*args, **kwargs): # real signature unknown
    """ Executes a command as if it was executed from the server console. """
    pass

def console_print(*args, **kwargs): # real signature unknown
    """ Prints text on the console. If used during an RCON command, it will be printed in the player's console. """
    pass

def destroy_kamikaze_timers(*args, **kwargs): # real signature unknown
    """ Removes all current kamikaze timers. """
    pass

def dev_print_items(*args, **kwargs): # real signature unknown
    """ Prints all items and entity numbers to server console. """
    pass

def drop_holdable(*args, **kwargs): # real signature unknown
    """ Drops player's holdable item. """
    pass

def force_vote(*args, **kwargs): # real signature unknown
    """ Forces the current vote to either fail or pass. """
    pass

def force_weapon_respawn_time(*args, **kwargs): # real signature unknown
    """ Force all weapons to have a specified respawn time, overriding custom map respawn times set for them. """
    pass

def get_configstring(*args, **kwargs): # real signature unknown
    """ Get a configstring. """
    pass

def get_cvar(*args, **kwargs): # real signature unknown
    """ Gets a cvar. """
    pass

def get_userinfo(*args, **kwargs): # real signature unknown
    """ Returns a string with a player's userinfo. """
    pass

def kick(*args, **kwargs): # real signature unknown
    """ Kick a player and allowing the admin to supply a reason for it. """
    pass

def noclip(*args, **kwargs): # real signature unknown
    """ Sets noclip for a player. """
    pass

def players_info(*args, **kwargs): # real signature unknown
    """ Returns a list with dictionaries with information about all the players on the server. """
    pass

def player_info(*args, **kwargs): # real signature unknown
    """ Returns a dictionary with information about a player by ID. """
    pass

def player_spawn(*args, **kwargs): # real signature unknown
    """ Allows or disallows a game with only a single player in it to go on without forfeiting. Useful for race. """
    pass

def player_state(*args, **kwargs): # real signature unknown
    """ Get information about the player's state in the game. """
    pass

def player_stats(*args, **kwargs): # real signature unknown
    """ Get some player stats. """
    pass

def register_handler(*args, **kwargs): # real signature unknown
    """ Register an event handler. Can be called more than once per event, but only the last one will work. """
    pass

def remove_dropped_items(*args, **kwargs): # real signature unknown
    """ Removes all dropped items. """
    pass

def replace_items(*args, **kwargs): # real signature unknown
    """ Replaces target entity's item with specified one. """
    pass

def send_server_command(*args, **kwargs): # real signature unknown
    """ Sends a server command to either one specific client or all the clients. """
    pass

def set_ammo(*args, **kwargs): # real signature unknown
    """ Sets a player's ammo. """
    pass

def set_armor(*args, **kwargs): # real signature unknown
    """ Sets a player's armor. """
    pass

def set_configstring(*args, **kwargs): # real signature unknown
    """ Sets a configstring and sends it to all the players on the server. """
    pass

def set_cvar(*args, **kwargs): # real signature unknown
    """ Sets a cvar. """
    pass

def set_cvar_limit(*args, **kwargs): # real signature unknown
    """ Sets a non-string cvar with a minimum and maximum value. """
    pass

def set_flight(*args, **kwargs): # real signature unknown
    """ Sets a player's flight parameters, such as current fuel, max fuel and, so on. """
    pass

def set_health(*args, **kwargs): # real signature unknown
    """ Sets a player's health. """
    pass

def set_holdable(*args, **kwargs): # real signature unknown
    """ Sets a player's holdable item. """
    pass

def set_invulnerability(*args, **kwargs): # real signature unknown
    """ Makes player invulnerable for limited time. """
    pass

def set_position(*args, **kwargs): # real signature unknown
    """ Sets a player's position vector. """
    pass

def set_powerups(*args, **kwargs): # real signature unknown
    """ Sets a player's powerups. """
    pass

def set_privileges(*args, **kwargs): # real signature unknown
    """ Sets a player's privileges. Does not persist. """
    pass

def set_score(*args, **kwargs): # real signature unknown
    """ Sets a player's score. """
    pass

def set_velocity(*args, **kwargs): # real signature unknown
    """ Sets a player's velocity vector. """
    pass

def set_weapon(*args, **kwargs): # real signature unknown
    """ Sets a player's current weapon. """
    pass

def set_weapons(*args, **kwargs): # real signature unknown
    """ Sets a player's weapons. """
    pass

def slay_with_mod(*args, **kwargs): # real signature unknown
    """ Slay player with mean of death. """
    pass

def spawn_item(*args, **kwargs): # real signature unknown
    """ Spawns item with specified coordinates. """
    pass

# classes

class Flight(tuple):
    """ A struct sequence containing parameters for the flight holdable item. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    fuel = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    max_fuel = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    refuel = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    thrust = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


    n_fields = 4
    n_sequence_fields = 4
    n_unnamed_fields = 0


class PlayerInfo(tuple):
    """ Information about a player, such as Steam ID, name, client ID, and whatnot. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    client_id = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's client ID."""

    connection_state = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's connection state."""

    name = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's name."""

    privileges = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's privileges."""

    steam_id = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's 64-bit representation of the Steam ID."""

    team = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's team."""

    userinfo = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's userinfo."""


    n_fields = 7
    n_sequence_fields = 7
    n_unnamed_fields = 0


class PlayerState(tuple):
    """ Information about a player's state in the game. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    ammo = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's weapon ammo."""

    armor = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's armor."""

    flight = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """A struct sequence with flight parameters."""

    health = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's health."""

    holdable = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's holdable item."""

    is_alive = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """Whether the player's alive or not."""

    is_frozen = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """Whether the player is frozen(freezetag)."""

    noclip = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """Whether the player has noclip or not."""

    position = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's position."""

    powerups = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's powerups."""

    velocity = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's velocity."""

    weapon = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The weapon the player is currently using."""

    weapons = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's weapons."""


    n_fields = 13
    n_sequence_fields = 13
    n_unnamed_fields = 0


class PlayerStats(tuple):
    """ A player's score and some basic stats. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    damage_dealt = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's total damage dealt."""

    damage_taken = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's total damage taken."""

    deaths = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's number of deaths."""

    kills = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's number of kills."""

    ping = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's ping."""

    score = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The player's primary score."""

    time = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """The time in milliseconds the player has on a team since the game started."""


    n_fields = 7
    n_sequence_fields = 7
    n_unnamed_fields = 0


class Powerups(tuple):
    """ A struct sequence containing all the powerups in the game. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    battlesuit = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    haste = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    invisibility = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    invulnerability = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    quad = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    regeneration = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


    n_fields = 6
    n_sequence_fields = 6
    n_unnamed_fields = 0


class Vector3(tuple):
    """ A three-dimensional vector. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    x = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    y = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    z = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


    n_fields = 3
    n_sequence_fields = 3
    n_unnamed_fields = 0


class Weapons(tuple):
    """ A struct sequence containing all the weapons in the game. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __reduce__(self, *args, **kwargs): # real signature unknown
        pass

    def __repr__(self, *args, **kwargs): # real signature unknown
        """ Return repr(self). """
        pass

    bfg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    cg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    g = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    gh = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    gl = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    hands = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    hmg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    lg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    mg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    ng = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    pg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    pl = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    rg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    rl = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    sg = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


    n_fields = 15
    n_sequence_fields = 15
    n_unnamed_fields = 0


# variables with complex values

__loader__ = None # (!) real value is ''

__spec__ = None # (!) real value is ''

