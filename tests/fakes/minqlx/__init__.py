"""Test fake of the minqlx interface.

Real logic (commands, event dispatchers, plugin base class, decorators) is kept; everything that needs the Quake Live
server (players, games, database, handlers, zmq) is generated from the stubs in stubs/minqlx and raises
NotImplementedError until a test replaces it.
"""

# ruff: noqa: F401, F403, I001
from . import _minqlx
from ._minqlx import *
from ._core import (
    CONNECTION_STATES,
    DEFAULT_PLUGINS,
    GAMETYPES,
    GAMETYPES_SHORT,
    TEAMS,
    WEAPONS,
    PluginLoadError,
    PluginUnloadError,
    delay,
    get_logger,
    log_exception,
    next_frame,
    owner,
    parse_variables,
    set_cvar_limit_once,
    set_cvar_once,
    thread,
)
from . import database
from ._commands import (
    BLUE_TEAM_CHAT_CHANNEL,
    CHAT_CHANNEL,
    COMMANDS,
    CONSOLE_CHANNEL,
    FREE_CHAT_CHANNEL,
    MAX_MSG_LENGTH,
    RED_TEAM_CHAT_CHANNEL,
    SPECTATOR_CHAT_CHANNEL,
    AbstractChannel,
    ChatChannel,
    ClientCommandChannel,
    Command,
    CommandInvoker,
    ConsoleChannel,
    TeamChatChannel,
    TellChannel,
    re_color_tag,
)
from ._events import (
    EVENT_DISPATCHERS,
    ChatEventDispatcher,
    ClientCommandDispatcher,
    CommandDispatcher,
    ConsolePrintDispatcher,
    DamageDispatcher,
    DeathDispatcher,
    EventDispatcher,
    EventDispatcherManager,
    FrameEventDispatcher,
    GameCountdownDispatcher,
    GameEndDispatcher,
    GameStartDispatcher,
    KamikazeExplodeDispatcher,
    KamikazeUseDispatcher,
    KillDispatcher,
    MapDispatcher,
    NewGameDispatcher,
    PlayerConnectDispatcher,
    PlayerDisconnectDispatcher,
    PlayerLoadedDispatcher,
    PlayerSpawnDispatcher,
    RoundCountdownDispatcher,
    RoundEndDispatcher,
    RoundStartDispatcher,
    ServerCommandDispatcher,
    SetConfigstringDispatcher,
    StatsDispatcher,
    TeamSwitchAttemptDispatcher,
    TeamSwitchDispatcher,
    UnloadDispatcher,
    UserinfoDispatcher,
    VoteCalledDispatcher,
    VoteDispatcher,
    VoteEndedDispatcher,
    VoteStartedDispatcher,
)
from ._game import Game, NonexistentGameError
from ._handlers import frame_tasks, handle_frame, next_frame_tasks
from ._player import AbstractDummyPlayer, NonexistentPlayerError, Player, RconDummyPlayer
from ._plugin import Plugin
from ._testing import join_minqlx_threads, reset_registrations, run_delayed_tasks, run_next_frame_tasks

__version__ = _minqlx.__version__
__version_info__ = (999, 999, 999)
__plugins_version__ = "NOT_SET"
