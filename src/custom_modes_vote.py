import time
import math
import random
from datetime import datetime, timedelta
import redis

import minqlx
import minqlx.database

game_settings = {
    "dmflags": {'pql': '60', 'vql': '28', 'midair': '28', 'midair+': '28'},
    "g_infiniteammo": {'pql': '0', 'vql': '0', 'midair': '1', 'midair+': '1'},
    "g_knockback_pg": {'pql': '1.25', 'vql': '1.10', 'midair': '1.10', 'midair+': '1.10'},
    "g_knockback_rl": {'pql': '1.10', 'vql': '0.90', 'midair': '1.80', 'midair+': '1.80'},
    "g_knockback_gl": {'pql': '1.10', 'vql': '1.10', 'midair': '1.80', 'midair+': '1.80'},
    "g_knockback_z": {'pql': '40', 'vql': '24', 'midair': '700', 'midair+': '700'},
    "g_max_knockback": {'pql': '160', 'vql': '120', 'midair': '120', 'midair+': '120'},
    "g_respawn_delay_max": {'pql': '3500', 'vql': '2400', 'midair': '2400', 'midair+': '2400'},
    "g_splashdamage_rl": {'pql': '84', 'vql': '84', 'midair': '1', 'midair+': '1'},
    "g_splashdamage_gl": {'pql': '100', 'vql': '100', 'midair': '1', 'midair+': '1'},
    "g_splashradius_pg": {'pql': '32', 'vql': '20', 'midair': '20', 'midair+': '20'},
    "g_startingWeapons": {'pql': '8447', 'vql': '8447', 'midair': '16', 'midair+': '24'},
    "g_startingHealth": {'pql': '200', 'vql': '200', 'midair': '100', 'midair+': '100'},
    "g_startingHealthBonus": {'pql': '0', 'vql': '0', 'midair': '5', 'midair+': '5'},
    "g_startingArmor": {'pql': '100', 'vql': '100', 'midair': '0', 'midair+': '0'},
    "g_velocity_gl": {'pql': '800', 'vql': '700', 'midair': '700', 'midair+': '700'},
    "pmove_AirControl": {'pql': '1', 'vql': '0', 'midair': '0', 'midair+': '0'},
    "pmove_RampJump": {'pql': '1', 'vql': '0', 'midair': '0', 'midair+': '0'},
    "pmove_WeaponRaiseTime": {'pql': '10', 'vql': '200', 'midair': '200', 'midair+': '200'},
    "pmove_WeaponDropTime": {'pql': '10', 'vql': '200', 'midair': '200', 'midair+': '200'},
    "weapon_reload_rg": {'pql': '1250', 'vql': '1500', 'midair': '1500', 'midair+': '1500'},
    "weapon_reload_sg": {'pql': '950', 'vql': '1000', 'midair': '1000', 'midair+': '1000'},
    "pmove_BunnyHop": {'pql': '0', 'vql': '1', 'midair': '1', 'midair+': '1'},
    "pmove_CrouchStepJump": {'pql': '0', 'vql': '1', 'midair': '1', 'midair+': '1'},
    "pmove_JumpTimeDeltaMin": {'pql': '50', 'vql': '100.0f', 'midair': '100.0f', 'midair+': '100.0f'},
    "pmove_WaterSwimScale": {'pql': '0.5f', 'vql': '0.6f', 'midair': '0.6f', 'midair+': '0.6f'},
    "pmove_WaterWadeScale": {'pql': '0.75f', 'vql': '0.8f', 'midair': '0.8f', 'midair+': '0.8f'}
}

HOLY_SHIT_SOUNDS = ["sound/vo_evil/holy_shit.ogg", "sound/vo_female/holy_shit.ogg", "sound/vo/holy_shit.ogg"]
NEW_HIGHSCORE_SOUNDS = ["sound/vo_evil/new_high_score.ogg", "sound/vo_female/new_high_score.ogg",
                        "sound/vo/new_high_score.ogg"]

MIDAIR_KEY = "minqlx:midair:{}"
PLAYER_KEY = "minqlx:players:{}"
LAST_USED_NAME_KEY = "minqlx:players:{}:last_used_name"


def available_modes():
    keys = set()
    for value in game_settings.values():
        for key in value:
            keys.add(key)

    return keys


def calculate_distance(data):
    killer_x = data['KILLER']['POSITION']['X']
    killer_y = data['KILLER']['POSITION']['Y']
    killer_z = data['KILLER']['POSITION']['Z']
    victim_x = data['VICTIM']['POSITION']['X']
    victim_y = data['VICTIM']['POSITION']['Y']
    victim_z = data['VICTIM']['POSITION']['Z']
    return math.sqrt((victim_x - killer_x) ** 2 + (victim_y - killer_y) ** 2 + (victim_z - killer_z) ** 2)


def calculate_height_difference(data):
    killer_z = data['KILLER']['POSITION']['Z']
    victim_z = data['VICTIM']['POSITION']['Z']
    return abs(killer_z - victim_z)


def identify_reply_channel(channel):
    if channel in [minqlx.RED_TEAM_CHAT_CHANNEL, minqlx.BLUE_TEAM_CHAT_CHANNEL,
                   minqlx.SPECTATOR_CHAT_CHANNEL, minqlx.FREE_CHAT_CHANNEL]:
        return minqlx.CHAT_CHANNEL

    return channel


# noinspection PyPep8Naming
class custom_modes_vote(minqlx.Plugin):
    """
    This plugin allows switching to customizable game modes, ships with vanilla QL settings and PQL promode settings

    Uses:
    * qlx_modeVoteNewMapDefault (default: "pql") Default game mode upon new map loading, set to None to keep the
    previous map's mode even with the new map.
    """

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_modeVoteNewMapDefault", "vql")

        self.set_cvar_once("qlx_midair_mindistance", "300")
        self.set_cvar_once("qlx_midair_minheight_diff", "100")

        self.default_mode = self.get_cvar("qlx_modeVoteNewMapDefault", str)

        self.midair_mindistance: int = self.get_cvar("qlx_midair_mindistance", int)
        self.midair_minheight_diff: int = self.get_cvar("qlx_midair_minheight_diff", int)

        self.add_hook("frame", self.handle_frame, priority=minqlx.PRI_LOWEST)
        self.add_hook("map", self.handle_map_change)
        self.add_hook("vote_called", self.handle_vote_called)
        self.add_hook("vote_ended", self.handle_vote_ended, priority=minqlx.PRI_LOWEST)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("death", self.handle_death)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)

        formatted_modes = "|".join(available_modes())
        self.add_command("mode", self.cmd_switch_mode, permission=5, usage=f"[{formatted_modes}]")
        self.add_command(("topshots", "top"), self.cmd_topshots)
        self.add_command(("mytopshots", "mytop"), self.cmd_mytopshots)
        self.add_command(("kills", "killstats"), self.cmd_killstats)
        self.add_command("cleartopshots", self.cmd_cleartopshots, 5)
        self.add_command("clearkillstats", self.cmd_clearkillstats, 5)

        self.previous_factory = None

        self.mode = self.default_mode

        self.maploadtime = 0.0

        self.round_start_time = None
        self.previous_healths = {}

        self.holy_shit_iterator = random_iterator(HOLY_SHIT_SOUNDS)
        self.new_highscore_iterator = random_iterator(NEW_HIGHSCORE_SOUNDS)

        self.record = 0.0
        self.top_midair = {}

    def handle_frame(self):
        if not self.game:
            return

        if not self.mode.startswith("midair") and self.game.factory not in ["maido", "midair", "midair+"]:
            return

        starting_health = self.get_cvar("g_startingHealth", int)
        starting_health_bonus = self.get_cvar("g_startingHealthBonus", int)

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            if player.health <= 0:
                continue

            if player.velocity().z == 0.0:
                current_health = player.health
                if current_health <= starting_health + starting_health_bonus:
                    self.previous_healths[player.steam_id] = current_health
                player.health = 666
                continue

            if player.health <= (starting_health + starting_health_bonus):
                continue

            seconds_into_round = self.seconds_into_round()
            if player.steam_id in self.previous_healths:
                previous_health = self.previous_healths[player.steam_id]
                if seconds_into_round == -1:
                    if self.game is not None and self.game.state == "warmup":
                        player.health = previous_health
                    else:
                        player.health = starting_health + starting_health_bonus
                elif seconds_into_round > starting_health_bonus:
                    player.health = min(previous_health, starting_health)
                elif previous_health < starting_health + starting_health_bonus - seconds_into_round:
                    player.health = previous_health
                else:
                    player.health = max(previous_health - seconds_into_round, starting_health)
            elif seconds_into_round == -1:
                player.health = starting_health + starting_health_bonus
            else:
                player.health = starting_health

    def seconds_into_round(self):
        if self.round_start_time is None:
            return -1

        round_start = datetime.fromtimestamp(self.round_start_time)
        delta = datetime.now() - round_start
        return int(delta.total_seconds())

    def handle_map_change(self, mapname, factory):
        self.maploadtime = time.time()

        self.round_start_time = None
        self.previous_healths = {}

        if MIDAIR_KEY.format(mapname) in self.db:
            self.record = self.db.zrevrange(MIDAIR_KEY.format(mapname), 0, 0, withscores=True)[0][1]
        else:
            self.record = 0.0

        minqlx.console_command("g_infiniteammo 1")

        if self.default_mode and self.mode != self.default_mode:
            self.switch_mode(self.default_mode)

        if factory in available_modes():
            self.switch_mode(factory)

        if factory == "ca" and self.previous_factory != "ca":
            if self.default_mode:
                self.switch_mode(self.default_mode)

        self.previous_factory = factory

    def handle_vote_called(self, caller, vote, args):
        if minqlx.Plugin.is_vote_active():
            return minqlx.RET_NONE

        if vote.lower() != "mode":
            return minqlx.RET_NONE

        if not self.is_vote_allowed(caller):
            return minqlx.RET_STOP_ALL

        voted_mode = args.lower().strip()

        if voted_mode not in available_modes():
            return minqlx.RET_NONE

        if voted_mode == self.mode.lower():
            return minqlx.RET_STOP_ALL

        # noinspection PyUnresolvedReferences
        minqlx.EVENT_DISPATCHERS["vote_started"].caller(caller)
        minqlx.callvote(f"mode {voted_mode}", f"mode {voted_mode}")
        minqlx.client_command(caller.id, "vote yes")

        self.msg(f"{caller.name}^7 called a vote.")
        return minqlx.RET_STOP_ALL

    def is_vote_allowed(self, player):
        if not self.get_cvar("g_allowSpecVote", bool) and player.team == "spectator":
            return False

        map_load_time = datetime.fromtimestamp(self.maploadtime)
        vote_delay = self.get_cvar("g_voteDelay", int)
        time_left = map_load_time + timedelta(milliseconds=vote_delay) - datetime.now()
        if time_left > timedelta(milliseconds=0):
            player.tell(f"Voting will be allowed in ^6{time_left.total_seconds():.1f}^7 seconds.")
            return False

        return True

    def handle_vote_ended(self, _votes, vote, args, passed):
        if vote.lower() != "mode":
            return

        if args.lower() not in available_modes():
            return

        if not passed:
            return

        self.switch_mode(args.lower())

    def handle_game_countdown(self):
        self.top_midair.clear()

        if self.game.factory in ["midair", "midair+"]:
            return

        infinite_ammo_settings = game_settings["g_infiniteammo"][self.mode]
        minqlx.console_command(f"g_infiniteammo {infinite_ammo_settings}")

    def handle_round_start(self, _roundnumber):
        self.round_start_time = time.time()

    def handle_death(self, victim, killer, data):
        if self.game is None or self.game.state != "in_progress":
            return

        if data['KILLER'] is None:
            return

        if data["MOD"] not in ["ROCKET", "GRENADE"] or not data["VICTIM"]["AIRBORNE"]:
            return

        if self.mode.startswith("midair") or self.game.factory in ["maido", "midair", "midair+"]:
            if victim.steam_id in self.previous_healths:
                del self.previous_healths[victim.steam_id]

        distance = calculate_distance(data)
        height = calculate_height_difference(data)

        if height < self.midair_minheight_diff or distance < self.midair_mindistance:
            return

        map_name = self.game.map.lower()

        killer_score, victim_score = self.record_midair_scores(map_name, killer.steam_id, victim.steam_id, distance,
                                                               int(time.time()))

        if distance <= self.record:
            if height > self.midair_minheight_diff or distance > self.midair_mindistance:
                self.play_sound_to_subscribers(next(self.holy_shit_iterator), players=[victim, killer])
            msg = f"{killer.name}^7 killed {victim.name}^7 from a distance of: ^1{round(distance)} ^7units. " \
                  f"Score: ^2{killer_score}^7:^2{victim_score}"
            self.msg(msg)
        elif distance > self.record:
            self.play_sound_to_subscribers(next(self.new_highscore_iterator), players=[victim, killer])
            msg = f"^1New map record^7! {killer.name}^7 killed {victim.name}^7 " \
                  f"from a distance of: ^1{round(distance)} ^7units. Score: ^2{killer_score}^7:^2{victim_score}"
            self.msg(msg)
            self.record = distance

        if not self.top_midair:
            self.top_midair = {'k_name': killer.name, 'v_name': victim.name, 'units': distance}
            return

        if distance <= self.top_midair['units']:
            return

        self.top_midair = {'k_name': killer.name, 'v_name': victim.name, 'units': distance}

    def handle_round_end(self, _data):
        self.round_start_time = None
        self.previous_healths = {}

    def record_midair_scores(self, map_name, killer_sid, victim_sid, distance, timestamp):
        if redis.VERSION[0] == 2:
            self.db.zadd(MIDAIR_KEY.format(map_name), distance, f"{killer_sid},{victim_sid},{timestamp}")
            self.db.zincrby(MIDAIR_KEY.format(map_name) + ":count", killer_sid, 1)
            self.db.zadd(PLAYER_KEY.format(killer_sid) + ":midair:" + str(map_name), distance,
                         f"{victim_sid},{timestamp}")
        else:
            self.db.zadd(MIDAIR_KEY.format(map_name), {f"{killer_sid},{victim_sid},{timestamp}": distance})
            self.db.zincrby(MIDAIR_KEY.format(map_name) + ":count", 1, killer_sid)
            self.db.zadd(PLAYER_KEY.format(killer_sid) + ":midair:" + str(map_name),
                         {f"{victim_sid},{timestamp}": distance})

        self.db.sadd(PLAYER_KEY.format(killer_sid) + ":midair", victim_sid)
        self.db.incr(PLAYER_KEY.format(killer_sid) + ":midair:" + str(victim_sid))

        killer_score = self.db[PLAYER_KEY.format(killer_sid) + ":midair:" + str(victim_sid)]
        victim_score = 0
        if PLAYER_KEY.format(victim_sid) + ":midair:" + str(killer_sid) in self.db:
            victim_score = self.db[PLAYER_KEY.format(victim_sid) + ":midair:" + str(killer_sid)]

        return killer_score, victim_score

    @minqlx.thread
    def play_sound_to_subscribers(self, sound, players=None):
        if players is None:
            players = self.players()

        for player in players:
            flag = self.db.get_flag(player, "essentials:sounds_enabled", default=True)
            if flag:
                self.play_sound(sound, player)

    def handle_game_end(self, data):
        self.round_start_time = None

        if self.top_midair:
            topkiller_name = self.top_midair['k_name']
            topvictim_name = self.top_midair['v_name']
            top_distance = round(self.top_midair['units'])
            self.msg(f"Top midair: {topkiller_name} killed {topvictim_name} "
                     f"from a distance of: ^1{top_distance} ^7units.")
        self.top_midair.clear()

        if bool(data["ABORTED"]):
            minqlx.console_command("g_infiniteammo 1")

    def cmd_switch_mode(self, _player, msg, _channel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        if msg[1].lower() not in available_modes():
            return minqlx.RET_USAGE

        self.switch_mode(msg[1].lower())
        return minqlx.RET_NONE

    def switch_mode(self, mode):
        self.mode = mode
        for setting, values in game_settings.items():
            minqlx.console_command(f"{setting} {values[mode]}")
        self.msg(f"^4{mode.upper()}^7 settings loaded!")
        self.center_print(f"{mode.upper()} settings loaded!")

        if self.game and self.game.state == "warmup":
            minqlx.console_command("g_infiniteammo 1")

    def cmd_topshots(self, _player, _msg, channel):
        x = 5  # how many topshots to list
        map_name = self.game.map.lower()
        reply_channel = identify_reply_channel(channel)

        if MIDAIR_KEY.format(map_name) not in self.db:
            reply_channel.reply(f"^7No midair topshots recorded for map ^1{map_name}^7.")
            return

        topshots = self.db.zrevrange(MIDAIR_KEY.format(map_name), 0, x - 1, withscores=True)
        reply_channel.reply(f"^1Midair ^7topshots for map ^1{map_name}^7:\n")
        i = 1
        for shot, distance in topshots:
            k_id, v_id, timestamp = map(int, shot.split(","))
            k_id_name = self.resolve_player_name(k_id)
            v_id_name = self.resolve_player_name(v_id)
            if not k_id_name:
                reply_channel.reply(
                    f"^2{str(i)}^7: BOT killed {v_id_name} from a distance of: ^1{round(distance)} ^7units.")
            elif not v_id_name:
                reply_channel.reply(
                    f"^2{str(i)}^7: {k_id_name} killed BOT from a distance of: ^1{round(distance)} ^7units.")
            else:
                reply_channel.reply(
                    f"^2{str(i)}^7: {k_id_name} killed {v_id_name} from a distance of: ^1{round(distance)} ^7units.")
            i += 1

    def cmd_mytopshots(self, player, _msg, channel):
        x = 10  # how many topshots to list
        map_name = self.game.map.lower()
        reply_channel = identify_reply_channel(channel)

        if PLAYER_KEY.format(player.steam_id) + ":midair:" + str(map_name) not in self.db:
            reply_channel.reply(f"^7No midair topshots recorded for map ^1{map_name}^7.")
            return

        topshots = self.db.zrevrange(PLAYER_KEY.format(player.steam_id) + ":midair:" + str(map_name), 0, x - 1,
                                     withscores=True)
        reply_channel.reply(f"^7Your ^1midair ^7topshots for map ^1{map_name}^7:\n")
        i = 1
        for shot, distance in topshots:
            v_id, timestamp = map(int, shot.split(","))
            v_id_name = self.resolve_player_name(v_id)
            if not v_id_name:
                reply_channel.reply(
                    f"^2{str(i)}^7: Victim: BOT, distance: ^1{round(distance)} ^7units.")
            else:
                reply_channel.reply(
                    f"^2{str(i)}^7: Victim: {v_id_name}, distance: ^1{round(distance)} ^7units.")
            i += 1

    def cmd_killstats(self, _player, _msg, channel):
        x = 5  # how many to list
        map_name = self.game.map.lower()
        reply_channel = identify_reply_channel(channel)

        if MIDAIR_KEY.format(map_name) + ":count" not in self.db:
            reply_channel.reply(f"^7No midair kills recorded for map ^1{map_name}^7.")
            return

        killstats = self.db.zrevrange(MIDAIR_KEY.format(map_name) + ":count", 0, x - 1, withscores=True)
        reply_channel.reply(f"^7Most midair kills for map ^1{map_name}^7:\n")
        i = 1
        for steamid, count in killstats:
            name = self.resolve_player_name(steamid)
            if not name:
                reply_channel.reply(f"^2{str(i)}^7: BOT^7: ^1{int(count)} ^7kills.")
            else:
                reply_channel.reply(f"^2{str(i)}^7: {name}^7: ^1{int(count)} ^7kills.")
            i += 1

    def cmd_cleartopshots(self, _player, _msg, channel):
        map_name = self.game.map.lower()
        reply_channel = identify_reply_channel(channel)
        if MIDAIR_KEY.format(map_name) in self.db:
            del self.db[MIDAIR_KEY.format(map_name)]
        self.record = 0.0
        reply_channel.reply(f"Topshots for map ^1{map_name} ^7were cleared.")

    def cmd_clearkillstats(self, _player, _msg, channel):
        map_name = self.game.map.lower()
        reply_channel = identify_reply_channel(channel)
        if MIDAIR_KEY.format(map_name) + ":count" in self.db:
            del self.db[MIDAIR_KEY.format(map_name) + ":count"]
        reply_channel.reply(f"Killstats for map ^1{map_name} ^7were cleared.")

    def resolve_player_name(self, item):
        if not isinstance(item, int) and not item.isdigit():
            return item

        steam_id = int(item)

        player = self.player(steam_id)

        if player is not None:
            return player.name

        if self.db.exists(LAST_USED_NAME_KEY.format(steam_id)):
            return self.db.get(LAST_USED_NAME_KEY.format(steam_id))

        return item


# noinspection PyPep8Naming
class random_iterator:
    def __init__(self, seq):
        self.seq = seq
        self.random_seq = random.sample(self.seq, len(self.seq))
        self.iterator = iter(self.random_seq)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            self.random_seq = random.sample(self.seq, len(self.seq))
            self.iterator = iter(self.random_seq)
            return next(self.iterator)
