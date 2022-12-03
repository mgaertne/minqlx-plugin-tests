import time
from operator import itemgetter

import minqlx
from minqlx import Plugin

MIN_ACTIVE_PLAYERS = 3  # min players for duelarena
MAX_ACTIVE_PLAYERS = 4  # max players for duelarena

DUELARENA_JOIN_CMD = ("join", "j")
DUELARENA_JOIN_MSG = "You joined ^6DuelArena^7 mode, and you will automatically rotate with round loser."


# noinspection PyPep8Naming
class duelarena(minqlx.Plugin):

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_duelarenaDuelToNormalThreshold", "6")
        self.set_cvar_once("qlx_duelarenaNormalToDuelThreshold", "11")
        self.set_cvar_once("qlx_duelarenaDuelToNormalScoreReset", "continue")

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_loaded", self.handle_player_loaded, priority=minqlx.PRI_LOWEST)
        self.add_hook("team_switch_attempt", self.handle_team_switch_event)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_command(DUELARENA_JOIN_CMD, self.cmd_join)

        self.duelarena_game = DuelArenaGame()

        teams = Plugin.teams()
        for _p in teams["red"] + teams["blue"]:
            self.duelarena_game.add_player(_p.steam_id)

    def handle_map_change(self, _smapname, _factory):
        self.duelarena_game.reset()

    @minqlx.delay(3)
    def handle_player_loaded(self, player):
        if not self.game:
            return

        player.update()
        if player.team != "spectator":
            return

        if len(self.duelarena_game.playerset) + 1 == MIN_ACTIVE_PLAYERS:
            player.tell(f"{player.name}, join to activate DuelArena! Round winner stays in, loser rotates with "
                        f"spectator.")

        if self.game.state != "in_progress":
            return

        if not self.duelarena_game.is_activated() or not self.duelarena_game.should_be_activated():
            return

        player.tell(
            f"{player.name}^7, type !{DUELARENA_JOIN_CMD[0]} to join Duel Arena or press join button to "
            f"force switch to Clan Arena!")

    def handle_team_switch_event(self, player, _old, new):
        if not self.game:
            return minqlx.RET_NONE

        if new in ['red', 'blue', 'any'] and not self.duelarena_game.is_player(player.steam_id):
            self.duelarena_game.add_player(player.steam_id)
            self.duelarena_game.validate_players()
            self.duelarena_game.check_for_activation_or_abortion()

        if new in ['spectator'] and self.duelarena_game.is_player(player.steam_id):
            if player.steam_id in self.duelarena_game.player_spec:
                self.duelarena_game.player_spec.remove(player.steam_id)
            else:
                self.duelarena_game.remove_player(player.steam_id)

        if self.game.state == "warmup":
            if not self.duelarena_game.should_be_activated():
                return minqlx.RET_NONE

            Plugin.center_print("Ready up for ^6DuelArena^7!")
            Plugin.msg("Ready up for ^6DuelArena^7!")
            return minqlx.RET_NONE

        if not self.duelarena_game.is_activated():
            return minqlx.RET_NONE

        if player.steam_id == self.duelarena_game.player_red:
            self.duelarena_game.player_red = None
            return minqlx.RET_NONE

        if player.steam_id == self.duelarena_game.player_blue:
            self.duelarena_game.player_blue = None
            return minqlx.RET_NONE

        if new in ['red', 'blue', 'any']:
            player.tell(DUELARENA_JOIN_MSG)
            return minqlx.RET_STOP_ALL
        return minqlx.RET_NONE

    def handle_player_disconnect(self, player, _reason):
        self.duelarena_game.remove_player(player.steam_id)

    @minqlx.delay(3)
    def handle_game_countdown(self):
        self.duelarena_game.validate_players()

        if not self.duelarena_game.should_be_activated():
            if self.duelarena_game.is_activated():
                self.duelarena_game.deactivate()
            return

        if not self.duelarena_game.is_activated():
            self.duelarena_game.activate()
        self.duelarena_game.init_duel()

    def handle_round_countdown(self, _round_number):
        self.duelarena_game.announce_next_round()
        self.ensure_duel_players()

    @minqlx.thread
    def ensure_duel_players(self):
        warmup_delay = self.get_cvar('g_roundWarmupDelay', int) or 30
        time.sleep(warmup_delay / 1000 - 1)
        self.duelarena_game.ensure_duelarena_players()

    @minqlx.delay(1)
    def handle_round_end(self, data):
        if self.game is None or self.game.type_short != "ca":
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.duelarena_game.should_print_and_reset_scores():
            self.duelarena_game.record_scores(self.game.red_score, self.game.blue_score)
            self.duelarena_game.print_and_reset_scores()
            return

        winning_team = self.determine_winning_team(data)
        if winning_team not in ["red", "blue"]:
            return

        if self.duelarena_game.is_pending_initialization():
            winner_sid = None
            teams = Plugin.teams()
            if len(teams["red"]) == 1 and len(teams["blue"]) == 1:
                winner_sid = teams[winning_team][-1].steam_id

            self.duelarena_game.init_duel(winner_sid)
            return

        if not self.duelarena_game.is_activated():
            return

        self.duelarena_game.record_scores(self.game.red_score, self.game.blue_score)

        losing_team = self.other_team(winning_team)
        self.duelarena_game.exchange_player(losing_team)

    @staticmethod
    def determine_winning_team(data):
        return data["TEAM_WON"].lower()

    @staticmethod
    def other_team(team):
        if team == "red":
            return "blue"
        if team == "blue":
            return "red"
        return None

    def handle_game_end(self, data):
        if not self.game or bool(data["ABORTED"]):
            return

        if not self.duelarena_game.is_activated():
            return

        self.duelarena_game.record_scores(data["TSCORE0"], data["TSCORE1"])
        self.duelarena_game.print_results()

    def cmd_join(self, player, _msg, _channel):
        if not self.duelarena_game.is_activated():
            return

        if self.duelarena_game.is_player(player.steam_id) or player.team != "spectator":
            return

        self.duelarena_game.add_player(player.steam_id)
        player.tell("You successfully joined the DuelArena queue. Prepare for your duel!")
        Plugin.msg(f"^7{player.clean_name} joined DuelArena!")


class DuelArenaGame:

    def __init__(self):
        self.duelmode = False
        self.initduel = False
        self.playerset = []
        self.queue = []
        self.player_red = None
        self.player_blue = None
        self.player_spec = []
        self.scores = {}
        self.print_reset_scores = False

        self.duel_to_normal_threshold = Plugin.get_cvar("qlx_duelarenaDuelToNormalThreshold", int)
        self.normal_to_duel_threshold = Plugin.get_cvar("qlx_duelarenaNormalToDuelThreshold", int)
        self.duel_to_normal_score_reset = Plugin.get_cvar("qlx_duelarenaDuelToNormalScoreReset")

    @property
    def game(self):
        try:
            return minqlx.Game()
        except minqlx.NonexistentGameError:
            return None

    def add_player(self, player_sid):
        if player_sid not in self.playerset:
            self.playerset.append(player_sid)

        if not self.is_activated():
            return

        if player_sid not in self.queue:
            self.queue.insert(0, player_sid)
        if player_sid not in self.scores:
            self.scores[player_sid] = 0

    def remove_player(self, player_sid):
        if self.should_emergency_replace_player(player_sid):
            player = Plugin.player(player_sid)
            if player is not None:
                self.insert_next_player(player.team)

        if player_sid in self.playerset:
            self.playerset.remove(player_sid)

        self.validate_players()
        self.check_for_activation_or_abortion()

    def should_emergency_replace_player(self, player_sid):
        if not self.game:
            return False

        if self.game.state != "in_progress":
            return False

        if not self.is_activated():
            return False

        if not self.is_player(player_sid):
            return False

        player = Plugin.player(player_sid)
        if player is None:
            return False

        return player.team in ["red", "blue"]

    def next_player_sid(self):
        try:
            return self.queue.pop()
        except IndexError:
            return None

    def is_player(self, steam_id):
        return steam_id in self.playerset

    def check_for_activation_or_abortion(self):
        if self.should_be_aborted():
            self.deactivate()
            return

        if not self.is_activated() and self.should_be_activated():
            self.activate()
            return

        if self.is_activated() and (
                MIN_ACTIVE_PLAYERS < len(self.playerset) or len(self.playerset) > MAX_ACTIVE_PLAYERS) and len(
                self.scores) > 0 and max(self.scores.values()) < self.duel_to_normal_threshold:
            self.deactivate()

    def activate(self):
        if self.is_activated():
            return

        self.duelmode = True
        self.print_reset_scores = False
        self.announce_activation()

        self.initduel = (self.game is not None and (self.game.state == "countdown" or
                                                    (self.game.state == "in_progress" and len(self.scores) == 0)))

    def announce_activation(self):
        if not self.game:
            return
        Plugin.msg(
            f"DuelArena activated! Round winner stays in, loser rotates with spectator. Hit {self.game.roundlimit} "
            f"rounds first to win!")
        Plugin.center_print("DuelArena activated!")

    def should_be_activated(self):
        if len(self.playerset) != MIN_ACTIVE_PLAYERS:
            return False

        if not self.game or self.game.state != "in_progress":
            return True

        return self.game.red_score + self.game.blue_score < self.normal_to_duel_threshold

    def is_activated(self):
        return self.duelmode

    def deactivate(self):
        if not self.is_activated():
            return

        self.print_reset_scores = (self.game is not None and self.game.state == "in_progress" and
                                   not self.is_pending_initialization() and len(self.scores) != 0)

        self.print_reset_scores = self.print_reset_scores and len(self.playerset) != 2
        self.print_reset_scores = self.print_reset_scores and max(self.scores.values()) < self.duel_to_normal_threshold

        if not self.print_reset_scores and not self.is_pending_initialization():
            self.reset_duelarena_scores()

        self.duelmode = False
        self.initduel = False
        self.player_red = None
        self.player_blue = None
        self.player_spec = []
        self.announce_deactivation()

    def announce_deactivation(self):
        if not self.game:
            return
        Plugin.msg("DuelArena has been deactivated!")
        Plugin.center_print("DuelArena deactivated!")

    def should_be_aborted(self):
        if not self.is_activated():
            return False

        if not self.game or self.game.state != "in_progress":
            return True

        if MIN_ACTIVE_PLAYERS <= len(self.playerset) <= MAX_ACTIVE_PLAYERS:
            return False

        if len(self.scores) == 0:
            return True

        return max(self.scores.values()) < self.duel_to_normal_threshold

    def reset(self):
        self.deactivate()
        self.print_reset_scores = False
        self.playerset = []
        self.queue = []

    def init_duel(self, winner_sid=None):
        teams = Plugin.teams()
        for p in [player for player in teams["red"] + teams["blue"] if player.steam_id not in self.playerset]:
            self.playerset.append(p.steam_id)
        self.validate_players()
        self.init_scores()

        for sid in [player_sid for player_sid in self.playerset if player_sid not in self.queue]:
            self.queue.insert(0, sid)

        red_sid, blue_sid = self.determine_initial_players(winner_sid)

        self.put_players_on_the_right_teams(red_sid, blue_sid)

        self.initduel = False

    def determine_initial_players(self, winner_sid=None):
        if winner_sid is None or winner_sid not in self.queue:
            return self.queue.pop(), self.queue.pop()

        teams = Plugin.teams()
        self.queue.remove(winner_sid)
        other_player = self.next_player_sid()
        while other_player in [player.steam_id for player in teams["red"] + teams["blue"]]:
            self.queue.insert(0, other_player)
            other_player = self.next_player_sid()

        return winner_sid, other_player

    def put_players_on_the_right_teams(self, red_sid, blue_sid):
        self.put_active_players_on_the_right_teams(red_sid, blue_sid)

        teams = Plugin.teams()
        for player in [_p for _p in teams["red"] + teams["blue"] if _p.steam_id not in [red_sid, blue_sid]]:
            player.put("spectator")

    def put_active_players_on_the_right_teams(self, red_sid, blue_sid):
        red_player = Plugin.player(red_sid)
        blue_player = Plugin.player(blue_sid)

        if not red_player or not blue_player:
            return

        if red_player.team == "red" and blue_player.team == "blue":
            self.game.addteamscore("red", self.scores[red_sid] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[blue_sid] - self.game.blue_score)
            return

        if red_player.team == "blue" and blue_player.team == "red":
            self.game.addteamscore("red", self.scores[blue_player.steam_id] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[red_player.steam_id] - self.game.blue_score)
            return

        if red_player.team == "red":
            self.game.addteamscore("red", self.scores[red_sid] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[blue_sid] - self.game.blue_score)
            self.player_blue = blue_sid
            blue_player.put("blue")
            return

        if red_player.team == "blue":
            self.game.addteamscore("red", self.scores[blue_sid] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[red_sid] - self.game.blue_score)
            self.player_red = blue_sid
            blue_player.put("red")
            return

        if blue_player.team == "blue":
            self.game.addteamscore("red", self.scores[red_sid] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[blue_sid] - self.game.blue_score)
            self.player_red = red_sid
            red_player.put("red")
            return

        if blue_player.team == "red":
            self.game.addteamscore("red", self.scores[blue_sid] - self.game.red_score)
            self.game.addteamscore("blue", self.scores[red_sid] - self.game.blue_score)
            self.player_blue = red_sid
            red_player.put("blue")
            return

        self.game.addteamscore("red", self.scores[red_sid] - self.game.red_score)
        self.game.addteamscore("blue", self.scores[blue_sid] - self.game.blue_score)
        self.player_red = red_sid
        red_player.put("red")
        self.player_blue = blue_sid
        blue_player.put("blue")

    def ensure_duelarena_players(self):
        if not self.is_activated():
            return

        teams = Plugin.teams()
        if len(teams["red"] + teams["blue"]) != 3:
            return

        for player in teams["red"] + teams["blue"]:
            if not self.is_player(player.steam_id):
                self.player_spec.append(player.steam_id)
                player.put("spectator")
                return

            if player.steam_id in self.queue:
                self.player_spec.append(player.steam_id)
                player.put("spectator")
                return

    def init_scores(self):
        self.scores = {sid: 0 for sid in self.playerset}

        teams = Plugin.teams()
        if not self.game or self.game.state != "in_progress" or len(teams["red"]) != 1 or len(teams["blue"]) != 1:
            return

        self.scores[teams["red"][-1].steam_id] = self.game.red_score
        self.scores[teams["blue"][-1].steam_id] = self.game.blue_score

    def is_pending_initialization(self):
        return self.initduel

    def validate_players(self):
        self.playerset[:] = [sid for sid in self.playerset if self.player_is_still_with_us(sid)]
        self.queue[:] = [sid for sid in self.queue if sid in self.playerset]

    @staticmethod
    def player_is_still_with_us(steam_id):
        player = Plugin.player(steam_id)
        if not player:
            return False

        return player.ping < 990

    def record_scores(self, red_score, blue_score):
        teams = Plugin.teams()
        try:
            self.scores[teams["red"][-1].steam_id] = max(red_score, 0)
        except IndexError:
            pass

        try:
            self.scores[teams["blue"][-1].steam_id] = max(blue_score, 0)
        except IndexError:
            pass

    def exchange_player(self, losing_team):
        teams = Plugin.teams()

        try:
            loser = teams[losing_team][-1]
        except IndexError:
            loser = None

        self.insert_next_player(losing_team)

        if loser is None:
            return

        self.queue.insert(0, loser.steam_id)
        self.player_spec.append(loser.steam_id)
        loser.put("spectator")
        loser.tell(f"{loser.name}, you've been put back to DuelArena queue. Prepare for your next duel!")

    def insert_next_player(self, team):
        loser_team_score = getattr(self.game, f"{team}_score")
        next_sid = self.next_player_sid()

        if next_sid is None:
            Plugin.msg("Problem fetching next player. Aborting DuelArena ...")
            self.deactivate()
            return

        next_player = Plugin.player(next_sid)
        if next_player is None:
            Plugin.msg("Problem fetching next player. Aborting DuelArena ...")
            self.deactivate()
            return

        setattr(self, f"player_{team}", next_sid)
        next_player.put(team)
        self.game.addteamscore(team, self.scores[next_player.steam_id] - loser_team_score)

    def announce_next_round(self):
        if not self.is_activated():
            return

        teams = Plugin.teams()
        if teams["red"] and teams["blue"]:
            Plugin.center_print(f"{teams['red'][-1].name} ^2vs^7 {teams['blue'][-1].name}")
            Plugin.msg(f"DuelArena: {teams['red'][-1].name} ^2vs^7 {teams['blue'][-1].name}")

    def should_print_and_reset_scores(self):
        return self.print_reset_scores

    def print_and_reset_scores(self):
        self.print_results()
        self.reset_team_scores()
        self.print_reset_scores = False
        self.reset_duelarena_scores()

    def print_results(self):
        Plugin.msg("DuelArena results:")
        place = 0
        prev_score = -1
        for pscore in sorted(self.scores.items(), key=itemgetter(1), reverse=True):
            if pscore[1] != prev_score:
                place += 1
            prev_score = pscore[1]
            player = Plugin.player(pscore[0])
            if player and len(player.name) != 0:
                Plugin.msg(f"Place ^3{place}.^7 {player.name} ^7(Wins:^2{pscore[1]}^7)")

    def reset_duelarena_scores(self):
        self.scores = {}

    def reset_team_scores(self):
        if not self.game or self.game.state != "in_progress":
            return

        if self.duel_to_normal_score_reset == "zero":
            self.game.addteamscore("red", -self.game.red_score)
            self.game.addteamscore("blue", -self.game.blue_score)
            return

        if self.duel_to_normal_score_reset == "maximum":
            teams = Plugin.teams()
            red_team_scores = [self.scores[player.steam_id] for player in teams["red"] if
                               player.steam_id in self.scores]
            blue_team_scores = [self.scores[player.steam_id] for player in teams["blue"] if
                                player.steam_id in self.scores]

            if len(red_team_scores) == 0:
                self.game.addteamscore("red", -self.game.red_score)
            else:
                self.game.addteamscore("red", max(red_team_scores) - self.game.red_score)
            if len(blue_team_scores) == 0:
                self.game.addteamscore("blue", -self.game.blue_score)
            else:
                self.game.addteamscore("blue", max(blue_team_scores) - self.game.blue_score)
            return
