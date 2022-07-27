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

from __future__ import annotations

from logging import Logger
from typing import List, Dict, Optional, Callable, Tuple, Iterable, Type, Union, Set, overload

import minqlx
from minqlx.database import Redis


class Plugin:
    """The base plugin class.

    Every plugin must inherit this or a subclass of this. It does not support any database
    by itself, but it has a *database* static variable that must be a subclass of the
    abstract class :class:`minqlx.database.AbstractDatabase`. This abstract class requires
    a few methods that deal with permissions. This will make sure that simple plugins that
    only care about permissions can work on any database. Abstraction beyond that is hard,
    so any use of the database past that point will be uncharted territory, meaning the
    plugin will likely be database-specific unless you abstract it yourself.

    Permissions for commands can be overriden in the config. If you have a plugin called
    ``my_plugin`` with a command ``my_command``, you could override its permission
    requirement by adding ``perm_my_command: 3`` under a ``[my_plugin]`` header.
    This allows users to set custom permissions without having to edit the scripts.

    .. warning::
        I/O is the bane of single-threaded applications. You do **not** want blocking operations
        in code called by commands or events. That could make players lag. Helper decorators
        like :func:`minqlx.thread` can be useful.

    """
    # Static dictionary of plugins currently loaded for the purpose of inter-plugin communication.
    _loaded_plugins: Dict[str, Plugin] = {}
    # The database driver class the plugin should use.
    database: Optional[Type[Redis]] = None

    def __init__(self):
        self._hooks: List[Tuple[str, Callable, int]] = []
        self._commands: List[minqlx.Command] = []
        self._db_instance: Optional[Redis] = None

    def __str__(self):
        return self.name

    @property
    def db(self) -> Optional[Redis]:
        """The database instance."""
        if not self.database:
            raise RuntimeError(f"Plugin '{self.name}' does not have a database driver.")
        if not hasattr(self, "_db_instance") or self._db_instance is None:
            self._db_instance = self.database(self)  # pylint: disable=not-callable

        return self._db_instance

    @property
    def name(self) -> str:
        """The name of the plugin."""
        return self.__class__.__name__

    @property
    def plugins(self) -> Dict[str, Plugin]:
        """A dictionary containing plugin names as keys and plugin instances
        as values of all currently loaded plugins.

        """
        return self._loaded_plugins.copy()

    @property
    def hooks(self) -> List[Tuple[str, Callable, int]]:
        """A list of all the hooks this plugin has."""
        if not hasattr(self, "_hooks"):
            self._hooks = []
        return self._hooks.copy()

    @property
    def commands(self) -> List[minqlx.Command]:
        """A list of all the commands this plugin has registered."""
        if not hasattr(self, "_commands"):
            self._commands = []
        return self._commands.copy()

    @property
    def game(self) -> Optional[minqlx.Game]:
        """A Game instance."""
        try:
            return minqlx.Game()
        except minqlx.NonexistentGameError:
            return None

    @property
    def logger(self) -> Logger:
        """An instance of :class:`logging.Logger`, but initialized for this plugin."""
        return minqlx.get_logger(self)

    # TODO: Document plugin methods.
    def add_hook(self, event: str, handler: Callable, priority: int = minqlx.PRI_NORMAL) -> None:
        if not hasattr(self, "_hooks"):
            self._hooks = []

        self._hooks.append((event, handler, priority))
        minqlx.EVENT_DISPATCHERS[event].add_hook(self.name, handler, priority)

    def remove_hook(self, event: str, handler: Callable, priority: int = minqlx.PRI_NORMAL) -> None:
        if not hasattr(self, "_hooks"):
            self._hooks = []
            return

        minqlx.EVENT_DISPATCHERS[event].remove_hook(self.name, handler, priority)
        self._hooks.remove((event, handler, priority))

    def add_command(self, name: Union[str, Tuple[str, ...]], handler: Callable, permission: int = 0,
                    channels: Optional[Iterable[minqlx.AbstractChannel]] = None,
                    exclude_channels: Iterable[minqlx.AbstractChannel] = (), priority: int = minqlx.PRI_NORMAL,
                    client_cmd_pass: bool = False, client_cmd_perm: int = 5, prefix: bool = True, usage: str = ""):
        if not hasattr(self, "_commands"):
            self._commands = []

        cmd = minqlx.Command(self, name, handler, permission, channels, exclude_channels, client_cmd_pass,
                             client_cmd_perm, prefix, usage)
        self._commands.append(cmd)
        minqlx.COMMANDS.add_command(cmd, priority)

    def remove_command(self, name: List[str], handler: Callable):
        if not hasattr(self, "_commands"):
            self._commands = []
            return

        for cmd in self._commands:
            if cmd.name == name and cmd.handler == handler:
                minqlx.COMMANDS.remove_command(cmd)

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[str] = str) -> Optional[str]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[bool]) -> Optional[bool]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[int]) -> Optional[int]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[float]) -> Optional[float]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[list]) -> Optional[List[str]]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[set]) -> Optional[Set[str]]:
        ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[tuple]) -> Optional[Tuple[str, ...]]:
        ...

    @classmethod
    def get_cvar(cls, name: str, return_type: Type[Union[str, bool, int, float, list, set, tuple]] = str) \
            -> Optional[Union[str, bool, int, float, List[str], Set[str], Tuple[str, ...]]]:
        """Gets the value of a cvar as a string.

        :param: name: The name of the cvar.
        :type: name: str
        :param: return_type: The type the cvar should be returned in.
            Supported types: str, int, float, bool, list, tuple

        """
        res = minqlx.get_cvar(name)
        if return_type == str:
            return res
        if return_type == int:
            return int(res) if res else None
        if return_type == float:
            return float(res) if res else None
        if return_type == bool:
            return bool(int(res)) if res else False
        if return_type == list:
            return [s.strip() for s in res.split(",")] if res else []
        if return_type == set:
            return {s.strip() for s in res.split(",")} if res else set()
        if return_type == tuple:
            return ([s.strip() for s in res.split(",")]) if res else ()

        raise ValueError(f"Invalid return type: {return_type}")

    @classmethod
    def set_cvar(cls, name: str, value, flags: int = 0) -> bool:
        """Sets a cvar. If the cvar exists, it will be set as if set from the console,
        otherwise create it.

        :param: name: The name of the cvar.
        :type: name: str
        :param: value: The value of the cvar.
        :type: value: Anything with an __str__ method.
        :param: flags: The flags to set if, and only if, the cvar does not exist and has to be created.
        :type: flags: int
        :returns: True if a new cvar was created, False if an existing cvar was set.
        :rtype: bool

        """
        if cls.get_cvar(name) is None:
            minqlx.set_cvar(name, value, flags)
            return True

        minqlx.console_command(f"{name} \"{value}\"")
        return False

    @classmethod
    def set_cvar_limit(cls, name: str, value: Union[int, float], minimum: Union[int, float],
                       maximum: Union[int, float], flags: int = 0) -> bool:
        """Sets a cvar with upper and lower limits. If the cvar exists, it will be set
        as if set from the console, otherwise create it.

        :param: name: The name of the cvar.
        :type: name: str
        :param: value: The value of the cvar.
        :type: value: int, float
        :param: minimum: The minimum value of the cvar.
        :type: value: int, float
        :param: maximum: The maximum value of the cvar.
        :type: value: int, float
        :param: flags: The flags to set if, and only if, the cvar does not exist and has to be created.
        :type: flags: int
        :returns: True if a new cvar was created, False if an existing cvar was set.
        :rtype: bool

        """
        if cls.get_cvar(name) is None:
            minqlx.set_cvar_limit(name, value, minimum, maximum, flags)
            return True

        minqlx.set_cvar_limit(name, value, minimum, maximum, flags)
        return False

    @classmethod
    def set_cvar_once(cls, name: str, value, flags: int = 0) -> bool:
        """Sets a cvar. If the cvar exists, do nothing.

        :param: name: The name of the cvar.
        :type: name: str
        :param: value: The value of the cvar.
        :type: value: Anything with an __str__ method.
        :param: flags: The flags to set if, and only if, the cvar does not exist and has to be created.
        :type: flags: int
        :returns: True if a new cvar was created, False if an existing cvar was set.
        :rtype: bool

        """
        return minqlx.set_cvar_once(name, value, flags)

    @classmethod
    def set_cvar_limit_once(cls, name: str, value: Union[int, float], minimum: Union[int, float],
                            maximum: Union[int, float], flags: int = 0) -> bool:
        """Sets a cvar with upper and lower limits. If the cvar exists, not do anything.

        :param: name: The name of the cvar.
        :type: name: str
        :param: value: The value of the cvar.
        :type: value: int, float
        :param: minimum: The minimum value of the cvar.
        :type: value: int, float
        :param: maximum: The maximum value of the cvar.
        :type: value: int, float
        :param: flags: The flags to set if, and only if, the cvar does not exist and has to be created.
        :type: flags: int
        :returns: True if a new cvar was created, False if an existing cvar was set.
        :rtype: bool

        """
        return minqlx.set_cvar_limit_once(name, value, minimum, maximum, flags)

    @classmethod
    def players(cls) -> List[minqlx.Player]:
        """Get a list of all the players on the server."""
        return minqlx.Player.all_players()

    @classmethod
    def player(cls, name: Union[str, int, minqlx.Player], player_list: List[minqlx.Player] = None) \
            -> Optional[minqlx.Player]:
        """Get a Player instance from the name, client ID,
        or Steam ID. Assumes [0, 64) to be a client ID
        and [64, inf) to be a Steam ID.

        """
        # In case 'name' isn't a string.
        if isinstance(name, minqlx.Player):
            return name
        if isinstance(name, int) and 0 <= name < 64:
            return minqlx.Player(name)

        if not player_list:
            players = cls.players()
        else:
            players = player_list

        if isinstance(name, int) and name >= 64:
            for p in players:
                if p.steam_id == name:
                    return p
        else:
            cid = cls.client_id(name, players)
            if cid:
                for p in players:
                    if p.id == cid:
                        return p

        return None

    @classmethod
    def msg(cls, msg: str, chat_channel: str = "chat", **kwargs) -> None:
        """Send a message to the chat, or any other channel."""
        if isinstance(chat_channel, minqlx.AbstractChannel):
            chat_channel.reply(msg, **kwargs)
        elif chat_channel == minqlx.CHAT_CHANNEL:
            minqlx.CHAT_CHANNEL.reply(msg, **kwargs)
        elif chat_channel == minqlx.RED_TEAM_CHAT_CHANNEL:
            minqlx.RED_TEAM_CHAT_CHANNEL.reply(msg, **kwargs)
        elif chat_channel == minqlx.BLUE_TEAM_CHAT_CHANNEL:
            minqlx.BLUE_TEAM_CHAT_CHANNEL.reply(msg, **kwargs)
        elif chat_channel == minqlx.CONSOLE_CHANNEL:
            minqlx.CONSOLE_CHANNEL.reply(msg, **kwargs)
        else:
            raise ValueError("Invalid channel.")

    @classmethod
    def console(cls, text: str) -> None:
        """Prints text in the console."""
        minqlx.console_print(str(text))

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Removes color tags from text."""
        return minqlx.re_color_tag.sub("", text)

    @classmethod
    def colored_name(cls, name: Union[str, minqlx.Player], player_list: Optional[List[minqlx.Player]] = None) \
            -> Optional[str]:
        """Get the colored name of a decolored name."""
        if isinstance(name, minqlx.Player):
            return name.name

        if not player_list:
            players = cls.players()
        else:
            players = player_list

        clean = cls.clean_text(name).lower()
        for p in players:
            if p.clean_name.lower() == clean:
                return p.name

        return None

    @classmethod
    def client_id(cls, name: Union[str, int, minqlx.Player], player_list: Optional[List[minqlx.Player]] = None) \
            -> Optional[int]:
        """Get a player's client id from the name, client ID,
        Player instance, or Steam ID. Assumes [0, 64) to be
        a client ID and [64, inf) to be a Steam ID.

        """
        if isinstance(name, int) and 0 <= name < 64:
            return name
        if isinstance(name, minqlx.Player):
            return name.id

        if not player_list:
            players = cls.players()
        else:
            players = player_list

        # Check Steam ID first, then name.
        if isinstance(name, int) and name >= 64:
            for p in players:
                if p.steam_id == name:
                    return p.id

        if isinstance(name, str):
            clean = cls.clean_text(name).lower()
            for p in players:
                if p.clean_name.lower() == clean:
                    return p.id

        return None

    @classmethod
    def find_player(cls, name: str, player_list: Optional[List[minqlx.Player]] = None) -> List[minqlx.Player]:
        """Find a player based on part of a players name.

        :param: name: A part of someone's name.
        :type: name: str
        :returns: A list of players that had that in their names.

        """
        if not player_list:
            players = cls.players()
        else:
            players = player_list

        if not name:
            return players

        res = []
        for p in players:
            if cls.clean_text(name.lower()) in p.clean_name.lower():
                res.append(p)

        return res

    @classmethod
    def teams(cls, player_list: Optional[List[minqlx.Player]] = None) -> Dict[str, List[minqlx.Player]]:
        """Get a dictionary with the teams as keys and players as values."""
        if not player_list:
            players = cls.players()
        else:
            players = player_list

        res: Dict[str, List[minqlx.Player]] = {team_value: [] for team_value in minqlx.TEAMS.values()}

        for p in players:
            res[p.team].append(p)

        return res

    @classmethod
    def center_print(cls, msg: str, recipient: Optional[Union[str, int, minqlx.Player]] = None) -> None:
        client_id: Optional[int] = None
        if recipient:
            client_id = cls.client_id(recipient)

        minqlx.send_server_command(client_id, f"cp \"{msg}\"")

    @classmethod
    def tell(cls, msg: str, recipient: Union[str, int, minqlx.Player], **kwargs) -> None:
        """Send a tell (private message) to someone.

        :param: msg: The message to be sent.
        :type: msg: str
        :param: recipient: The player that should receive the message.
        :type: recipient: str/int/minqlx.Player
        :returns: bool -- True if succeeded, False otherwise.
        :raises: ValueError
        """
        minqlx.TellChannel(recipient).reply(msg, **kwargs)

    @classmethod
    def is_vote_active(cls) -> bool:
        return bool(minqlx.get_configstring(9))

    @classmethod
    def current_vote_count(cls) -> Optional[Tuple[int, int]]:
        yes = minqlx.get_configstring(10)
        no = minqlx.get_configstring(11)
        if yes and no:
            return int(yes), int(no)

        return None

    @classmethod
    def callvote(cls, vote: str, display: str, time: int = 30) -> bool:
        if cls.is_vote_active():
            return False

        # Tell vote_started's dispatcher that it's a vote called by the server.
        minqlx.EVENT_DISPATCHERS["vote_started"].caller(None)
        minqlx.callvote(vote, display, time)
        return True

    @classmethod
    def force_vote(cls, pass_it: bool) -> bool:
        if pass_it is True or pass_it is False:
            return minqlx.force_vote(pass_it)

        raise ValueError("pass_it must be either True or False.")

    @classmethod
    def teamsize(cls, size: int) -> None:
        minqlx.Game().teamsize = size

    @classmethod
    def kick(cls, player: Union[str, int, minqlx.Player], reason: str = "") -> None:
        cid = cls.client_id(player)
        if cid is None:
            raise ValueError("Invalid player.")

        if not reason:
            minqlx.kick(cid, None)
        else:
            minqlx.kick(cid, reason)

    @classmethod
    def shuffle(cls) -> None:
        minqlx.Game().shuffle()

    @classmethod
    def cointoss(cls) -> None:
        # TODO: Call cointoss directly and implement cointoss().
        pass

    @classmethod
    def change_map(cls, new_map: str, factory: str = None) -> None:
        if not factory:
            minqlx.Game().map = new_map
        else:
            minqlx.console_command(f"map {new_map} {factory}")

    @classmethod
    def switch(cls, player: minqlx.Player, other_player: minqlx.Player) -> None:
        p1 = cls.player(player)
        p2 = cls.player(other_player)

        if not p1:
            raise ValueError("The first player is invalid.")
        if not p2:
            raise ValueError("The second player is invalid.")

        t1 = p1.team
        t2 = p2.team

        if t1 == t2:
            raise ValueError("Both players are on the same team.")

        cls.put(p1, t2)
        cls.put(p2, t1)

    @classmethod
    def play_sound(cls, sound_path: str, player: minqlx.Player = None) -> bool:
        if not sound_path or "music/" in sound_path.lower():
            return False

        if player:
            minqlx.send_server_command(player.id, f"playSound {sound_path}")
        else:
            minqlx.send_server_command(None, f"playSound {sound_path}")
        return True

    @classmethod
    def play_music(cls, music_path: str, player: Optional[minqlx.Player] = None) -> bool:
        if not music_path or "sound/" in music_path.lower():
            return False

        if player:
            minqlx.send_server_command(player.id, f"playMusic {music_path}")
        else:
            minqlx.send_server_command(None, f"playMusic {music_path}")
        return True

    @classmethod
    def stop_sound(cls, player: Optional[minqlx.Player] = None) -> None:
        minqlx.send_server_command(player.id if player else None, "clearSounds")

    @classmethod
    def stop_music(cls, player: Optional[minqlx.Player] = None) -> None:
        minqlx.send_server_command(player.id if player else None, "stopMusic")

    @classmethod
    def slap(cls, player: Union[str, int, minqlx.Player], damage: int = 0) -> None:
        cid = cls.client_id(player)
        if cid is None:
            raise ValueError("Invalid player.")

        minqlx.console_command(f"slap {cid} {damage}")

    @classmethod
    def slay(cls, player: Union[str, int, minqlx.Player]) -> None:
        cid = cls.client_id(player)
        if cid is None:
            raise ValueError("Invalid player.")

        minqlx.console_command(f"slay {cid}")

    # ====================================================================
    #                         ADMIN COMMANDS
    # ====================================================================

    @classmethod
    def timeout(cls) -> None:
        minqlx.Game.timeout()

    @classmethod
    def timein(cls) -> None:
        minqlx.Game.timein()

    @classmethod
    def allready(cls) -> None:
        minqlx.Game.allready()

    @classmethod
    def pause(cls) -> None:
        minqlx.Game.pause()

    @classmethod
    def unpause(cls) -> None:
        minqlx.Game.unpause()

    @classmethod
    def lock(cls, team: Optional[str] = None) -> None:
        minqlx.Game.lock(team)

    @classmethod
    def unlock(cls, team: Optional[str] = None) -> None:
        minqlx.Game.unlock(team)

    @classmethod
    def put(cls, player: minqlx.Player, team: str) -> None:
        minqlx.Game.put(player, team)

    @classmethod
    def mute(cls, player: minqlx.Player) -> None:
        minqlx.Game.mute(player)

    @classmethod
    def unmute(cls, player: minqlx.Player) -> None:
        minqlx.Game.unmute(player)

    @classmethod
    def tempban(cls, player: minqlx.Player) -> None:
        # TODO: Add an optional reason to tempban.
        minqlx.Game.tempban(player)

    @classmethod
    def ban(cls, player: minqlx.Player) -> None:
        minqlx.Game.ban(player)

    @classmethod
    def unban(cls, player: minqlx.Player) -> None:
        minqlx.Game.unban(player)

    @classmethod
    def opsay(cls, msg: str) -> None:
        minqlx.Game.opsay(msg)

    @classmethod
    def addadmin(cls, player: minqlx.Player) -> None:
        minqlx.Game.addadmin(player)

    @classmethod
    def addmod(cls, player: minqlx.Player) -> None:
        minqlx.Game.addmod(player)

    @classmethod
    def demote(cls, player: minqlx.Player) -> None:
        minqlx.Game.demote(player)

    @classmethod
    def abort(cls) -> None:
        minqlx.Game.abort()

    @classmethod
    def addscore(cls, player: minqlx.Player, score: int) -> None:
        minqlx.Game.addscore(player, score)

    @classmethod
    def addteamscore(cls, team: str, score: int) -> None:
        minqlx.Game.addteamscore(team, score)

    @classmethod
    def setmatchtime(cls, time: int) -> None:
        minqlx.Game.setmatchtime(time)
