import minqlx

from datetime import datetime

from minqlx.database import Redis

BDAY_KEY = "minqlx:players:{0}:bday"
_name_key = "minqlx:players:{}:last_used_name"

# redis db key where we store all meaningful longmapnames
LONG_MAP_NAMES_KEY = "minqlx:maps:longnames"


class bday(minqlx.Plugin):
    database = Redis

    def __init__(self):
        super().__init__()

        self.bmap_steamid = None
        self.bmap_map = None

        self.set_cvar_once("qlx_bday_mapscount", "1")

        self.add_command("bday", self.cmd_bday, usage="[dd.mm.]")
        self.add_command("confirmbday", self.cmd_confirmbday)
        self.add_command("bmap", self.cmd_bmap, usage="[map]")
        self.add_command("when", self.cmd_when, usage="[player or steam_id]")
        self.add_command("nextbday", self.cmd_nextbday)
        self.add_command(("bdayedit", "setbday"), self.cmd_bdayedit, permission=2,
                         usage="[player or steam_id] [dd.mm.]")

        self.add_hook("player_loaded", self.handle_player_connected)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("map", self.handle_map)
        self.add_hook("team_switch", self.handle_team_switch)

        self.number_of_bday_maps = self.get_cvar("qlx_bday_mapscount", int)
        self.pending_bday_confirmations = dict()

    def cmd_bday(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if self.has_birthday_set(player):
            _bday = self.db[BDAY_KEY.format(player.steam_id)]
            player.tell("^7You already set your birthday to {}. If you need to correct it, please consult an admin."
                        .format(_bday))
            return

        if len(msg) < 2 or len(msg) > 4 or (len(msg) == 3 and msg[2] != "confirm"):
            return minqlx.RET_USAGE

        self.parse_date(player, msg)

    @minqlx.thread
    def parse_date(self, player: minqlx.Player, msg: str):
        try:
            birthday = datetime.strptime(msg[1], "%d.%m.")
        except ValueError:
            player.tell("^7Invalid date given")
            return minqlx.RET_USAGE

        self.pending_bday_confirmations[player.steam_id] = "{0}.{1}.".format(birthday.day, birthday.month)
        player.tell("^7We will remember your birthday as ^6{0}.{1}.^7. Please confirm with ^6!confirmbday^7 within the "
                    "next 2 minutes."
                    .format(birthday.day, birthday.month))
        self.delayed_removal_of_pending_registration(player.steam_id)

    @minqlx.delay(120)
    def delayed_removal_of_pending_registration(self, steam_id: int):
        if steam_id not in self.pending_bday_confirmations:
            return
        del self.pending_bday_confirmations[steam_id]

    def cmd_confirmbday(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if player.steam_id not in self.pending_bday_confirmations:
            player.tell("^7No pending confirmation for your birthday found. Use ^6!bday [dd.mm.]^7 to register your "
                        "birthday")
            return
        _bday = self.pending_bday_confirmations[player.steam_id]
        self.db[BDAY_KEY.format(player.steam_id)] = _bday
        del self.pending_bday_confirmations[player.steam_id]
        player.tell("^7Your birthday was stored as ^6{1}^7."
                    .format(msg[0], _bday))

    def cmd_bmap(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if not self.has_birthday_set(player):
            player.tell("^7You did ^1not^7 set your birthday, yet. Please use ^2!bday^7 to set up your birthday")
            return

        if not self.has_birthday_today(player):
            player.tell("^7Nice try, but it's not your birthday. You can't pick your birthday map now!")
            return

        if not self.can_still_pick_bday_map(player):
            player.tell("^7Sorry, you already picked enough maps for your birthday!")
            return

        if len(msg) != 2:
            return minqlx.RET_USAGE

        if not self.game:
            return

        if self.game.state != "warmup":
            player.tell("^7Sorry, you can only pick your birthday map during warmup!")
            return

        self.bmap_steamid = player.steam_id
        bday_map = self.resolve_short_mapname(msg[1], player)
        if bday_map is None:
            return

        self.bmap_map = bday_map
        self.msg("{}^7 picked {}^7 for her/his birthday".format(player.name, bday_map),
                 "chat")
        self.delay_change_map(bday_map)

    def cmd_bdayedit(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 3:
            return minqlx.RET_USAGE

        self.parse_admin_date(player, msg)

    @minqlx.thread
    def parse_admin_date(self, admin: minqlx.Player, msg: str):
        player_name, player_sid = self.identify_target(admin, msg[1])
        if player_sid is None:
            return

        try:
            _bday = datetime.strptime(msg[2], "%d.%m.")
        except ValueError:
            admin.tell("^7Invalid date given")
            return minqlx.RET_USAGE

        admin.tell("^6{0}'s birthday stored as ^6{1}.{2}."
                   .format(player_name, _bday.day, _bday.month))
        self.db[BDAY_KEY.format(player_sid)] = "{}.{}.".format(_bday.day, _bday.month)

    def identify_target(self, player: minqlx.Player, target: str):
        if hasattr(target, "name") and hasattr(target, "steam_id"):
            return target.name, target.steam_id

        try:
            steam_id = int(target)
            if self.db.exists(_name_key.format(steam_id)):
                return self.resolve_player_name(steam_id), steam_id
        except ValueError:
            pass

        player = self.find_target_player_or_list_alternatives(player, target)
        if player is None:
            return None, None

        return player.name, player.steam_id

    def resolve_player_name(self, item):
        if not isinstance(item, int) and not item.isdigit():
            return item

        steam_id = int(item)

        player = self.player(steam_id)

        if player is not None:
            return player.name

        if self.db.exists(_name_key.format(steam_id)):
            return self.db.get(_name_key.format(steam_id))

        return item

    def find_target_player_or_list_alternatives(self, player: minqlx.Player, target: str):
        # Tell a player which players matched
        def list_alternatives(players, indent=2):
            player.tell("A total of ^6{}^7 players matched for {}:".format(len(players), target))
            out = ""
            for p in players:
                out += " " * indent
                out += "{}^6:^7 {}\n".format(p.id, p.name)
            player.tell(out[:-1])

        try:
            steam_id = int(target)

            target_player = self.player(steam_id)
            if target_player:
                return target_player

        except ValueError:
            pass
        except minqlx.NonexistentPlayerError:
            pass

        target_players = self.find_player(target)

        # If there were absolutely no matches
        if not target_players:
            player.tell("Sorry, but no players matched your tokens: {}.".format(target))
            return None

        # If there were more than 1 matches
        if len(target_players) > 1:
            list_alternatives(target_players)
            return None

        # By now there can only be one person left
        return target_players.pop()

    def cmd_when(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        player_name, player_sid = self.identify_target(player, msg[1])
        if player_sid is None:
            return

        if BDAY_KEY.format(player_sid) not in self.db:
            self.msg("{} did not tell us about her/his birthday.".format(player_name))
            return

        birthday = self.db[BDAY_KEY.format(player_sid)]

        self.msg("{}^7's birthday is on ^6{}^7.".format(player_name, birthday))

    def cmd_nextbday(self, player: minqlx.Player, msg: str, channel: minqlx.AbstractChannel):
        reply_channel = self.identify_reply_channel(channel)

        self.report_next_birthday(reply_channel)

    @minqlx.thread
    def report_next_birthday(self, channel: minqlx.AbstractChannel):
        today = datetime.now()
        birthday_keys = self.db.scan_iter(BDAY_KEY.format("*"))
        min_delta = 367
        min_player_sid = None
        for birthday_key in birthday_keys:
            birthdate = datetime.strptime(self.db[birthday_key], "%d.%m.")
            next_birthdate = self.next_birthdate(birthdate)
            delta = next_birthdate - today

            if delta.days < min_delta:
                min_delta = delta.days + 1
                min_player_sid = birthday_key.replace("minqlx:players:", "").replace(":bday", "")

            if today.day == birthdate.day and today.month == birthdate.month:
                min_delta = 0
                min_player_sid = birthday_key.replace("minqlx:players:", "").replace(":bday", "")

        if min_player_sid is None:
            return

        player_name = self.resolve_player_name(int(min_player_sid))
        player_bday = self.db[BDAY_KEY.format(min_player_sid)]

        if min_delta == 0:
            channel.reply("Next birthday: {}^7 has her/his birthday today! ({}) Happy Birthday!".format(
                player_name, player_bday))
            return
        if min_delta == 1:
            channel.reply("Next birthday: {}^7 ({}) will be tomorrow!".format(player_name, player_bday))
            return

        channel.reply("Next birthday: {}^7 ({}) in {} days.".format(player_name, player_bday, min_delta))

    def next_birthdate(self, birthday: datetime):
        today = datetime.now()
        if today > birthday.replace(year=today.year):
            return birthday.replace(year=today.year + 1)
        return birthday.replace(year=today.year)

    def identify_reply_channel(self, channel):
        if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                       minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
            return minqlx.CHAT_CHANNEL

        return channel

    @minqlx.delay(5)
    def handle_player_connected(self, player: minqlx.Player):
        if self.has_birthday_today(player) and self.can_still_pick_bday_map(player):
            self.msg("It's {}^7's birthday today! Congratulate her/him!".format(player.name))
            player.tell("Happy Birthday! You can pick a birthday map by using ^6!bmap^7 <mapname>!")

    def handle_game_end(self, data):
        if self.bmap_steamid is None:
            return

        self.db.incr("{}:{}".format(BDAY_KEY.format(self.bmap_steamid), datetime.today().year))
        self.bmap_steamid = None
        self.bmap_map = None

    def handle_map(self, mapname: str, factory: str):
        if self.bmap_steamid is None and self.bmap_map is None:
            return

        if self.bmap_map == mapname:
            return

        self.bmap_steamid = None
        self.bmap_map = None

    def handle_team_switch(self, player: minqlx.Player, old: str, new: str):
        if not self.game:
            return

        if self.game.state != "warmup":
            return

        if self.bmap_steamid is None and self.bmap_map is None:
            return

        if self.game.map != self.bmap_map:
            return

        if player.steam_id != self.bmap_steamid:
            return

        if new not in ["red", "blue", "any"]:
            return

        self.play_birthday_song()

    def play_birthday_song(self):
        if "karaoke" in self.plugins:
            karaoke_plugin = minqlx.Plugin._loaded_plugins["karaoke"]
            karaoke_plugin.double = True
            karaoke_plugin.currentsong = "happybirthday"
            karaoke_plugin.clrdouble(66, "_")

        self.stop_sound()
        self.play_sound("sound/karaoke4/happybirthday.ogg")

    def has_birthday_today(self, player: minqlx.Player):
        if not self.has_birthday_set(player):
            return False

        birthday = datetime.strptime(self.db[BDAY_KEY.format(player.steam_id)], "%d.%m.")
        today = datetime.now()

        return birthday.day == today.day and birthday.month == today.month

    def has_birthday_set(self, player: minqlx.Player):
        return BDAY_KEY.format(player.steam_id) in self.db

    def can_still_pick_bday_map(self, player: minqlx.Player):
        this_years_map_picks_key = "{}:{}".format(BDAY_KEY.format(player.steam_id), datetime.today().year)
        if this_years_map_picks_key not in self.db:
            return True

        maps_picked_this_year = int(self.db["{}:{}".format(BDAY_KEY.format(player.steam_id), datetime.today().year)])
        return maps_picked_this_year < self.number_of_bday_maps

    def resolve_short_mapname(self, mapstring: str, player: minqlx.Player):
        logged_maps = self.determine_installed_maps()
        if mapstring in logged_maps:
            return mapstring

        long_map_names_db_lookup = self.db.hgetall(LONG_MAP_NAMES_KEY)
        long_map_names_lookup = {key: self.cleaned_up_longmapname(value) for (key, value) in
                                 long_map_names_db_lookup.items()}

        if mapstring in long_map_names_lookup.keys():
            return mapstring

        if len(mapstring) < 3:
            return mapstring

        matched_maps = sorted([item for item in set(
            [key for key, value in long_map_names_lookup.items() if value.find(mapstring) != -1
             and key in logged_maps] +
            [_mapname for _mapname in logged_maps if _mapname.lower().find(mapstring) != -1]
        )])

        if len(matched_maps) == 1:
            return matched_maps.pop()

        if len(matched_maps) == 0:
            return mapstring

        player.tell("More than one map matched your criteria:")
        for _mapname in matched_maps:
            if _mapname in long_map_names_lookup.keys():
                player.tell("  ^4{}^7 (short name: ^4{}^7)".format(long_map_names_db_lookup[_mapname], _mapname))
            else:
                player.tell("  ^4{}^7".format(_mapname))

        return None

    def determine_installed_maps(self):
        if "maps" in self._loaded_plugins:
            return self.plugins["maps"].logged_maps

        if "maps_manager" in self._loaded_plugins:
            return self.plugins["maps_manager"].installed_maps

        return []

    def cleaned_up_longmapname(self, longmapname: str):
        return longmapname.translate(str.maketrans("", "", " ,.-!\"'_&()")).lower()

    @minqlx.delay(3)
    def delay_change_map(self, _mapname: str):
        self.change_map("{} ca".format(_mapname))
