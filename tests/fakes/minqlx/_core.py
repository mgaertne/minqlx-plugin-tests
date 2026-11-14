# minqlx - Extends Quake Live's dedicated server with extra functionality and scripting.
# Copyright (C) 2015 Mino <mino@minomino.org>

# This file is part of minqlx.

# minqlx is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# minqlx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with minqlx. If not, see <http://www.gnu.org/licenses/>.

# Reduced to what plugins use at runtime: lookup tables, helpers, and the thread, next_frame and delay decorators.
import collections
import logging
import threading
import traceback
from functools import wraps

import minqlx

TEAMS = {0: "free", 1: "red", 2: "blue", 3: "spectator"}

GAMETYPES = {
    0: "Free for All",
    1: "Duel",
    2: "Race",
    3: "Team Deathmatch",
    4: "Clan Arena",
    5: "Capture the Flag",
    6: "One Flag",
    8: "Harvester",
    9: "Freeze Tag",
    10: "Domination",
    11: "Attack and Defend",
    12: "Red Rover",
}

GAMETYPES_SHORT = {
    0: "ffa",
    1: "duel",
    2: "race",
    3: "tdm",
    4: "ca",
    5: "ctf",
    6: "1f",
    8: "har",
    9: "ft",
    10: "dom",
    11: "ad",
    12: "rr",
}

CONNECTION_STATES = {0: "free", 1: "zombie", 2: "connected", 3: "primed", 4: "active"}

WEAPONS = {
    1: "g",
    2: "mg",
    3: "sg",
    4: "gl",
    5: "rl",
    6: "lg",
    7: "rg",
    8: "pg",
    9: "bfg",
    10: "gh",
    11: "ng",
    12: "pl",
    13: "cg",
    14: "hmg",
    15: "hands",
}

DEFAULT_PLUGINS = (
    "plugin_manager",
    "essentials",
    "motd",
    "permission",
    "ban",
    "silence",
    "clan",
    "names",
    "log",
    "workshop",
)


class PluginLoadError(Exception):
    pass


class PluginUnloadError(Exception):
    pass


def parse_variables(varstr, ordered=False):
    """Parses strings of key-value pairs delimited by "\\" and puts them into a dictionary."""
    res = collections.OrderedDict() if ordered else {}
    if not varstr.strip():
        return res

    _vars = varstr.lstrip("\\").split("\\")
    try:
        for i in range(0, len(_vars), 2):
            res[_vars[i]] = _vars[i + 1]
    except IndexError:
        logger = minqlx.get_logger()
        logger.warning("Uneven number of keys and values: %s", varstr)

    return res


def get_logger(plugin=None):
    if plugin:
        return logging.getLogger("minqlx." + str(plugin))
    return logging.getLogger("minqlx")


def log_exception(plugin=None):
    logger = get_logger(plugin)
    e = traceback.format_exc().rstrip("\n")
    for line in e.split("\n"):
        logger.error(line)


def owner():
    """Returns the SteamID64 of the owner. This is set in the config."""
    # noinspection PyBroadException
    try:
        owner_cvar = minqlx.get_cvar("qlx_owner")
        if owner_cvar is None:
            raise RuntimeError
        sid = int(owner_cvar)
        if sid == -1:
            raise RuntimeError
        return sid
    except:  # noqa: E722
        logger = minqlx.get_logger()
        logger.error("Failed to parse the Owner Steam ID. Make sure it's in SteamID64 format.")
    return None


def set_cvar_once(name, value, flags=0):
    if minqlx.get_cvar(name) is None:
        minqlx.set_cvar(name, value, flags)
        return True

    return False


def set_cvar_limit_once(name, value, minimum, maximum, flags=0):
    if minqlx.get_cvar(name) is None:
        minqlx.set_cvar_limit(name, value, minimum, maximum, flags)
        return True

    return False


def next_frame(func):
    @wraps(func)
    def f(*args, **kwargs):
        minqlx.next_frame_tasks.put((func, args, kwargs), block=False)

    return f


def delay(time):
    """Delay a function call a certain amount of time."""

    def wrap(func):
        @wraps(func)
        def f(*args, **kwargs):
            minqlx.frame_tasks.enter(time, 1, func, args, kwargs)

        return f

    return wrap


_thread_count = 0
_thread_name = "minqlxthread"


def thread(func, force=False):
    """Starts a thread with the function passed as its target."""

    @wraps(func)
    def f(*args, **kwargs):
        if not force and threading.current_thread().name.endswith(_thread_name):
            func(*args, **kwargs)
        else:
            global _thread_count
            name = func.__name__ + f"-{_thread_count!s}-{_thread_name}"
            t = threading.Thread(target=func, name=name, args=args, kwargs=kwargs, daemon=True)
            t.start()
            _thread_count += 1

            return t

    return f
