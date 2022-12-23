import re as _re
import importlib

from ._minqlx import DEBUG, RET_NONE, RET_STOP, RET_STOP_EVENT, RET_STOP_ALL, RET_USAGE, PRI_HIGHEST, PRI_HIGH, \
    PRI_NORMAL, PRI_LOW, PRI_LOWEST, CVAR_ARCHIVE, CVAR_USERINFO, CVAR_SERVERINFO, CVAR_SYSTEMINFO, CVAR_INIT, \
    CVAR_LATCH, CVAR_ROM, CVAR_USER_CREATED, CVAR_TEMP, CVAR_CHEAT, CVAR_NORESTART, PRIV_NONE, PRIV_MOD, PRIV_ADMIN, \
    PRIV_ROOT, PRIV_BANNED, CS_FREE, CS_ZOMBIE, CS_CONNECTED, CS_PRIMED, CS_ACTIVE, TEAM_FREE, TEAM_RED, TEAM_BLUE, \
    TEAM_SPECTATOR, MOD_UNKNOWN, MOD_SHOTGUN, MOD_GAUNTLET, MOD_MACHINEGUN, MOD_GRENADE, MOD_GRENADE_SPLASH, \
    MOD_ROCKET, MOD_ROCKET_SPLASH, MOD_PLASMA, MOD_PLASMA_SPLASH, MOD_RAILGUN, MOD_LIGHTNING, MOD_BFG, MOD_BFG_SPLASH, \
    MOD_WATER, MOD_SLIME, MOD_LAVA, MOD_CRUSH, MOD_TELEFRAG, MOD_FALLING, MOD_SUICIDE, MOD_TARGET_LASER, \
    MOD_TRIGGER_HURT, MOD_NAIL, MOD_CHAINGUN, MOD_PROXIMITY_MINE, MOD_KAMIKAZE, MOD_JUICED, MOD_GRAPPLE, \
    MOD_SWITCH_TEAMS, MOD_THAW, MOD_LIGHTNING_DISCHARGE, MOD_HMG, MOD_RAILGUN_HEADSHOT, Vector3, Flight, Powerups, \
    Weapons, PlayerInfo, PlayerState, PlayerStats, player_info, players_info, get_userinfo, send_server_command, \
    client_command, console_command, get_cvar, set_cvar, set_cvar_limit, kick, console_print, get_configstring, \
    set_configstring, force_vote, add_console_command, player_state, player_stats, set_position, set_velocity, noclip, \
    set_health, set_armor, set_weapons, set_weapon, set_ammo, set_powerups, set_holdable, drop_holdable, set_flight, \
    set_invulnerability, set_score, callvote, allow_single_player, player_spawn, set_privileges, \
    destroy_kamikaze_timers, spawn_item, remove_dropped_items, slay_with_mod, replace_items, dev_print_items, \
    force_weapon_respawn_time, register_handler
from ._core import PluginLoadError, PluginUnloadError, TEAMS, GAMETYPES, GAMETYPES_SHORT, CONNECTION_STATES, WEAPONS, \
    DEFAULT_PLUGINS, parse_variables, get_logger, log_exception, handle_exception, threading_excepthook, uptime, \
    owner, stats_listener, set_cvar_once, set_cvar_limit_once, set_plugins_version, set_map_subtitles, next_frame, \
    delay, thread, load_preset_plugins, load_plugin, unload_plugin, reload_plugin, initialize_cvars, initialize, \
    late_init
from ._game import Game, NonexistentGameError
from ._player import Player, NonexistentPlayerError, AbstractDummyPlayer, RconDummyPlayer
from ._plugin import Plugin
from ._events import EventDispatcher, EventDispatcherManager, ConsolePrintDispatcher, CommandDispatcher, \
    ClientCommandDispatcher, ServerCommandDispatcher, FrameEventDispatcher, SetConfigstringDispatcher, \
    ChatEventDispatcher, UnloadDispatcher, PlayerConnectDispatcher, PlayerLoadedDispatcher, PlayerDisonnectDispatcher, \
    PlayerSpawnDispatcher, StatsDispatcher, VoteCalledDispatcher, VoteStartedDispatcher, VoteEndedDispatcher, \
    VoteDispatcher, GameCountdownDispatcher, GameStartDispatcher, GameEndDispatcher, RoundCountdownDispatcher, \
    RoundStartDispatcher, RoundEndDispatcher, TeamSwitchDispatcher, TeamSwitchAttemptDispatcher, MapDispatcher, \
    NewGameDispatcher, KillDispatcher, DeathDispatcher, UserinfoDispatcher, KamikazeUseDispatcher, \
    KamikazeExplodeDispatcher, PlayerInactivityKickDispatcher, PlayerInactivityKickWarningDispatcher, \
    PlayerItemsTossDispatcher, EVENT_DISPATCHERS
from ._handlers import frame_tasks, next_frame_tasks, handle_rcon, handle_client_command, handle_server_command, \
    handle_frame, handle_new_game, handle_set_configstring, handle_player_connect, handle_player_loaded, \
    handle_player_disconnect, handle_player_spawn, handle_kamikaze_use, handle_kamikaze_explode, handle_console_print, \
    redirect_print, register_handlers
from ._commands import MAX_MSG_LENGTH, re_color_tag, AbstractChannel, ChatChannel, RedTeamChatChannel, \
    BlueTeamChatChannel, FreeChatChannel, SpectatorChatChannel, TellChannel, ConsoleChannel, ClientCommandChannel, \
    Command, CommandInvoker, COMMANDS, CHAT_CHANNEL, RED_TEAM_CHAT_CHANNEL, BLUE_TEAM_CHAT_CHANNEL, FREE_CHAT_CHANNEL, \
    SPECTATOR_CHAT_CHANNEL, CONSOLE_CHANNEL
from ._zmq import StatsListener

try:
    _minqlx = importlib.import_module(name="_minqlx")
    from _minqlx import *
except ModuleNotFoundError:
    _minqlx = importlib.import_module(name="._minqlx", package="minqlx")
    from ._minqlx import *

__version__ = _minqlx.__version__
__plugins_version__ = "NOT_SET"

_map_title = ""
_map_subtitle1 = ""
_map_subtitle2 = ""

temp = _re.search(r"(\d+)\.(\d+)\.(\d+)", __version__)
if temp is None:
    __version_info__ = (999, 999, 999)
else:
    # noinspection PyBroadException
    try:
        __version_info__ = int(temp.group(1)), int(temp.group(2)), int(temp.group(3))
    except:  # pylint: disable=bare-except
        __version_info__ = (999, 999, 999)
del temp

# Put everything into a single module.
__all__ = [
    "__version__", "__version_info__", "__plugins_version__",
    # _minqlx
    "DEBUG", "RET_NONE", "RET_STOP", "RET_STOP_EVENT", "RET_STOP_ALL", "RET_USAGE", "PRI_HIGHEST", "PRI_HIGH",
    "PRI_NORMAL", "PRI_LOW", "PRI_LOWEST", "CVAR_ARCHIVE", "CVAR_USERINFO", "CVAR_SERVERINFO", "CVAR_SYSTEMINFO",
    "CVAR_INIT", "CVAR_LATCH", "CVAR_ROM", "CVAR_USER_CREATED", "CVAR_TEMP", "CVAR_CHEAT", "CVAR_NORESTART",
    "PRIV_NONE", "PRIV_MOD", "PRIV_ADMIN", "PRIV_ROOT", "PRIV_BANNED", "CS_FREE", "CS_ZOMBIE", "CS_CONNECTED",
    "CS_PRIMED", "CS_ACTIVE", "TEAM_FREE", "TEAM_RED", "TEAM_BLUE", "TEAM_SPECTATOR", "MOD_UNKNOWN", "MOD_SHOTGUN",
    "MOD_GAUNTLET", "MOD_MACHINEGUN", "MOD_GRENADE", "MOD_GRENADE_SPLASH", "MOD_ROCKET", "MOD_ROCKET_SPLASH",
    "MOD_PLASMA", "MOD_PLASMA_SPLASH", "MOD_RAILGUN", "MOD_LIGHTNING", "MOD_BFG", "MOD_BFG_SPLASH", "MOD_WATER",
    "MOD_SLIME", "MOD_LAVA", "MOD_CRUSH", "MOD_TELEFRAG", "MOD_FALLING", "MOD_SUICIDE", "MOD_TARGET_LASER",
    "MOD_TRIGGER_HURT", "MOD_NAIL", "MOD_CHAINGUN", "MOD_PROXIMITY_MINE", "MOD_KAMIKAZE", "MOD_JUICED", "MOD_GRAPPLE",
    "MOD_SWITCH_TEAMS", "MOD_THAW", "MOD_LIGHTNING_DISCHARGE", "MOD_HMG", "MOD_RAILGUN_HEADSHOT", "Vector3", "Flight",
    "Powerups", "Weapons", "PlayerInfo", "PlayerState", "PlayerStats", "player_info", "players_info", "get_userinfo",
    "send_server_command", "client_command", "console_command", "get_cvar", "set_cvar", "set_cvar_limit", "kick",
    "console_print", "get_configstring", "set_configstring", "force_vote", "add_console_command", "player_state",
    "player_stats", "set_position", "set_velocity", "noclip", "set_health", "set_armor", "set_weapons", "set_weapon",
    "set_ammo", "set_powerups", "set_holdable", "drop_holdable", "set_flight", "set_invulnerability", "set_score",
    "callvote", "allow_single_player", "player_spawn", "set_privileges", "destroy_kamikaze_timers", "spawn_item",
    "remove_dropped_items", "slay_with_mod", "replace_items", "dev_print_items", "force_weapon_respawn_time",
    "register_handler",
    # _core
    "PluginLoadError", "PluginUnloadError", "TEAMS", "GAMETYPES", "GAMETYPES_SHORT", "CONNECTION_STATES", "WEAPONS",
    "DEFAULT_PLUGINS", "parse_variables", "get_logger", "log_exception", "handle_exception", "threading_excepthook",
    "uptime", "owner", "stats_listener", "set_cvar_once", "set_cvar_limit_once", "set_plugins_version",
    "set_map_subtitles", "next_frame", "delay", "thread", "load_preset_plugins", "load_plugin", "unload_plugin",
    "reload_plugin", "initialize_cvars", "initialize", "late_init",
    # _plugin, _game
    "Plugin", "Game", "NonexistentGameError",
    # _player
    "Player", "NonexistentPlayerError", "AbstractDummyPlayer", "RconDummyPlayer",
    # _commands
    "MAX_MSG_LENGTH", "re_color_tag", "AbstractChannel", "ChatChannel", "RedTeamChatChannel", "BlueTeamChatChannel",
    "FreeChatChannel", "SpectatorChatChannel", "TellChannel", "ConsoleChannel", "ClientCommandChannel", "Command",
    "CommandInvoker", "COMMANDS", "CHAT_CHANNEL", "RED_TEAM_CHAT_CHANNEL", "BLUE_TEAM_CHAT_CHANNEL",
    "FREE_CHAT_CHANNEL", "SPECTATOR_CHAT_CHANNEL", "CONSOLE_CHANNEL",
    # _events
    "EventDispatcher", "EventDispatcherManager", "ConsolePrintDispatcher", "CommandDispatcher",
    "ClientCommandDispatcher", "ServerCommandDispatcher", "FrameEventDispatcher", "SetConfigstringDispatcher",
    "ChatEventDispatcher", "UnloadDispatcher", "PlayerConnectDispatcher", "PlayerLoadedDispatcher",
    "PlayerDisonnectDispatcher", "PlayerSpawnDispatcher", "StatsDispatcher", "VoteCalledDispatcher",
    "VoteStartedDispatcher", "VoteEndedDispatcher", "VoteDispatcher", "GameCountdownDispatcher", "GameStartDispatcher",
    "GameEndDispatcher", "RoundCountdownDispatcher", "RoundStartDispatcher", "RoundEndDispatcher",
    "TeamSwitchDispatcher", "TeamSwitchAttemptDispatcher", "MapDispatcher", "NewGameDispatcher", "KillDispatcher",
    "DeathDispatcher", "UserinfoDispatcher", "KamikazeUseDispatcher", "KamikazeExplodeDispatcher",
    "PlayerInactivityKickDispatcher", "PlayerInactivityKickWarningDispatcher", "PlayerItemsTossDispatcher",
    "EVENT_DISPATCHERS",
    # _handlers
    "frame_tasks", "next_frame_tasks", "handle_rcon", "handle_client_command", "handle_server_command", "handle_frame",
    "handle_new_game", "handle_set_configstring", "handle_player_connect", "handle_player_loaded",
    "handle_player_disconnect", "handle_player_spawn", "handle_kamikaze_use", "handle_kamikaze_explode",
    "handle_console_print", "redirect_print", "register_handlers",
    # _zmq
    "StatsListener",
]
