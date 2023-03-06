import time
import random
from datetime import datetime
import math
import redis

import minqlx
from minqlx import Plugin

LAST_STANDING_LOG = "minqlx:players:{}:last_standings"


# noinspection PyPep8Naming
class showdown(Plugin):
    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_showdown_vote", "0")
        self.set_cvar_once("qlx_showdown_vote_teamsize", "2")
        self.set_cvar_once("qlx_showdown_min", "2")
        self.set_cvar_once("qlx_showdown_max", "4")
        self.set_cvar_once("qlx_showdown_random_weapons", "g,gl,pg,bfg,gh,ng")
        self.set_cvar_once("qlx_showdown_overwrite_permission_level", "1")

        self.add_hook("death", self.handle_death)
        self.add_hook("team_switch", self.handle_switch)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)

        self.add_command(("hurry", "showdown"), self.cmd_showdown)

        self.vote_showdown = self.get_cvar("qlx_showdown_vote", bool)
        self.vote_showdown_teamsize = (
            self.get_cvar("qlx_showdown_vote_teamsize", int) or 2
        )
        self.min_opp = self.get_cvar("qlx_showdown_min", int) or 2
        self.max_opp = self.get_cvar("qlx_showdown_max", int) or 4
        self.showdown_random_weapons = self.get_cvar(
            "qlx_showdown_random_weapons", list
        )
        self.random_weapons_iter = random_iterator(self.showdown_random_weapons)

        self.showdown_overwrite_permission_level = (
            self.get_cvar("qlx_showdown_overwrite_permission_level", int) or 1
        )
        self.between_rounds = True

        self.last_standing_steam_id = None
        self.last_standing_time = None

        self.showdown_skipped_this_round = False
        self.showdown_activated = False
        self.showdown_weapon = None
        self.weapons_taken = None
        self.showdown_is_counting_down = False
        self.music_started = False

        self.showdown_votes = None

    def handle_switch(self, _player, _old, _new):
        if _old not in ["blue", "red"] and _new not in ["spectator", "free"]:
            return

        self.detect()

    def detect(self):
        if self.game is None or self.game.type_short != "ca":
            return

        if self.game.state != "in_progress":
            return

        if self.between_rounds:
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.showdown_skipped_this_round:
            return

        teams = self.teams()

        if (
            len(teams["red"]) < self.vote_showdown_teamsize
            or len(teams["blue"]) < self.vote_showdown_teamsize
        ):
            return

        alive_r = self.alive_players(teams["red"])
        alive_b = self.alive_players(teams["blue"])

        if not alive_r or not alive_b:
            return

        if len(alive_r) != 1 and len(alive_b) != 1:
            return

        if self.last_standing_time is None:
            self.last_standing_time = time.time()
            self.last_standing_steam_id = (
                alive_r[0].steam_id if len(alive_r) == 1 else alive_b[0].steam_id
            )

        self.handle_automatic_showdown(alive_r, alive_b)

        if self.vote_showdown:
            self.callvote_showdown()

    def handle_automatic_showdown(self, alive_r, alive_b):
        if self.should_reactivate_normal_game(alive_r, alive_b):
            self.reactivate_normal_game()
            return

        if self.should_activate_gauntlet_showdown(alive_r, alive_b):
            if self.should_skip_automatic_showdown_this_round(alive_r, alive_b):
                self.showdown_skipped_this_round = True
                return

            random_weapon = next(self.random_weapons_iter)
            self.activate_showdown(alive_r, alive_b, showdown_weapon=random_weapon)
            return

        if not self.showdown_activated:
            return

        if self.showdown_is_counting_down:
            return

        self.announce_player_died(alive_r, alive_b)

    def callvote_showdown(self):
        if not self.should_allow_automatic_showdown():
            return

        if self.showdown_votes is not None:
            return

        teams = self.teams()
        if self.last_standing_steam_id is None:
            return

        showdown_player = self.player(self.last_standing_steam_id)
        if showdown_player is None:
            return

        voting_team = showdown_player.team

        self.showdown_votes = {"hurry": [], "showdown": []}

        vote_now_sound = random.choice(
            ["sound/vo/vote_now", "sound/vo_evil/vote_now", "sound/vo_female/vote_now"]
        )
        for player in teams[voting_team]:
            if player.is_alive:
                continue

            self.play_sound(vote_now_sound, player)
            player.tell(
                f"Have a say in your team mate's fate:\n"
                f"  ^5!showdown^7 for a random weapon showdown^7\n"
                f"  ^5!hurry^7 to punish ^7{showdown_player.name}"
            )

    def should_allow_automatic_showdown(self):
        if self.showdown_is_counting_down:
            return False

        if self.showdown_activated:
            return False

        if self.last_standing_steam_id is None:
            return False

        teams = self.teams()
        showdown_player = self.player(self.last_standing_steam_id)

        if showdown_player is None:
            return False

        other_team = self.other_team(showdown_player.team)
        if other_team is None:
            return False

        larger_team = teams[other_team]
        alive_opponents = self.alive_players(larger_team)

        if len(alive_opponents) < self.min_opp:
            return False

        if showdown_player.health < 100:
            return False

        return True

    # noinspection PyMethodMayBeStatic
    def alive_players(self, players):
        return [player for player in players if player.is_alive]

    def should_reactivate_normal_game(self, alive_r, alive_b):
        if not self.showdown_activated:
            return False

        return len(alive_r) <= self.min_opp and len(alive_b) <= self.min_opp

    def reactivate_normal_game(self):
        if self.music_started:
            self.stop_sound()
            self.music_started = False

        self.showdown_activated = False
        for p in self.players():
            p.weapons(
                g=False,
                mg=False,
                sg=False,
                gl=False,
                rl=False,
                lg=False,
                rg=False,
                pg=False,
                bfg=False,
                gh=False,
                ng=False,
                pl=False,
                cg=False,
                hmg=False,
                hands=False,
            )
            p.weapon(15)

        minqlx.console_command("g_guidedRocket 0")

        r = "^3Restoring weapons in "
        self.blink(
            [r + "5", r + "4", r + "3", r + "2", r + "1", "^2FIGHT!"],
            interval=1,
            sound="sound/items/regen",
            callback=self.restore_original_weapons,
        )

    @minqlx.thread
    def blink(self, messages, interval=0.12, sound=None, callback=None):
        @minqlx.next_frame
        def logic(_m):
            self.center_print(f"^3{_m}")
            if sound is not None:
                self.play_sound(sound)

        for m in messages:
            time.sleep(interval)
            logic(m)

        if callback is not None:
            callback()

    def restore_original_weapons(self):
        @minqlx.next_frame
        def set_weapons(_p):
            minqlx.set_weapons(_p.id, self.weapons_taken or _p.weapons())

        for p in self.players():
            set_weapons(p)
        minqlx.console_command("g_friendlyfire 0")
        self.play_sound("sound/vo_evil/fight")

    def should_activate_gauntlet_showdown(self, alive_r, alive_b):
        if self.showdown_activated:
            return False

        if not self.game or self.game.state != "in_progress":
            return False

        return self.max_opp < len(alive_b + alive_r)

    # noinspection PyMethodMayBeStatic
    def should_skip_automatic_showdown_this_round(self, alive_r, alive_b):
        total_living_players = len(alive_b + alive_r)
        if total_living_players == 5:
            chance = 5
        elif total_living_players == 6:
            chance = 10
        elif total_living_players == 7:
            chance = 15
        elif total_living_players == 8:
            chance = 20
        else:
            chance = 25

        return random.randint(1, 100) > chance

    def activate_showdown(self, alive_r, alive_b, showdown_weapon="g"):
        for weapon in ALL_WEAPONS:
            if weapon.is_identified_by(showdown_weapon):
                self.showdown_weapon = weapon

        if self.showdown_weapon is None:
            return

        self.showdown_activated = True
        self.weapons_taken = self.weapons_taken or alive_r[0].weapons()
        for p in self.players():
            if not p.is_alive:
                continue
            p.weapons(
                g=False,
                mg=False,
                sg=False,
                gl=False,
                rl=False,
                lg=False,
                rg=False,
                pg=False,
                bfg=False,
                gh=False,
                ng=False,
                pl=False,
                cg=False,
                hmg=False,
                hands=False,
            )
            p.weapon(15)

        self.showdown_is_counting_down = True

        amount_alive_red = len(alive_r)
        amount_alive_blue = len(alive_b)
        self.blink(
            [self.showdown_weapon.countdown_announcement, ""] * 9
            + [
                f"^2{amount_alive_red}vs{amount_alive_blue} - {self.showdown_weapon.start_announcement}"
            ],
            callback=self.start_showdown,
        )
        self.play_sound("sound/world/turksquish22.wav")

        if random.random() < 0.25:
            if amount_alive_red == 1:
                alive_r[0].holdable = "kamikaze"

            if amount_alive_blue == 1:
                alive_b[0].holdable = "kamikaze"

        if not self.vote_showdown and self.min_opp > 0:
            restore_opponents = self.min_opp + 1
            self.msg(
                f"^7{self.showdown_weapon.longname} showdown! Weapons will be restored when ^6{restore_opponents}^7 "
                f"players are left standing."
            )
        else:
            self.msg(
                f"^7{self.showdown_weapon.longname} showdown! Weapons will be restored next round."
            )

    def start_showdown(self):
        @minqlx.next_frame
        def set_showdown_weapon(_p, _weapons):
            if self.showdown_weapon is None:
                return

            _p.weapons(**_weapons)
            _p.weapon(self.showdown_weapon.ql_id)
            _p.ammo(**{self.showdown_weapon.shortname: -1})
            _p.powerups(haste=30)

        if self.showdown_weapon is None:
            return

        weapons = {
            "g": False,
            "mg": False,
            "sg": False,
            "gl": False,
            "rl": False,
            "lg": False,
            "rg": False,
            "pg": False,
            "bfg": False,
            "gh": False,
            "ng": False,
            "pl": False,
            "cg": False,
            "hmg": False,
            "hands": True,
            self.showdown_weapon.shortname: True,
        }
        for p in self.players():
            if not p.is_alive:
                continue
            set_showdown_weapon(p, weapons)

        if self.showdown_weapon.shortname == "rl":
            minqlx.console_command("g_guidedRocket 1")
        minqlx.console_command("g_friendlyfire 1")
        self.play_sound("sound/vo_evil/go")

        if self.allow_music():
            self.music_started = True
            self.play_sound("sound/gaunt_showdown/yakety_sax")
        self.showdown_is_counting_down = False

    def allow_music(self):
        if not self.game:
            return False

        if self.game.blue_score == self.game.roundlimit - 1:
            return False

        if self.game.red_score == self.game.roundlimit - 1:
            return False

        return True

    def announce_player_died(self, alive_r, alive_b):
        if self.showdown_votes is not None:
            self.showdown_votes = None

        if self.showdown_weapon is None:
            return

        if not self.vote_showdown and self.min_opp > 0:
            enemies_left_for_restoring = len(alive_b + alive_r) - 1 - self.min_opp
            self.msg(
                f"^7{self.showdown_weapon.longname} showdown! Kill ^6{enemies_left_for_restoring}^7 "
                f"more enemies to restore weapons"
            )
        else:
            enemies_left = len(alive_b + alive_r) - 1
            self.msg(
                f"^7{self.showdown_weapon.longname} showdown! Kill ^6{enemies_left}^7 more enemies"
            )

        if self.showdown_weapon.shortname == "g":
            sound = random.choice(
                [
                    "sound/vo/humiliation1",
                    "sound/vo/humiliation2",
                    "sound/vo/humiliation3",
                ]
            )
            self.play_sound(sound)

        if self.last_standing_steam_id is None:
            return

        showdown_player = self.player(self.last_standing_steam_id)
        if showdown_player is None:
            return

        other_team = self.other_team(showdown_player.team)
        opponents_left = len(alive_r) if other_team == "red" else len(alive_b)

        if opponents_left == 1:
            self.blink(([f"{opponents_left} {other_team} left!"] + [""]) * 6)
        else:
            self.blink(([f"{opponents_left} {other_team}s left!"] + [""]) * 6)

    # noinspection PyMethodMayBeStatic
    def other_team(self, team):
        if team == "red":
            return "blue"

        if team == "blue":
            return "red"

        return None

    def handle_death(self, _victim, _killer, _data):
        self.detect()

    def handle_round_start(self, _round_number):
        self.between_rounds = False

    @minqlx.delay(3)
    def handle_round_end(self, _data):
        self.between_rounds = True

        self.showdown_skipped_this_round = False

        self.showdown_weapon = None
        self.showdown_votes = None

        minqlx.console_command("g_guidedRocket 0")
        minqlx.console_command("g_friendlyfire 0")
        minqlx.remove_dropped_items()

        if self.last_standing_time is not None:
            timestamp = datetime.now().timestamp()
            base_key = LAST_STANDING_LOG.format(self.last_standing_steam_id)
            last_standing_time = int(time.time() - self.last_standing_time)
            # noinspection PyUnresolvedReferences
            if self.db:
                if redis.VERSION >= (3,):
                    # noinspection PyTypeChecker
                    self.db.zadd(base_key, {timestamp: last_standing_time})
                else:
                    # noinspection PyTypeChecker
                    self.db.zadd(base_key, last_standing_time, timestamp)
            self.last_standing_steam_id = None
            self.last_standing_time = None

        if not self.showdown_activated:
            return

        self.showdown_activated = False

        if (
            self.music_started
            and self.game is not None
            and self.game.roundlimit not in [self.game.red_score, self.game.blue_score]
        ):
            self.stop_sound()
        self.music_started = False

    def cmd_showdown(self, player, msg, _channel):
        if not self.game or self.game.state != "in_progress":
            return

        if self.between_rounds:
            return

        if self.showdown_activated:
            return

        if self.is_player_eligible_to_trigger_showdown(
            player
        ) and self.is_showdown_trigger_attempt(player, msg):
            if len(msg) < 2 or msg[1] == "random":
                self.logger.debug("random showdown")
                self.weapon_showdown()
                return

            for weapon in ALL_WEAPONS:
                if weapon.is_identified_by(msg[1]):
                    self.logger.debug(f"showdown with {weapon.shortname}")
                    self.weapon_showdown(weapon.shortname)
                    return

            available_weapons = sorted(
                [weapon.shortname.lower() for weapon in ALL_WEAPONS] + ["random"]
            )
            formatted_showdown_weapons = "^7, ^5".join(available_weapons)
            player.tell(
                f"Weapon ^5{msg[1]}^7 not available. Available weapons: ^5{formatted_showdown_weapons}"
            )
            return

        if self.showdown_votes is None:
            return

        if self.last_standing_steam_id is None:
            return

        if not self.should_allow_automatic_showdown():
            self.msg("Too late for showdown votes!")
            return

        showdown_player = self.player(self.last_standing_steam_id)
        if showdown_player is None:
            return

        if player.team != showdown_player.team:
            player.tell("Nice try, but you're not on the last standing player's team!")
            return

        if player.steam_id == self.last_standing_steam_id:
            return

        voted_showdown = msg[0][1:].lower()
        if player.steam_id in self.showdown_votes[voted_showdown]:
            if not self.is_player_eligible_to_trigger_showdown(player):
                voted_text = self.showdown_vote_text_for(voted_showdown)
                player.tell(f"You already voted for {voted_text}!")
                return

            if voted_showdown == "hurry":
                self.punish_last_standing_player()
                return

            if voted_showdown == "showdown":
                self.weapon_showdown()
                return

        if player.steam_id in self.showdown_votes["hurry"]:
            player.tell(f"Changing your vote from ^5hurry up^7 to ^5{voted_showdown}^7")
            self.showdown_votes["hurry"].remove(player.steam_id)

        if player.steam_id in self.showdown_votes["showdown"]:
            player.tell(
                f"Changing your vote from ^5random weapon showdown^7 to ^5{voted_showdown}^7"
            )
            self.showdown_votes["showdown"].remove(player.steam_id)

        self.showdown_votes[voted_showdown].append(player.steam_id)
        teams = self.teams()
        votes_for_showdown = len(self.showdown_votes["showdown"])
        votes_for_hurry = len(self.showdown_votes["hurry"])
        votes_needed = math.floor((len(teams[showdown_player.team]) - 1) / 2) + 1
        self.msg(
            f"{player.name}^7 voted for {voted_showdown}. ^5{votes_for_showdown}^7/^5{votes_needed}^7 "
            f"voted for showdown, ^5{votes_for_hurry}^7/^5{votes_needed}^7 voted to punish {showdown_player.name}^7."
        )

        self.evaluate_votes()

    def is_player_eligible_to_trigger_showdown(self, player):
        if player.privileges is not None:
            return True

        if not self.db:
            return False

        return self.db.has_permission(
            player.steam_id, self.showdown_overwrite_permission_level
        )

    def is_showdown_trigger_attempt(self, player, msg):
        if len(msg) < 1:
            return False

        if msg[0][1:] != "showdown":
            return False

        if len(msg) > 1:
            return True

        return (
            self.showdown_votes is not None
            and player.steam_id in self.showdown_votes["showdown"]
        )

    def punish_last_standing_player(self):
        if self.last_standing_steam_id is None:
            return

        showdown_player = self.player(self.last_standing_steam_id)
        if showdown_player is None:
            return

        showdown_player.slap(damage=math.floor(showdown_player.health / 2))
        showdown_player.center_print("Hurry up!")
        showdown_player.tell("Your team mates voted to punish you to hurry up!")
        self.showdown_votes = None

    def weapon_showdown(self, preselected_weapon=None):
        teams = self.teams()
        alive_r = self.alive_players(teams["red"])
        alive_b = self.alive_players(teams["blue"])

        if len(alive_r) < 1 or len(alive_b) < 1:
            return

        random_weapon = (
            preselected_weapon if preselected_weapon else next(self.random_weapons_iter)
        )

        self.activate_showdown(alive_r, alive_b, showdown_weapon=random_weapon)
        self.showdown_votes = None

    # noinspection PyMethodMayBeStatic
    def showdown_vote_text_for(self, voted_showdown):
        if voted_showdown == "hurry":
            return "^5hurry up^7"

        if voted_showdown == "showdown":
            return "^5random weapon showdown^7"

        return None

    def evaluate_votes(self):
        teams = self.teams()
        if self.last_standing_steam_id is None:
            return

        showdown_player = self.player(self.last_standing_steam_id)
        if showdown_player is None:
            return

        voting_team = teams[showdown_player.team]

        votes_needed = math.floor((len(voting_team) - 1) / 2) + 1

        if self.showdown_votes is None:
            return
        if (
            "hurry" in self.showdown_votes
            and len(self.showdown_votes["hurry"]) >= votes_needed
        ):
            self.punish_last_standing_player()
            return

        if (
            "showdown" in self.showdown_votes
            and len(self.showdown_votes["showdown"]) >= votes_needed
        ):
            self.weapon_showdown()


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


class Weapon:
    def __init__(
        self,
        ql_id,
        shortname,
        longname,
        aliases,
        countdown_announcement,
        start_announcement,
    ):
        self.ql_id = ql_id
        self.shortname = shortname
        self.longname = longname
        self.aliases = aliases
        self.countdown_announcement = countdown_announcement
        self.start_announcement = start_announcement

    def is_identified_by(self, text):
        if self.shortname.lower().strip() == text.lower().strip():
            return True

        if self.longname.lower().strip() == text.lower().strip():
            return True

        return any(
            aliases.lower().strip() == text.lower().strip() for aliases in self.aliases
        )


ALL_WEAPONS = [
    Weapon(1, "g", "Pummel", ["gauntlet"], "Lube your fists...", "Go fisting!"),
    Weapon(2, "mg", "Machine gun", [], "Lube your guns...", "Go hunting!"),
    Weapon(3, "sg", "Shotgun", [], "Lube your guns...", "Shotgun!"),
    Weapon(4, "gl", "Nade", ["grenade"], "Lube your nades...", "Go nading!"),
    Weapon(5, "rl", "Guided Rocket", [], "Lube your rockets...", "Rocket them down!"),
    Weapon(6, "lg", "Shaft", [], "Lube your shafts...", "Go shafting!"),
    Weapon(7, "rg", "Rail", [], "Lube your rails...", "Go railing!"),
    Weapon(8, "pg", "Plasma", [], "Lube your plasma...", "Plasma them down!"),
    Weapon(9, "bfg", "BFG", [], "Lube your BFGs...", "Go gettem!"),
    Weapon(
        10, "gh", "Grappling", ["grapple"], "Lube your grapples...", "Grapple them!"
    ),
    Weapon(11, "ng", "Nail", [], "Lube your nails...", "Nail them!"),
    Weapon(12, "pl", "Mining", ["mine", "mines"], "Lube your mines...", "Let's mine!"),
    Weapon(13, "cg", "Chain", ["chaingun"], "Lube your chains...", "Let's chain some!"),
    Weapon(14, "hmg", "Heavy machine gun", [], "Lube your guns...", "Go hunting!"),
]
