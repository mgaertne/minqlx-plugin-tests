# DuelArena will start automatically with 3 players

import minqlx
from minqlx import Plugin

from abc import abstractmethod
from math import floor

MIN_ACTIVE_PLAYERS = 3  # min players for duelarena
MAX_ACTIVE_PLAYERS = 4  # max players for duelarena


class duelarena(minqlx.Plugin):
    def __init__(self):
        super().__init__()

        self.add_hook("team_switch_attempt", self.handle_team_switch_event)
        self.add_hook("player_disconnect", self.handle_player_disco)
        self.add_hook("player_loaded", self.handle_player_loaded, priority=minqlx.PRI_LOWEST)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("map", self.handle_map_change)
        self.add_command("duelarena", self.cmd_duelarena, permission=5, usage="[auto|force]")
        self.add_command(("duel", "d"), self.cmd_duel)

        self.duelarenastrategy = AutoDuelArenaStrategy(MIN_ACTIVE_PLAYERS)
        self.duelmode = False  # global gametype switch
        self.initduel = False  # initial player setup switch
        self.print_reset_scores = False  # flag for round_countdown
        self.player_red = None  # force spec exception for this player
        self.player_blue = None  # force spec exception for this player
        self.player_spec = set()  # force spec exception for this player
        self.duelvotes = set()  # !d !duel votes counter
        self.queue = []  # queue for rotating players
        self.scores = {}  # store/restore individual team scores

        # initialize playerset on plugin reload
        teams = Plugin.teams()
        self.playerset = set(teams['red'] + teams['blue'])  # collect players who joined a team

    # Don't allow players to join manually when DuelArena is active
    def handle_team_switch_event(self, player, old, new):

        if not self.game:
            return

        if new in ['spectator'] and player.steam_id in self.player_spec:
            self.player_spec.remove(player.steam_id)  # we initiated switch to spec? Just remove him from exception list
        elif new in ['spectator'] \
                and player.steam_id in self.playerset:  # player left team? let's see what we do with him...
                self.playerset.remove(player.steam_id)
                self.duelarena_switch()

        if new in ['red', 'blue', 'any'] and player.steam_id not in self.playerset:
            self.playerset.add(player.steam_id)  # player joined a team? Add him to playerset
            self.duelarena_switch()  # we good enough for DuelArena?

        if self.game.state == "warmup":
            if len(self.playerset) == MIN_ACTIVE_PLAYERS:
                Plugin.center_print("Ready up for ^6DuelArena^7!")
                Plugin.msg("Ready up for ^6DuelArena^7! Round winner stays in, loser rotates with spectator.")
            return

        if not self.duelmode:
            return

        # If we initiated this switch, allow it
        if player == self.player_red:
            self.player_red = None
            return
        if player == self.player_blue:
            self.player_blue = None
            return

        # If they wanted to join a team, halt this hook at enginge-level and other hooks from being called
        if new in ['red', 'blue', 'any']:
            player.tell("Server is now in ^6DuelArena^7 mode. You will automatically rotate with round loser.")
            return minqlx.RET_STOP_ALL

    # Announce next duel
    def handle_round_countdown(self, round_number):
        if not self.duelmode:
            return

        if self.print_reset_scores:
            self.print_results_and_reset_scores()
            return

        teams = Plugin.teams()
        if teams["red"] and teams["blue"]:
            Plugin.center_print("{} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))
            Plugin.msg("DuelArena: {} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))

    def print_results_and_reset_scores(self):
        self.print_results()
        self.reset_team_scores()
        self.print_reset_scores = False

    # check if we need to deavtivate DuelArena on player disconnect
    @minqlx.delay(3)
    def handle_player_disco(self, player, reason):
        if player.steam_id in self.playerset:
            self.playerset.remove(player.steam_id)
            self.duelarena_switch()

        if player.steam_id in self.duelvotes:
            self.duelvotes.remove(player.steam_id)

    @minqlx.delay(3)
    def handle_player_loaded(self, player):
        if isinstance(self.duelarenastrategy, ForcedDuelArenaStrategy) and self.game.state == "in_progress":
            playerset_with_loaded_player = self.playerset | {player.steam_id}
            if self.duelarena_should_be_aborted(self.game, playerset_with_loaded_player, self.scores):
                player.tell(
                    "{}, by joining DuelArena will be aborted and server switches to standard CA!".format(player.name))
            else:
                player.tell(
                    "{}, DuelArena match is in progress. Join to enter DuelArena! Round winner stays in, loser "
                    "rotates with spectator."
                    .format(player.name))
        elif player.team == "spectator" and len(self.playerset) == 2:
            player.tell("{}, join to activate DuelArena! Round winner stays in, loser rotates with spectator."
                        .format(player.name))
        elif not self.duelmode and len(self.connected_players()) in range(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS + 1):
            player.tell(
                "{}, type ^6!duel^7 or ^6!d^7 to vote for DuelArena! Round winner stays in, loser rotates with "
                "spectator. Hit 8 rounds first to win!"
                .format(player.name))

    # When a game is about to start and duelmode is active, initialize
    @minqlx.delay(3)
    def handle_game_countdown(self):

        self.duelarena_switch()

        if self.duelmode:
            self.init_duel()

    def handle_game_end(self, data):

        if not self.game:
            return

        # put both players back to the queue, winner first position, loser last position
        if not self.duelmode:
            return

        (loser, winner) = ("red", "blue") if int(data['TSCORE1']) > int(data['TSCORE0']) else ("blue", "red")

        teams = Plugin.teams()

        if len(teams[loser]) == 1:
            self.queue.insert(0, teams[loser][-1].steam_id)
        if len(teams[winner]) == 1:
            self.queue.append(teams[winner][-1].steam_id)
            if not teams[winner][-1].steam_id in self.scores.keys():
                self.scores[teams[winner][-1].steam_id] = 0
            self.scores[teams[winner][-1].steam_id] += 1

        self.print_results()

    @minqlx.delay(1.5)
    def handle_round_end(self, data):

        # Not in CA? Do nothing
        if not self.game or self.game.type_short != "ca":
            return

        # Last round? Do nothing except adding last score point to winner
        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.initduel:
            self.init_duel()
            return

        if not self.duelmode:
            return

        teams = Plugin.teams()

        winning_team = data["TEAM_WON"].lower()
        if winning_team not in ["red", "blue"]:
            return  # Draw? Do nothing

        winner = teams[winning_team][-1]
        self.scores[winner.steam_id] = getattr(self.game, winning_team + "_score")

        losing_team = "blue" if winning_team == "red" else "red"
        loser = teams[losing_team][-1]
        loser_team_score = getattr(self.game, losing_team + "_score")
        self.scores[loser.steam_id] = loser_team_score  # store loser team score

        if len(self.queue) == 0:
            self.deactivate_duelarena()
            self.print_results_and_reset_scores()
            return

        next_player = Plugin.player(self.queue.pop())

        if not next_player or next_player.team != "spectator":
            self.deactivate_duelarena()
            self.print_results_and_reset_scores()
            return

        self.move_player_to_team(next_player, losing_team)
        self.game.addteamscore(losing_team, self.scores[next_player.steam_id] - loser_team_score)

        self.queue.insert(0, loser.steam_id)
        self.move_player_to_team(loser, "spectator")
        loser.tell("{}, you've been put back to DuelArena queue. Prepare for your next duel!".format(loser.name))

    def move_player_to_team(self, player, team):
        if team == "spectator":
            self.player_spec.add(player.steam_id)
        else:
            setattr(self, "player_" + team, player)
        player.put(team)

    def handle_map_change(self, mapname, factory):
        self.duelarenastrategy = AutoDuelArenaStrategy(MIN_ACTIVE_PLAYERS)
        self.duelvotes = set()
        self.duelmode = False
        self.initduel = False

    def init_duel(self):

        self.checklists()
        self.init_duel_team_scores()  # set all player scores 0

        for sid in self.playerset - set(self.queue):
            self.queue.insert(0, sid)

        teams = Plugin.teams()

        player1 = Plugin.player(self.queue.pop())
        player2 = Plugin.player(self.queue.pop())

        # both players already on different teams? Do nothing
        if (player2.team != 'blue' or player1.team != 'red') and \
                (player2.team != 'red' or player1.team != 'blue'):
            # only one player already in any team?
            if player1.team == 'red':
                self.move_player_to_team(player2, "blue")
            elif player1.team == 'blue':
                self.move_player_to_team(player2, "red")
            elif player2.team == 'blue':
                self.move_player_to_team(player1, "red")
            elif player2.team == 'red':
                self.move_player_to_team(player1, "blue")
            # both players not in teams?
            else:
                self.move_player_to_team(player1, "red")
                self.move_player_to_team(player2, "blue")

        # put all other players to spec
        for player in set(teams['red'] + teams['blue']) - {player1, player2}:
            self.move_player_to_team(player, "spectator")

        self.initduel = False

    def duelarena_switch(self):
        self.checklists()

        if self.duelmode and self.duelarena_should_be_aborted(self.game, self.playerset, self.scores):
            self.deactivate_duelarena()

        if not self.duelmode and self.duelarena_should_be_activated():
            self.activate_duelarena()
        elif self.duelmode and not self.duelarena_should_be_activated():
            self.deactivate_duelarena()

    def duelarena_should_be_aborted(self, game, playerset, scores):
        return self.duelarenastrategy.duelarena_should_be_aborted(game, playerset, scores)

    def duelarena_should_be_activated(self):
        return self.duelarenastrategy.duelarena_should_be_activated(self.playerset)

    def deactivate_duelarena(self):
        self.duelarenastrategy = AutoDuelArenaStrategy(MIN_ACTIVE_PLAYERS)
        self.duelmode = False
        self.initduel = False
        Plugin.msg("DuelArena has been deactivated!")
        Plugin.center_print("DuelArena deactivated!")
        if self.game.state == "in_progress":
            self.print_reset_scores = True

    def activate_duelarena(self):
        self.duelmode = True
        self.print_reset_scores = False
        Plugin.msg(
            "DuelArena activated! Round winner stays in, loser rotates with spectator. Hit 8 rounds first to win!")
        Plugin.center_print("DuelArena activated!")
        if self.game.state == "in_progress":
            self.initduel = True

    def checklists(self):
        self.queue[:] = [sid for sid in self.queue if Plugin.player(sid) and Plugin.player(sid).ping < 990]
        self.playerset = set([sid for sid in self.playerset if Plugin.player(sid) and Plugin.player(sid).ping < 990])

    def reset_team_scores(self):
        if self.game.state != "in_progress":
            return

        self.game.addteamscore('red', -self.game.red_score)
        self.game.addteamscore('blue', -self.game.blue_score)

    def init_duel_team_scores(self):
        self.reset_team_scores()
        self.scores = {player_id: 0 for player_id in self.playerset}

    def print_results(self):
        Plugin.msg("DuelArena results:")
        place = 0
        prev_score = -1
        for (steam_id, score) in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            if score != prev_score:
                place += 1
            prev_score = score
            player = Plugin.player(steam_id)
            if player:
                Plugin.msg("Place ^3{}.^7 {} ^7(Wins:^2{}^7)".format(place, player.name, score))
            else:
                Plugin.msg("Place ^3{}.^7 <Player disconnected> ^7(Wins:^2{}^7)".format(place, score))

    def cmd_duelarena(self, player, msg, channel):

        if len(msg) < 2 or msg[1] not in ["auto", "force"]:
            state = self.duelarenastrategy.state
            Plugin.msg("Current DuelArena state is: ^6{}".format(state))
            return minqlx.RET_USAGE
        if msg[1] == "force":
            self.duelarenastrategy = ForcedDuelArenaStrategy(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS)
            Plugin.msg("^7Duelarena is now ^6forced^7!")
        elif msg[1] == "auto":
            self.duelarenastrategy = AutoDuelArenaStrategy(MIN_ACTIVE_PLAYERS)
            Plugin.msg("^7Duelarena is now ^6automatic^7!")
        self.duelarena_switch()

    def cmd_duel(self, player, msg, channel):

        if self.duelmode:
            Plugin.msg("^7DuelArena already active!")
            return

        if self.game.state != "warmup":
            Plugin.msg("^7DuelArena votes only allowed in warmup!")
            return

        connected_players = len(self.connected_players())

        if connected_players not in range(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS + 1):
            Plugin.msg("^6!duel^7 votes only available with ^6{}-{}^7 players connected"
                       .format(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS))
            return

        if player.steam_id in self.duelvotes:
            Plugin.msg("{}^7 you already voted for DuelArena!".format(player.name))
            return

        self.duelvotes.add(player.steam_id)

        have = len(self.duelvotes)
        need = floor(connected_players / 2) + 1
        votes_left = need - have

        if votes_left > 0:
            Plugin.msg(
                "^7Total DuelArena votes = ^6{}^7, but I need ^6{}^7 more to activate DuelArena."
                .format(have, votes_left))
            return

        Plugin.msg("^7Total DuelArena votes = ^6{}^7, vote passed!".format(have))
        Plugin.play_sound("sound/vo/vote_passed.ogg")
        self.duelarenastrategy = ForcedDuelArenaStrategy(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS)
        self.duelarena_switch()

    def connected_players(self):
        teams = Plugin.teams()
        return teams["red"] + teams["blue"] + teams["spectator"]


class DuelArenaStrategy:

    @property
    def state(self):
        """
        :rtype: str
        """
        pass

    @abstractmethod
    def duelarena_should_be_activated(self, playerset):
        """
        :rtype: bool
        """
        pass

    def duelarena_should_be_aborted(self, game, playerset, scores):
        if not game or game.state != "in_progress":
            return False

        if len(playerset) <= MAX_ACTIVE_PLAYERS:
            return False

        return len(scores) == 0 or max(scores.values()) < 6


class AutoDuelArenaStrategy(DuelArenaStrategy):

    def __init__(self, min_active_players):
        super().__init__()

        self.min_active_players = min_active_players

    @property
    def state(self):
        return "auto"

    def duelarena_should_be_activated(self, playerset):
        return len(playerset) == self.min_active_players


class ForcedDuelArenaStrategy(DuelArenaStrategy):

    def __init__(self, min_active_players, max_active_players):
        super().__init__()

        self.min_active_players = min_active_players
        self.max_active_players = max_active_players

    @property
    def state(self):
        return "force"

    def duelarena_should_be_activated(self, playerset):
        return len(playerset) in range(self.min_active_players, self.max_active_players + 1)
