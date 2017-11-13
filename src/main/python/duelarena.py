# DuelArena will start automatically with 3 players

import minqlx


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
        self.add_command("duelarena", self.cmd_duelarena, 1, usage="[auto|force]")

        self.forceduel = False  # False: Start Duelarena automatically, True: Force Duelarena
        self.duelmode = False  # global gametype switch
        self.initduel = False  # initial player setup switch
        self.playerset = []  # collect players who joined a team
        self.queue = []  # queue for rotating players
        self.player_red = None  # force spec exception for this player
        self.player_blue = None  # force spec exception for this player
        self.player_spec = None  # force spec exception for this player
        self.scores = {}  # store/restore individual team scores

        # initialize playerset on plugin reload
        teams = self.teams()
        for _p in teams['red'] + teams['blue']:
            if _p.steam_id not in self.playerset:
                self.playerset.append(_p.steam_id)

    # Don't allow players to join manually when DuelArena is active
    def handle_team_switch_event(self, player, old, new):

        if not self.game:
            return

        if new in ['red', 'blue', 'any'] and player.steam_id not in self.playerset:
            self.playerset.append(player.steam_id)  # player joined a team? Add him to playerset
            self.duelarena_switch(player)  # we good enough for DuelArena?
        elif new in ['spectator'] \
                and player.steam_id in self.playerset:  # player left team? let's see what we do with him...
            if player.steam_id != self.player_spec:  # player initiated switch to spec? Remove him from playerset
                self.playerset.remove(player.steam_id)
                self.duelarena_switch(player)
            else:  # player.steam_id == self.player_spec:
                #  we initiated switch to spec? Only remove him from exception list
                self.player_spec = None

        if self.game.state == "warmup" and len(self.playerset) == 3:
            self.center_print("Ready up for ^6DuelArena^7!")
            self.msg("Ready up for ^6DuelArena^7! Round winner stays in, loser rotates with spectator.")
            return
        elif self.game.state == "warmup":
            return

        if not self.duelmode:
            return

        # If we initiated this switch, allow it
        if player == self.player_red or player == self.player_blue:
            self.player_red = None
            self.player_blue = None
            return

        # If they wanted to join a team, halt this hook at enginge-level and other hooks from being called
        if new in ['red', 'blue', 'any']:
            player.tell("Server is now in ^6DuelArena^7 mode. You will automatically rotate with round loser.")
            return minqlx.RET_STOP_ALL

    # Announce next duel
    def handle_round_countdown(self, round_number):
        if self.duelmode:
            teams = self.teams()
            if teams["red"] and teams["blue"]:
                self.center_print("{} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))
                self.msg("DuelArena: {} ^2vs^7 {}".format(teams["red"][-1].name, teams["blue"][-1].name))

    # check if we need to deavtivate DuelArena on player disconnect
    @minqlx.delay(3)
    def handle_player_disco(self, player, reason):
        if player.steam_id in self.playerset:
            self.playerset.remove(player.steam_id)
            self.duelarena_switch()

    @minqlx.delay(3)
    def handle_player_loaded(self, player):
        if player.team == "spectator" and len(self.playerset) == 2:
            player.tell("{}, join to activate DuelArena! Round winner stays in, loser rotates with spectator.".format(
                player.name))

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
        if self.duelmode:

            if int(data['TSCORE1']) > int(data['TSCORE0']):
                loser = "red"
                winner = "blue"
            else:
                loser = "blue"
                winner = "red"

            teams = self.teams()

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
        if (self.game is None) or (self.game.type_short != "ca"):
            return

        # Last round? Do nothing except adding last score point to winner
        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.initduel:
            self.init_duel()
            return

        if self.duelmode:

            teams = self.teams()

            if data['TEAM_WON'] == 'RED':
                empty_team = 'blue'
                loser_team_score = self.game.blue_score
                winner = teams['red'][-1]
                self.scores[winner.steam_id] = self.game.red_score
            elif data['TEAM_WON'] == 'BLUE':
                empty_team = 'red'
                loser_team_score = self.game.red_score
                winner = teams['blue'][-1]
                self.scores[winner.steam_id] = self.game.blue_score
            else:
                return  # Draw? Do nothing

            next_player = self.queue.pop()

            _p = self.player(next_player)

            if _p.team != "spectator":
                self.duelmode = False
                return

            self.player_blue = _p
            self.player_red = _p
            loser = teams[empty_team][-1]
            _p.put(empty_team)
            self.game.addteamscore(empty_team, self.scores[next_player] - loser_team_score)
            self.queue.insert(0, loser.steam_id)
            self.player_spec = loser.steam_id
            self.scores[loser.steam_id] = loser_team_score  # store loser team score
            loser.put("spectator")
            loser.tell(
                "{}, you've been put back to DuelArena queue. Prepare for your next duel!".format(loser.name))

    def init_duel(self):

        self.checklists()
        self.init_duel_team_scores()  # set all player scores 0

        for sid in self.playerset:
            if sid not in self.queue:
                self.queue.insert(0, sid)

        teams = self.teams()

        self.player_red = self.player(self.queue.pop())
        self.player_blue = self.player(self.queue.pop())

        # both players already on different teams? Do nothing
        if (self.player_blue.team != 'blue' or self.player_red.team != 'red') and \
                (self.player_blue.team != 'red' or self.player_red.team != 'blue'):
            # only one player already in any team?
            if self.player_red.team == 'red':
                self.player_blue.put("blue")
            elif self.player_red.team == 'blue':
                self.player_blue.put("red")
            elif self.player_blue.team == 'blue':
                self.player_red.put("red")
            elif self.player_blue.team == 'red':
                self.player_red.put("blue")
            # both players not in teams?
            else:
                self.player_red.put("red")
                self.player_blue.put("blue")

        # put all other players to spec
        for _p in teams['red'] + teams['blue']:
            if _p != self.player_red and _p != self.player_blue:
                _p.put("spectator")

        self.initduel = False

    def duelarena_switch(self, player=None):

        self.checklists()

        # admin forced Duelarena?
        if self.forceduel:
            if not self.duelmode and len(self.playerset) > 2:
                self.duelmode = True
                if self.game.state == "in_progress":
                    self.initduel = True
            elif self.duelmode and len(self.playerset) < 3:
                self.duelmode = False
                self.initduel = False
                if self.game.state == "in_progress":
                    self.print_results()
                    self.reset_team_scores()
            return

        # Main conditions not true? Skip the switch
        if not self.duelmode and len(self.playerset) != 3:
            return

        if self.duelmode:
            if len(self.playerset) != 3:
                self.duelmode = False
                self.initduel = False
                self.msg("DuelArena has been deactivated!")
                self.center_print("DuelArena deactivated!")
                if self.game.state == "in_progress":
                    self.print_results()
                    self.reset_team_scores()
        else:  # we already left the switch for the relevant cases
            self.duelmode = True
            self.msg("DuelArena activated! Round winner stays in, loser rotates with spectator.")
            self.center_print("DuelArena activated!")
            if self.game and self.game.state == "in_progress":
                if player:
                    # Player switched into a team and game is already in progress? Give him first queue position!
                    self.queue.append(player.steam_id)
                self.initduel = True

        minqlx.console_command(
            "echo duelarena_switch: duelmode={}, len_playerset={}, initduel={}".format(self.duelmode,
                                                                                       len(self.playerset),
                                                                                       self.initduel))

    def checklists(self):

        self.queue[:] = [sid for sid in self.queue if self.player(sid) and self.player(sid).ping < 990]
        self.playerset[:] = [sid for sid in self.playerset if self.player(sid) and self.player(sid).ping < 990]

    def reset_team_scores(self):
        if self.game.state == "in_progress":
            self.game.addteamscore('red', -self.game.red_score)
            self.game.addteamscore('blue', -self.game.blue_score)

    def init_duel_team_scores(self):
        self.reset_team_scores()
        self.scores = {}
        for sid in self.playerset:
            self.scores[sid] = 0

    def print_results(self):
        self.msg("DuelArena results:")
        place = 0
        prev_score = -1
        for pscore in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            if pscore[1] != prev_score:
                place += 1
            prev_score = pscore[1]
            player = self.player(pscore[0])
            if player:
                self.msg("Place ^3{}.^7 {} ^7(Wins:^2{}^7)".format(place, player.name, pscore[1]))

    def cmd_duelarena(self, player, msg, channel):

        if len(msg) < 2 or msg[1] not in ["auto", "force"]:
            state = "auto"
            if self.forceduel:
                state = "force"
            self.msg("Current DuelArena state is: ^6{}".format(state))
            return minqlx.RET_USAGE
        if msg[1] == "force":
            self.forceduel = True
            self.msg("^7Duelarena is now ^6forced^7!")
        elif msg[1] == "auto":
            self.forceduel = False
            self.msg("^7Duelarena is now ^6automatic^7!")
        self.duelarena_switch()
