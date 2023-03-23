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
import re
from abc import abstractmethod

import minqlx


MAX_MSG_LENGTH = 1000
re_color_tag = re.compile(r"\^[^\^]")


# ====================================================================
#                             CHANNELS
# ====================================================================
class AbstractChannel:
    """An abstract class of a chat channel. A chat channel being a source of a message.

    Chat channels must implement reply(), since that's the whole point of having a chat channel
    as a class. Makes it quite convenient when dealing with commands and such, while allowing
    people to implement their own channels, opening the possibilites for communication with the
    bot through other means than just chat and console (e.g. web interface).

    Say "ChatChannelA" and "ChatChannelB" are both subclasses of this, and "cca" and "ccb" are instances,
    the default implementation of "cca == ccb" is comparing __repr__(). However, when you register
    a command and list what channels you want it to work with, it'll use this class' __str__(). It's
    important to keep this in mind if you make a subclass. Say you have a web interface that
    supports multiple users on it simulaneously. The right way would be to set "name" to something
    like "webinterface", and then implement a __repr__() to return something like "webinterface user1".

    """

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    # Equal.
    def __eq__(self, other):
        if isinstance(other, str):
            # For string comparison, we use self.name. This allows
            # stuff like: if channel == "tell": do_something()
            return self.name == other
        return repr(self) == repr(other)

    # Not equal.
    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self):
        return self._name

    def reply(self, msg, limit=100, delimiter=" "):
        raise NotImplementedError()

    # noinspection PyMethodMayBeStatic
    def split_long_lines(self, msg, limit=100, delimiter=" "):
        res = []

        while msg:
            i = msg.find("\n")
            if 0 <= i <= limit:
                res.append(msg[:i])
                msg = msg[i + 1:]
                continue

            if len(msg) < limit:
                if msg:
                    res.append(msg)
                break

            length = 0
            while True:
                i = msg[length:].find(delimiter)
                if i == -1 or i + length > limit:
                    if not length:
                        length = limit + 1
                    res.append(msg[: length - 1])
                    msg = msg[length + len(delimiter) - 1:]
                    break
                length += i + 1

        return res


class ChatChannel(AbstractChannel):
    """A channel for chat to and from the server."""

    def __init__(self, name="chat", fmt='print "{}\n"\n'):
        super().__init__(name)
        self.fmt = fmt

    @abstractmethod
    def receipients(self):
        pass

    @minqlx.next_frame
    def reply(self, msg, limit=100, delimiter=" "):
        # We convert whatever we got to a string and replace all double quotes
        # to single quotes, since the engine doesn't support escaping them.
        # TODO: rcon can print quotes to clients using NET_OutOfBandPrint. Maybe we should too?
        msg = str(msg).replace('"', "'")
        # Can deal with all the below ChatChannel subclasses.
        last_color = ""
        targets = self.receipients()

        split_msgs = self.split_long_lines(msg, limit, delimiter)
        # We've split messages, but we can still just join them up to 1000-ish
        # bytes before we need to send multiple server cmds.
        joined_msgs: list[str] = []
        for s in split_msgs:
            if len(joined_msgs) == 0:
                joined_msgs.append(s)
            else:
                s_new = joined_msgs[-1] + "\n" + s
                if len(s_new.encode(errors="replace")) > MAX_MSG_LENGTH:
                    joined_msgs.append(s)
                else:
                    joined_msgs[-1] = s_new

        for s in joined_msgs:
            if not targets:
                minqlx.send_server_command(None, self.fmt.format(last_color + s))
            else:
                for cid in targets:
                    minqlx.send_server_command(cid, self.fmt.format(last_color + s))

            find = re_color_tag.findall(s)
            if find:
                last_color = find[-1]


class TeamChatChannel(ChatChannel):
    """A channel for chat to and from the server."""

    def __init__(self, team="all", name="chat", fmt='print "{}\n"\n'):
        super().__init__(name=name, fmt=fmt)
        self.team = team

    def receipients(self):
        if self.team == "all":
            return None

        return [
            player.id
            for player in minqlx.Player.all_players()
            if player.team == self.team
        ]


class TellChannel(ChatChannel):
    """A channel for private in-game messages."""

    def __init__(self, player):
        super().__init__(name="tell", fmt='print "{}\n"\n')
        self.recipient = player

    def __repr__(self):
        player = minqlx.Plugin.player(self.recipient)
        if player is None:
            return ""
        return f"tell {player.steam_id}"

    def receipients(self):
        cid = minqlx.Plugin.client_id(self.recipient)
        if cid is None:
            raise ValueError("Invalid recipient.")
        return [cid]


class ConsoleChannel(AbstractChannel):
    """A channel that prints to the console."""

    def __init__(self):
        super().__init__("console")

    def reply(self, msg, limit=100, delimiter=" "):
        minqlx.console_print(str(msg))


class ClientCommandChannel(AbstractChannel):
    """Wraps a TellChannel, but with its own name."""

    def __init__(self, player):
        super().__init__("client_command")
        self.recipient = player
        self.tell_channel = TellChannel(player)

    def __repr__(self):
        player = minqlx.Plugin.player(self.recipient)
        if player is None:
            return ""

        return f"client_command {player.id}"

    def reply(self, msg, limit=100, delimiter=" "):
        self.tell_channel.reply(msg, limit, delimiter)


# ====================================================================
#                              COMMANDS
# ====================================================================
class Command:
    """A class representing an input-triggered command.

    Has information about the command itself, its usage, when and who to call when
    action should be taken.

    """

    def __init__(
        self,
        plugin,
        name,
        handler,
        permission,
        channels,
        exclude_channels,
        client_cmd_pass,
        client_cmd_perm,
        prefix,
        usage,
    ):
        if not (channels is None or hasattr(channels, "__iter__")):
            raise ValueError("'channels' must be a finite iterable or None.")
        if not (channels is None or hasattr(exclude_channels, "__iter__")):
            raise ValueError("'exclude_channels' must be a finite iterable or None.")
        self.plugin = plugin  # Instance of the owner.

        # Allow a command to have alternative names.
        if isinstance(name, (list, tuple)):
            self.name = [n.lower() for n in name]
        else:
            self.name = [name]
        self.handler = handler
        self.permission = permission
        self.channels = list(channels) if channels is not None else []
        self.exclude_channels = (
            list(exclude_channels) if exclude_channels is not None else []
        )
        self.client_cmd_pass = client_cmd_pass
        self.client_cmd_perm = client_cmd_perm
        self.prefix = prefix
        self.usage = usage

    def execute(self, player, msg, channel):
        logger = minqlx.get_logger(self.plugin)
        logger.debug(
            "%s executed: %s @ %s -> %s",
            player.steam_id,
            self.name[0],
            self.plugin.name,
            channel,
        )
        return self.handler(player, msg.split(), channel)

    def is_eligible_name(self, name):
        if self.prefix:
            prefix = minqlx.get_cvar("qlx_commandPrefix")
            if prefix is None:
                return False
            if not name.startswith(prefix):
                return False
            name = name[len(prefix):]

        return name.lower() in self.name

    def is_eligible_channel(self, channel):
        """Check if a chat channel is one this command should execute in.

        Exclude takes precedence.

        """
        if channel in self.exclude_channels:
            return False
        return not self.channels or channel.name in self.channels

    def is_eligible_player(self, player, is_client_cmd):
        """Check if a player has the rights to execute the command."""
        # Check if config overrides permission.
        perm = self.permission
        client_cmd_perm = self.client_cmd_perm

        if is_client_cmd:
            cvar_client_cmd = minqlx.get_cvar("qlx_ccmd_perm_" + self.name[0])
            if cvar_client_cmd:
                client_cmd_perm = int(cvar_client_cmd)
        else:
            cvar = minqlx.get_cvar("qlx_perm_" + self.name[0])
            if cvar:
                perm = int(cvar)

        if (
            player.steam_id == minqlx.owner()
            or (not is_client_cmd and perm == 0)
            or (is_client_cmd and client_cmd_perm == 0)
        ):
            return True

        if self.plugin.db is None:
            return False

        player_perm = self.plugin.db.get_permission(player)
        if is_client_cmd:
            return player_perm >= client_cmd_perm
        return player_perm >= perm


class CommandInvoker:
    """Holds all commands and executes them whenever we get input and should execute."""

    def __init__(self):
        self._commands: tuple[
            list[Command], list[Command], list[Command], list[Command], list[Command]
        ] = (
            [],
            [],
            [],
            [],
            [],
        )

    @property
    def commands(self):
        c = []
        for cmds in self._commands:
            c.extend(cmds)

        return c

    def add_command(self, command, priority):
        if self.is_registered(command):
            raise ValueError("Attempted to add an already registered command.")

        self._commands[priority].append(command)

    def remove_command(self, command):
        if not self.is_registered(command):
            raise ValueError("Attempted to remove a command that was never added.")

        for priority_level in self._commands:
            for cmd in priority_level.copy():
                if cmd == command:
                    priority_level.remove(cmd)
                    return

    def is_registered(self, command):
        """Check if a command is already registed.

        Commands are unique by (command.name, command.handler).

        """
        for priority_level in self._commands:
            for cmd in priority_level:
                if command.name == cmd.name and command.handler == cmd.handler:
                    return True

        return False

    def handle_input(self, player, msg, channel):
        if not msg.strip():
            return False

        name = msg.strip().split(" ", 1)[0].lower()
        is_client_cmd = channel == "client_command"
        pass_through = True

        for priority_level in self._commands:
            for cmd in priority_level:
                if (
                    cmd.is_eligible_name(name)
                    and cmd.is_eligible_channel(channel)
                    and cmd.is_eligible_player(player, is_client_cmd)
                ):
                    # Client commands will not pass through to the engine unless told to explicitly.
                    # This is to avoid having to return RET_STOP_EVENT just to not get the "unknown cmd" msg.
                    if is_client_cmd:
                        pass_through = cmd.client_cmd_pass

                    # Dispatch "command" and allow people to stop it from being executed.
                    if (
                        minqlx.EVENT_DISPATCHERS["command"].dispatch(player, cmd, msg)
                        is False
                    ):
                        return True

                    res = cmd.execute(player, msg, channel)
                    if res == minqlx.RET_STOP:
                        return False
                    if res == minqlx.RET_STOP_EVENT:
                        pass_through = False
                    elif res == minqlx.RET_STOP_ALL:
                        # C-level dispatchers expect False if it shouldn't go to the engine.
                        return False
                    elif res == minqlx.RET_USAGE and cmd.usage:
                        channel.reply(f"^7Usage: ^6{name} {cmd.usage}")
                    elif res is not None and res != minqlx.RET_NONE:
                        logger = minqlx.get_logger(None)
                        logger.warning(
                            "Command '%s' with handler '%s' returned an unknown return value: %s",
                            cmd.name,
                            cmd.handler.__name__,
                            res,
                        )

        return pass_through


# ====================================================================
#                          MODULE CONSTANTS
# ====================================================================
COMMANDS = CommandInvoker()
CHAT_CHANNEL = TeamChatChannel(team="all", name="chat")
RED_TEAM_CHAT_CHANNEL = TeamChatChannel(team="red", name="red_team_chat")
BLUE_TEAM_CHAT_CHANNEL = TeamChatChannel(team="blue", name="blue_team_chat")
FREE_CHAT_CHANNEL = TeamChatChannel(team="free", name="free_chat")
SPECTATOR_CHAT_CHANNEL = TeamChatChannel(team="spectator", name="spectator_chat")
CONSOLE_CHANNEL = ConsoleChannel()
