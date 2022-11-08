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

import minqlx

_DUMMY_USERINFO = ("ui_singlePlayerActive\\0\\cg_autoAction\\1\\cg_autoHop\\0"
                   "\\cg_predictItems\\1\\model\\bitterman/sport_blue\\headmodel\\crash/red"
                   "\\handicap\\100\\cl_anonymous\\0\\color1\\4\\color2\\23\\sex\\male"
                   "\\teamtask\\0\\rate\\25000\\country\\NO")


class NonexistentPlayerError(Exception):
    """An exception that is raised when a player that disconnected is being used
    as if the player were still present.

    """


class Player:
    """A class that represents a player on the server. As opposed to minqlbot,
    attributes are all the values from when the class was instantiated. This
    means for instance if a player is on the blue team when you check, but
    then moves to red, it will still be blue when you check a second time.
    To update it, use :meth:`~.Player.update`. Note that if you update it
    and the player has disconnected, it will raise a
    :exc:`minqlx.NonexistentPlayerError` exception.

    """
    __slots__ = ("_valid", "_id", "_info", "_userinfo", "_steam_id", "_name")

    def __init__(self, client_id, info=None):
        self._valid = True

        # Can pass own info for efficiency when getting all players and to allow dummy players.
        if info:
            self._id = client_id
            self._info = info
        else:
            self._id = client_id
            self._info = minqlx.player_info(client_id)
            if not self._info:
                self._invalidate(f"Tried to initialize a Player instance of nonexistant player {client_id}.")

        self._userinfo = None
        self._steam_id = self._info.steam_id

        # When a player connects, the name field in the client struct has yet to be initialized,
        # so we fall back to the userinfo and try parse it ourselves to get the name if needed.
        if self._info.name:
            self._name = self._info.name
        else:
            self._userinfo = minqlx.parse_variables(self._info.userinfo, ordered=True)
            if "name" in self._userinfo:
                self._name = self._userinfo["name"]
            else:  # No name at all. Weird userinfo during connection perhaps?
                self._name = ""

    def __repr__(self):
        if not self._valid:
            return f"{self.__class__.__name__}(INVALID:'{self.clean_name}':{self.steam_id})"

        return f"{self.__class__.__name__}({self._id}:'{self.clean_name}':{self.steam_id})"

    def __str__(self):
        return self.name

    def __contains__(self, key):
        return key in self.cvars

    def __getitem__(self, key):
        return self.cvars[key]

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.steam_id == other.steam_id

        return self.steam_id == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def update(self):
        """Update the player information with the latest data. If the player
        disconnected it will raise an exception and invalidates a player.
        The player's name and Steam ID can still be accessed after being
        invalidated, but anything else will make it throw an exception too.

        :raises: minqlx.NonexistentPlayerError

        """
        self._info = minqlx.player_info(self._id)

        if not self._info or self._steam_id != self._info.steam_id:
            self._invalidate()
            return

        if self._info.name:
            self._name = self._info.name
        else:
            self._userinfo = minqlx.parse_variables(self._info.userinfo, ordered=True)
            if "name" in self._userinfo:
                self._name = self._userinfo["name"]
            else:
                self._name = ""

    def _invalidate(self, e="The player does not exist anymore. Did the player disconnect?"):
        self._valid = False
        raise NonexistentPlayerError(e)

    @property
    def cvars(self):
        if not self._valid:
            self._invalidate()

        if not self._userinfo:
            self._userinfo = minqlx.parse_variables(self._info.userinfo, ordered=True)

        return self._userinfo.copy()

    @cvars.setter
    def cvars(self, new_cvars):
        new = "".join([f"\\{key}\\{new_cvars[key]}" for key in new_cvars])
        minqlx.client_command(self.id, f"userinfo \"{new}\"")

    @property
    def steam_id(self):
        return self._steam_id

    @property
    def id(self):
        return self._id

    @property
    def ip(self):
        if "ip" in self:
            return self["ip"].split(":")[0]
        return ""

    @property
    def clan(self):
        """The clan tag. Not actually supported by QL, but it used to be and
        fortunately the scoreboard still properly displays it if we manually
        set the configstring to use clan tags."""
        try:
            return minqlx.parse_variables(minqlx.get_configstring(529 + self._id))["cn"]
        except KeyError:
            return ""

    @clan.setter
    def clan(self, tag):
        index = self.id + 529
        cs = minqlx.parse_variables(minqlx.get_configstring(index), ordered=True)
        cs["xcn"] = tag
        cs["cn"] = tag
        new_cs = "".join([f"\\{key}\\{cs[key]}" for key in cs])
        minqlx.set_configstring(index, new_cs)

    @property
    def name(self):
        return self._name + "^7"

    @name.setter
    def name(self, value):
        new = self.cvars
        new["name"] = value
        self.cvars = new

    @property
    def clean_name(self):
        """Removes color tags from the name."""
        return re.sub(r"\^\d", "", self.name)

    @property
    def qport(self):
        if "qport" in self:
            return int(self["qport"])

        return -1

    @property
    def team(self):
        return minqlx.TEAMS[self._info.team]

    @team.setter
    def team(self, new_team):
        self.put(new_team)

    @property
    def colors(self):
        # Float because they can occasionally be floats for some reason.
        return float(self["color1"]), float(self["color2"])

    @colors.setter
    def colors(self, value):
        new = self.cvars
        c1, c2 = value
        new["color1"] = c1
        new["color2"] = c2
        self.cvars = new

    @property
    def model(self):
        return self["model"]

    @model.setter
    def model(self, value):
        new = self.cvars
        new["model"] = value
        self.cvars = new

    @property
    def headmodel(self):
        return self["headmodel"]

    @headmodel.setter
    def headmodel(self, value):
        new = self.cvars
        new["headmodel"] = value
        self.cvars = new

    @property
    def handicap(self):
        return self["handicap"]

    @handicap.setter
    def handicap(self, value):
        new = self.cvars
        new["handicap"] = value
        self.cvars = new

    @property
    def autohop(self):
        return bool(int(self["cg_autoHop"]))

    @autohop.setter
    def autohop(self, value):
        new = self.cvars
        new["autohop"] = int(value)
        self.cvars = new

    @property
    def autoaction(self):
        return bool(int(self["cg_autoAction"]))

    @autoaction.setter
    def autoaction(self, value):
        new = self.cvars
        new["cg_autoAction"] = int(value)
        self.cvars = new

    @property
    def predictitems(self):
        return bool(int(self["cg_predictItems"]))

    @predictitems.setter
    def predictitems(self, value):
        new = self.cvars
        new["cg_predictItems"] = int(value)
        self.cvars = new

    @property
    def connection_state(self):
        """A string describing the connection state of a player.

        Possible values:
        - *free* -- The player has disconnected and the slot is free to be used by someone else.
        - *zombie* -- The player disconnected and his/her slot will be available to other players shortly.
        - *connected* -- The player connected, but is currently loading the game.
        - *primed* -- The player was sent the necessary information to play, but has yet to send commands.
        - *active* -- The player finished loading and is actively sending commands to the server.

        In other words, if you need to make sure a player is in-game, check if ``player.connection_state == "active"``.

        """
        return minqlx.CONNECTION_STATES[self._info.connection_state]

    @property
    def state(self):
        return minqlx.player_state(self.id)

    @property
    def privileges(self):
        if self._info.privileges == minqlx.PRIV_MOD:
            return "mod"
        if self._info.privileges == minqlx.PRIV_ADMIN:
            return "admin"
        if self._info.privileges == minqlx.PRIV_ROOT:
            return "root"
        if self._info.privileges == minqlx.PRIV_BANNED:
            return "banned"
        return None

    @privileges.setter
    def privileges(self, value):
        if not value or value == "none":
            minqlx.set_privileges(self.id, minqlx.PRIV_NONE)
        elif value == "mod":
            minqlx.set_privileges(self.id, minqlx.PRIV_MOD)
        elif value == "admin":
            minqlx.set_privileges(self.id, minqlx.PRIV_ADMIN)
        else:
            raise ValueError("Invalid privilege level.")

    @property
    def country(self):
        return self["country"]

    @country.setter
    def country(self, value):
        new = self.cvars
        new["country"] = value
        self.cvars = new

    @property
    def valid(self):
        return self._valid

    @property
    def stats(self):
        return minqlx.player_stats(self.id)

    @property
    def ping(self):
        return self.stats.ping

    def position(self, reset=False, **kwargs):
        if reset:
            pos = minqlx.Vector3((0, 0, 0))
        else:
            pos = self.state.position

        if not kwargs:
            return pos

        x = pos.x if "x" not in kwargs else kwargs["x"]
        y = pos.y if "y" not in kwargs else kwargs["y"]
        z = pos.z if "z" not in kwargs else kwargs["z"]

        return minqlx.set_position(self.id, minqlx.Vector3((x, y, z)))

    def velocity(self, reset=False, **kwargs):
        if reset:
            vel = minqlx.Vector3((0, 0, 0))
        else:
            vel = self.state.velocity

        if not kwargs:
            return vel

        x = vel.x if "x" not in kwargs else kwargs["x"]
        y = vel.y if "y" not in kwargs else kwargs["y"]
        z = vel.z if "z" not in kwargs else kwargs["z"]

        return minqlx.set_velocity(self.id, minqlx.Vector3((x, y, z)))

    def weapons(self, reset=False, **kwargs):
        if reset:
            weaps = minqlx.Weapons(((False,)*15))
        else:
            weaps = self.state.weapons

        if not kwargs:
            return weaps

        g = weaps.g if "g" not in kwargs else kwargs["g"]
        mg = weaps.mg if "mg" not in kwargs else kwargs["mg"]
        sg = weaps.sg if "sg" not in kwargs else kwargs["sg"]
        gl = weaps.gl if "gl" not in kwargs else kwargs["gl"]
        rl = weaps.rl if "rl" not in kwargs else kwargs["rl"]
        lg = weaps.lg if "lg" not in kwargs else kwargs["lg"]
        rg = weaps.rg if "rg" not in kwargs else kwargs["rg"]
        pg = weaps.pg if "pg" not in kwargs else kwargs["pg"]
        bfg = weaps.bfg if "bfg" not in kwargs else kwargs["bfg"]
        gh = weaps.gh if "gh" not in kwargs else kwargs["gh"]
        ng = weaps.ng if "ng" not in kwargs else kwargs["ng"]
        pl = weaps.pl if "pl" not in kwargs else kwargs["pl"]
        cg = weaps.cg if "cg" not in kwargs else kwargs["cg"]
        hmg = weaps.hmg if "hmg" not in kwargs else kwargs["hmg"]
        hands = weaps.hands if "hands" not in kwargs else kwargs["hands"]

        return minqlx.set_weapons(self.id,
                                  minqlx.Weapons((g, mg, sg, gl, rl, lg, rg, pg, bfg, gh, ng, pl, cg, hmg, hands)))

    def weapon(self, new_weapon=None):
        if new_weapon is None:
            return self.state.weapon
        if new_weapon in minqlx.WEAPONS:
            pass
        elif new_weapon in minqlx.WEAPONS.values():
            new_weapon = tuple(minqlx.WEAPONS.values()).index(new_weapon)

        return minqlx.set_weapon(self.id, new_weapon)

    def ammo(self, reset=False, **kwargs):
        if reset:
            a = minqlx.Weapons(((0,)*15))
        else:
            a = self.state.ammo

        if not kwargs:
            return a

        g = a.g if "g" not in kwargs else kwargs["g"]
        mg = a.mg if "mg" not in kwargs else kwargs["mg"]
        sg = a.sg if "sg" not in kwargs else kwargs["sg"]
        gl = a.gl if "gl" not in kwargs else kwargs["gl"]
        rl = a.rl if "rl" not in kwargs else kwargs["rl"]
        lg = a.lg if "lg" not in kwargs else kwargs["lg"]
        rg = a.rg if "rg" not in kwargs else kwargs["rg"]
        pg = a.pg if "pg" not in kwargs else kwargs["pg"]
        bfg = a.bfg if "bfg" not in kwargs else kwargs["bfg"]
        gh = a.gh if "gh" not in kwargs else kwargs["gh"]
        ng = a.ng if "ng" not in kwargs else kwargs["ng"]
        pl = a.pl if "pl" not in kwargs else kwargs["pl"]
        cg = a.cg if "cg" not in kwargs else kwargs["cg"]
        hmg = a.hmg if "hmg" not in kwargs else kwargs["hmg"]
        hands = a.hands if "hands" not in kwargs else kwargs["hands"]

        return minqlx.set_ammo(self.id,
                               minqlx.Weapons((g, mg, sg, gl, rl, lg, rg, pg, bfg, gh, ng, pl, cg, hmg, hands)))

    def powerups(self, reset=False, **kwargs):
        if reset:
            pu = minqlx.Powerups(((0,)*6))
        else:
            pu = self.state.powerups

        if not kwargs:
            return pu

        quad = pu.quad if "quad" not in kwargs else round(kwargs["quad"]*1000)
        bs = pu.battlesuit if "battlesuit" not in kwargs else round(kwargs["battlesuit"]*1000)
        haste = pu.haste if "haste" not in kwargs else round(kwargs["haste"]*1000)
        invis = pu.invisibility if "invisibility" not in kwargs else round(kwargs["invisibility"]*1000)
        regen = pu.regeneration if "regeneration" not in kwargs else round(kwargs["regeneration"]*1000)
        invul = pu.invulnerability if "invulnerability" not in kwargs else round(kwargs["invulnerability"]*1000)

        return minqlx.set_powerups(self.id,
                                   minqlx.Powerups((quad, bs, haste, invis, regen, invul)))

    @property
    def holdable(self):
        return self.state.holdable

    @holdable.setter
    def holdable(self, value):
        if not value:
            minqlx.set_holdable(self.id, 0)
        elif value == "teleporter":
            minqlx.set_holdable(self.id, 27)
        elif value == "medkit":
            minqlx.set_holdable(self.id, 28)
        elif value == "flight":
            minqlx.set_holdable(self.id, 34)
            self.flight(reset=True)
        elif value == "kamikaze":
            minqlx.set_holdable(self.id, 37)
        elif value == "portal":
            minqlx.set_holdable(self.id, 38)
        elif value == "invulnerability":
            minqlx.set_holdable(self.id, 39)
        else:
            raise ValueError("Invalid holdable item.")

    def drop_holdable(self):
        minqlx.drop_holdable(self.id)

    def flight(self, reset=False, **kwargs):
        state = self.state
        if state.holdable != "flight":
            self.holdable = "flight"
            reset = True

        if reset:
            # Set to defaults on reset.
            fl = minqlx.Flight((16000, 16000, 1200, 0))
        else:
            fl = state.flight

        fuel = fl.fuel if "fuel" not in kwargs else kwargs["fuel"]
        max_fuel = fl.max_fuel if "max_fuel" not in kwargs else kwargs["max_fuel"]
        thrust = fl.thrust if "thrust" not in kwargs else kwargs["thrust"]
        refuel = fl.refuel if "refuel" not in kwargs else kwargs["refuel"]

        return minqlx.set_flight(self.id, minqlx.Flight((fuel, max_fuel, thrust, refuel)))

    @property
    def noclip(self):
        return self.state.noclip

    @noclip.setter
    def noclip(self, value):
        minqlx.noclip(self.id, bool(value))

    @property
    def health(self):
        return self.state.health

    @health.setter
    def health(self, value):
        minqlx.set_health(self.id, value)

    @property
    def armor(self):
        return self.state.armor

    @armor.setter
    def armor(self, value):
        minqlx.set_armor(self.id, value)

    @property
    def is_alive(self):
        return self.state.is_alive

    @is_alive.setter
    def is_alive(self, value):
        if not isinstance(value, bool):
            raise ValueError("is_alive needs to be a boolean.")

        cur = self.is_alive
        if cur and value is False:
            # TODO: Proper death and not just setting health to 0.
            self.health = 0
        elif not cur and value is True:
            minqlx.player_spawn(self.id)

    @property
    def is_frozen(self):
        return self.state.is_frozen

    @property
    def score(self):
        return self.stats.score

    @score.setter
    def score(self, value):
        minqlx.set_score(self.id, value)

    @property
    def channel(self):
        return minqlx.TellChannel(self)

    def center_print(self, msg):
        minqlx.send_server_command(self.id, f"cp \"{msg}\"")

    def tell(self, msg, **kwargs):
        return minqlx.Plugin.tell(msg, self, **kwargs)

    def kick(self, reason=""):
        return minqlx.Plugin.kick(self, reason)

    def ban(self):
        return minqlx.Plugin.ban(self)

    def tempban(self):
        return minqlx.Plugin.tempban(self)

    def addadmin(self):
        return minqlx.Plugin.addadmin(self)

    def addmod(self):
        return minqlx.Plugin.addmod(self)

    def demote(self):
        return minqlx.Plugin.demote(self)

    def mute(self):
        return minqlx.Plugin.mute(self)

    def unmute(self):
        return minqlx.Plugin.unmute(self)

    def put(self, team):
        return minqlx.Plugin.put(self, team)

    def addscore(self, score):
        return minqlx.Plugin.addscore(self, score)

    def switch(self, other_player):
        return minqlx.Plugin.switch(self, other_player)

    def slap(self, damage=0):
        return minqlx.Plugin.slap(self, damage)

    def slay(self):
        return minqlx.Plugin.slay(self)

    def slay_with_mod(self, mod):
        return minqlx.slay_with_mod(self.id, mod)

    @classmethod
    def all_players(cls):
        return [cls(i, info=info) for i, info in enumerate(minqlx.players_info()) if info]


class AbstractDummyPlayer(Player):
    def __init__(self, name="DummyPlayer"):
        info = minqlx.PlayerInfo((-1, name, minqlx.CS_CONNECTED,
                                  _DUMMY_USERINFO, -1, minqlx.TEAM_SPECTATOR, minqlx.PRIV_NONE))
        super().__init__(-1, info=info)

    @property
    def id(self):
        raise AttributeError("Dummy players do not have client IDs.")

    @property
    def steam_id(self):
        raise NotImplementedError("steam_id property needs to be implemented.")

    def update(self):
        pass

    @property
    def channel(self):
        raise NotImplementedError("channel property needs to be implemented.")

    def tell(self, msg, **kwargs):
        raise NotImplementedError("tell() needs to be implemented.")


class RconDummyPlayer(AbstractDummyPlayer):
    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    @property
    def steam_id(self):
        return minqlx.owner()

    @property
    def channel(self):
        return minqlx.CONSOLE_CHANNEL

    def tell(self, msg, **kwargs):
        self.channel.reply(msg)
