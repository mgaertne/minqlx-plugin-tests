import minqlx
from minqlx import Plugin

import time
from operator import itemgetter

MIN_ACTIVE_PLAYERS = 3  # min players for duelarena
MAX_ACTIVE_PLAYERS = 4  # max players for duelarena


class duelarena(minqlx.Plugin):

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_duelarenaDuelToNormalThreshold", "6")
        self.set_cvar_once("qlx_duelarenaNormalToDuelThreshold", "11")

        self.add_hook("map", self.handle_map_change)
        self.add_hook("player_loaded", self.handle_player_loaded, priority=minqlx.PRI_LOWEST)
        self.add_hook("team_switch_attempt", self.handle_team_switch_event)
        self.add_hook("player_disconnect", self.handle_player_disco)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_command("join", self.cmd_join)

        self.duelarena_game = DuelArenaGame()
        self.player_agree_to_join = []

        teams = Plugin.teams()
        for _p in teams["red"] + teams["blue"]:
            self.duelarena_game.add_player(_p.steam_id)

    def handle_map_change(self, mapname, factory):
        self.duelarena_game.reset()
        self.player_agree_to_join = []

    @minqlx.delay(3)
    def handle_player_loaded(self, player):
        if not self.game:
            return

        if player.team != "spectator":
            return

        if len(self.duelarena_game.playerset) + 1 == MIN_ACTIVE_PLAYERS:
            player.tell("{}, join to activate DuelArena! Round winner stays in, loser rotates with spectator.".format(
                player.name))

        if self.game.state != "in_progress":
            return

        if not self.duelarena_game.is_activated() or not self.duelarena_game.should_be_activated():
            return

        player.tell(
            "{}, type !join to join Duel Arena or press join button to force switch to Clan Arena!".format(
                player.name))
        self.player_agree_to_join.append(player.steam_id)

    def handle_team_switch_event(self, player, old, new):
        if not self.game:
            return

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
                return

            Plugin.center_print("Ready up for ^6DuelArena^7!")
            Plugin.msg("Ready up for ^6DuelArena^7!")
            return

        if not self.duelarena_game.is_activated():
            return

        if player.steam_id == self.duelarena_game.player_red:
            self.duelarena_game.player_red = None
            return

        if player.steam_id == self.duelarena_game.player_blue:
            self.duelarena_game.player_blue = None
            return

        if new in ['red', 'blue', 'any']:
            player.tell("Server is now in ^6DuelArena^7 mode. You will automatically rotate with round loser.")
            return minqlx.RET_STOP_ALL

    def handle_player_disco(self, player, reason):
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

    def handle_round_countdown(self, round_number):
        self.duelarena_game.announce_next_round()
        self.ensure_duel_players()

    @minqlx.thread
    def ensure_duel_players(self):
        warmup_delay = int(self.get_cvar('g_roundWarmupDelay'))
        time.sleep(warmup_delay / 1000 - 1)
        self.duelarena_game.ensure_duelarena_players()

    @minqlx.delay(1)
    def handle_round_end(self, data):
        if self.game is None or self.game.type_short != "ca":
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.duelarena_game.should_print_and_reset_scores():
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

    def cmd_join(self, player, msg, channel):
        if not self.duelarena_game.is_activated():
            return

        if player.steam_id not in self.player_agree_to_join:
            return

        self.duelarena_game.add_player(player.steam_id)
        player.tell("You successfully joined the DuelArena queue. Prepare for your duel!")
        Plugin.msg("^7{} joined DuelArena!".format(player.clean_name))
        self.player_agree_to_join.remove(player.steam_id)


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

        if self.is_activated() and not self.should_be_activated():
            self.deactivate()

        if not self.is_activated() and self.should_be_activated():
            self.activate()

    def activate(self):
        if self.is_activated():
            return

        self.duelmode = True
        self.print_reset_scores = False
        self.announce_activation()

        self.initduel = (self.game is not None and self.game.state == "in_progress" and len(self.scores) == 0)

        if self.initduel:
            self.init_scores()

    def announce_activation(self):
        if not self.game:
            return
        Plugin.msg(
            "DuelArena activated! Round winner stays in, loser rotates with spectator. Hit {} rounds first to win!"
            .format(self.game.roundlimit))
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

        self.duelmode = False
        self.initduel = False
        self.player_red = None
        self.player_blue = None
        self.player_spec = []
        self.announce_deactivation()
        self.print_reset_scores = (self.game is not None and self.game.state == "in_progress" and len(self.scores) != 0)

        if not self.print_reset_scores:
            self.reset_duelarena_scores()

    def announce_deactivation(self):
        if not self.game:
            return
        Plugin.msg("DuelArena has been deactivated!")
        Plugin.center_print("DuelArena deactivated!")

    def should_be_aborted(self):
        if not self.is_activated():
            return False

        if not self.game or self.game.state != "in_progress":
            return False

        if MIN_ACTIVE_PLAYERS <= len(self.playerset) <= MAX_ACTIVE_PLAYERS:
            return False

        if len(self.scores) == 0:
            return True

        return max(self.scores.values()) < self.duel_to_normal_threshold

    def reset(self):
        self.deactivate()
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
        self.playerset[:] = [sid for sid in self.playerset if Plugin.player(sid) and Plugin.player(sid).ping < 990]
        self.queue[:] = [sid for sid in self.queue if sid in self.playerset]

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
        loser.tell("{}, you've been put back to DuelArena queue. Prepare for your next duel!".format(loser.name))

    def insert_next_player(self, team):
        loser_team_score = getattr(self.game, "{}_score".format(team))
        next_sid = self.next_player_sid()
        if next_sid is None:
            Plugin.msg("Problem fetching next player. Aborting DuelArena ...")
            self.deactivate()
            return

        next_player = Plugin.player(next_sid)
        if next_player is None or next_player.team != "spectator":
            Plugin.msg("Problem fetching next player. Aborting DuelArena ...")
            self.deactivate()
            return

        setattr(self, "player_{}".format(team), next_sid)
        next_player.put(team)
        self.game.addteamscore(team, self.scores[next_player.steam_id] - loser_team_score)

    def announce_next_round(self):
        if not self.is_activated():
            return

        teams = Plugin.teams()
        if teams["red"] and teams["blue"]:
            Plugin.center_print("{} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))
            Plugin.msg("DuelArena: {} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))

    def should_print_and_reset_scores(self):
        return self.print_reset_scores

    def print_and_reset_scores(self):
        self.print_results()
        self.reset_duelarena_scores()
        self.reset_team_scores()
        self.print_reset_scores = False

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
                Plugin.msg("Place ^3{}.^7 {} ^7(Wins:^2{}^7)".format(place, player.name, pscore[1]))

    def reset_duelarena_scores(self):
        self.scores = {}

    def reset_team_scores(self):
        if not self.game or self.game.state != "in_progress":
            return

        self.game.addteamscore("red", -self.game.red_score)
        self.game.addteamscore("blue", -self.game.blue_score)
