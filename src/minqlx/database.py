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
import redis
import minqlx


# ====================================================================
#                          AbstractDatabase
# ====================================================================
# noinspection PyProtectedMember
class AbstractDatabase:
    # An instance counter. Useful for closing connections.
    _counter = 0

    def __init__(self, plugin):
        self.plugin = plugin
        self.__class__._counter += 1

    def __del__(self):
        self.__class__._counter -= 1

    @property
    def logger(self):
        return minqlx.get_logger(self.plugin)

    def set_permission(self, player, level):
        """Abstract method. Should set the permission of a player.

        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def get_permission(self, player):
        """Abstract method. Should return the permission of a player.

        :returns: int
        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def has_permission(self, player, level=5):
        """Abstract method. Should return whether or not a player has more than or equal
        to a certain permission level. Should only take a value of 0 to 5, where 0 is
        always True.

        :returns: bool
        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def set_flag(self, player, flag, value=True):
        """Abstract method. Should set specified player flag to value.

        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def clear_flag(self, player, flag):
        """Should clear specified player flag."""
        return self.set_flag(player, flag, False)

    def get_flag(self, player, flag, default=False):
        """Abstract method. Should return specified player flag

        :returns: bool
        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def connect(self):
        """Abstract method. Should return a connection to the database. Exactly what a
        "connection" obviously depends on the database, so the specifics will be up
        to the implementation.

        A :class:`minqlx.Plugin` subclass can set

        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")

    def close(self):
        """Abstract method. If the database has a connection state, this method should
        close the connection.

        :raises: NotImplementedError

        """
        raise NotImplementedError("The base plugin can't do database actions.")


# ====================================================================
#                               Redis
# ====================================================================
# noinspection PyProtectedMember
class Redis(AbstractDatabase):
    """A subclass of :class:`minqlx.AbstractDatabase` providing support for Redis."""

    # We only use the instance-level ones if we override the URI from the config.
    _conn = None
    _pool = None
    _pass = ""

    def __del__(self):
        super().__del__()
        self.close()

    def __contains__(self, key):
        return self.r.exists(key)

    def __getitem__(self, key):
        res = self.r.get(key)
        if res is None:
            raise KeyError(f"The key '{key}' is not present in the database.")
        return res

    def __setitem__(self, key, item):
        res = self.r.set(key, item)
        if res is False:
            raise RuntimeError("The database assignment failed.")

    def __delitem__(self, key):
        res = self.r.delete(key)
        if res == 0:
            raise KeyError(f"The key '{key}' is not present in the database.")

    def __getattr__(self, attr):
        return getattr(self.r, attr)

    @property
    def r(self):
        return self.connect()

    def set_permission(self, player, level):
        """Sets the permission of a player.

        :param: player: The player in question.
        :type: player: minqlx.Player

        """
        if isinstance(player, minqlx.Player):
            key = f"minqlx:players:{player.steam_id}:permission"
        else:
            key = f"minqlx:players:{player}:permission"

        self[key] = level

    def get_permission(self, player):
        """Gets the permission of a player.

        :param: player: The player in question.
        :type: player: minqlx.Player, int
        :returns: int

        """
        if isinstance(player, minqlx.Player):
            steam_id = player.steam_id
        elif isinstance(player, int):
            steam_id = player
        elif isinstance(player, str):
            steam_id = int(player)
        else:
            raise ValueError("Invalid player. Use either a minqlx.Player instance or a SteamID64.")

        # If it's the owner, treat it like a 5.
        if steam_id == minqlx.owner():
            return 5

        key = f"minqlx:players:{steam_id}:permission"
        try:
            perm = self[key]
        except KeyError:
            perm = "0"

        return int(perm)

    def has_permission(self, player, level=5):
        """Checks if the player has higher than or equal to *level*.

        :param: player: The player in question.
        :type: player: minqlx.Player
        :param: level: The permission level to check for.
        :type: level: int
        :returns: bool

        """
        return self.get_permission(player) >= level

    def set_flag(self, player, flag, value=True):
        """Sets specified player flag

        :param: player: The player in question.
        :type: player: minqlx.Player
        :param: flag: The flag to set.
        :type: flag: string
        :param: value: (optional, default=True) Value to set
        :type: value: bool

        """
        if isinstance(player, minqlx.Player):
            key = f"minqlx:players:{player.steam_id}:flags:{flag}"
        else:
            key = f"minqlx:players:{player}:flags:{flag}"

        self[key] = 1 if value else 0

    def get_flag(self, player, flag, default=False):
        """Clears the specified player flag

        :param: player: The player in question.
        :type: player: minqlx.Player
        :param: flag: The flag to get
        :type: flag: string
        :param: default: (optional, default=False) The value to return if the flag is unknown
        :type: default: bool

        """
        if isinstance(player, minqlx.Player):
            key = f"minqlx:players:{player.steam_id}:flags:{flag}"
        else:
            key = f"minqlx:players:{player}:flags:{flag}"

        try:
            return bool(int(self[key]))
        except KeyError:
            return default

    def connect(self, host=None, database=0, unix_socket=False, password=None):
        """Returns a connection to a Redis database. If *host* is None, it will
        fall back to the settings in the config and ignore the rest of the arguments.
        It will also share the connection across any plugins using the default
        configuration. Passing *host* will make it connect to a specific database
        that is not shared at all. Subsequent calls to this will return the connection
        initialized the first call unless it has been closed.

        :param: host: The host name. If no port is specified, it will use 6379. Ex.: ``localhost:1234``.
        :type: host: str
        :param: database: The database number that should be used.
        :type: database: int
        :param: unix_socket: Whether or not *host* should be interpreted as a unix socket path.
        :type: unix_socket: bool
        :raises: RuntimeError

        """
        if not host and not self._conn:  # Resort to default settings in config?
            if not Redis._conn:
                cvar_host = minqlx.get_cvar("qlx_redisAddress")
                if cvar_host is None:
                    raise ValueError("cvar qlx_redisAddress misconfigured")
                redis_db_cvar = minqlx.get_cvar("qlx_redisDatabase")
                if redis_db_cvar is None:
                    raise ValueError("cvar qlx_redisDatabase misconfigured.")
                cvar_db = int(redis_db_cvar)
                unix_socket_cvar = minqlx.get_cvar("qlx_redisUnixSocket")
                if unix_socket_cvar is None:
                    raise ValueError("cvar qlx_redisUnixSocket misconfigured")
                cvar_unixsocket = bool(int(unix_socket_cvar))
                password_cvar = minqlx.get_cvar("qlx_redisPassword")
                if password_cvar is None:
                    raise ValueError("cvar qlx_redisPassword misconfigured")
                Redis._pass = password_cvar
                if cvar_unixsocket:
                    Redis._conn = redis.StrictRedis(
                        unix_socket_path=cvar_host,
                        db=cvar_db,
                        password=Redis._pass,
                        decode_responses=True,
                    )
                else:
                    split_host = cvar_host.split(":")
                    if len(split_host) > 1:
                        port = int(split_host[1])
                    else:
                        port = 6379  # Default port.
                    Redis._pool = redis.ConnectionPool(
                        host=split_host[0],
                        port=port,
                        db=cvar_db,
                        password=Redis._pass,
                        decode_responses=True,
                    )
                    Redis._conn = redis.StrictRedis(connection_pool=Redis._pool, decode_responses=True)
                    # TODO: Why does self._conn get set when doing Redis._conn?
                    self._conn = None
            return Redis._conn
        if not self._conn:
            if host is None:
                raise ValueError("wrong host")
            split_host = host.split(":")
            if len(split_host) > 1:
                port = int(split_host[1])
            else:
                port = 6379  # Default port.

            if unix_socket:
                self._conn = redis.StrictRedis(
                    unix_socket_path=host,
                    db=database,
                    password=password,
                    decode_responses=True,
                )
            else:
                self._pool = redis.ConnectionPool(
                    host=split_host[0],
                    port=port,
                    db=database,
                    password=password,
                    decode_responses=True,
                )
                self._conn = redis.StrictRedis(connection_pool=self._pool, decode_responses=True)
        return self._conn

    def close(self):
        """Close the Redis connection if the config was overridden. Otherwise only do so
        if this is the last plugin using the default connection.

        """
        if self._conn:
            self._conn = None
            if self._pool:
                self._pool.disconnect()
                self._pool = None

        if Redis._counter <= 1 and Redis._conn:
            Redis._conn = None
            if Redis._pool:
                Redis._pool.disconnect()
                Redis._pool = None
