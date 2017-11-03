import minqlx

MIN_ACTIVE_PLAYERS = 3  # with <3 connected and subscribed players we deactive DuelArena
MAX_ACTIVE_PLAYERS = 5  # with >5 connected players we deactivate DuelArena

DUEL_ARENA_ANNOUNCEMENT = "Type ^6!d ^7for DuelArena!"


class duelarena(minqlx.Plugin):
    """DuelArena will start automatically if at least 3 players opted in (!duel or !d) to the queue.

    DuelArena will be deactivated automatically if connected players exceed the player_limit (default 5),
    or if there are only 2 players left, or if too many players opted out.
    """

    def __init__(self):
        self.add_hook("team_switch_attempt", self.handle_team_switch_event)
        self.add_hook("player_disconnect", self.handle_player_disco)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)
        self.add_command(("duel", "d"), self.cmd_duel)
        self.add_command(("queue", "q"), self.cmd_printqueue)

        self.duelmode = False  # global gametype switch
        self.initduel = False  # initial player setup switch
        self.psub = []  # steam_ids of players subscribed to DuelArena
        self.queue = []  # queue for rotating players
        self.switching_players = []  # force spec exception for these players
        self.scores = {}

    # Don't allow players to join manually when DuelArena is active
    def handle_team_switch_event(self, player, old, new):
        if not self.duelmode:
            return
        if not self.game:
            return
        if self.game.state == "warmup":
            return

        # If we initiated this switch, allow it
        if player in self.switching_players:
            self.restore_score(player)
            self.switching_players.remove(player)
            return

        # If they wanted to join a team, halt this hook at enginge-level and other hooks from being called
        if new in ['red', 'blue']:
            player.tell(
                "Server is in DuelArena mode. You will automatically join. "
                "Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")
            return minqlx.RET_STOP_ALL

    def restore_score(self, player):
        if player.steam_id not in self.scores:
            return
        player.score = self.scores[player.steam_id]

    # When a player connects, display them a message and check if we should switch duel arena
    @minqlx.delay(4)
    def handle_player_connect(self, player):
        self.undelayed_handle_player_connected_or_disconnected(player)

    # When a player disconnects, display them a message and check if we should switch duel arena
    @minqlx.delay(3)
    def handle_player_disco(self, player, reason):
        self.undelayed_handle_player_connected_or_disconnected(player)

    def undelayed_handle_player_connected_or_disconnected(self, player):
        self.switch_duelarena_if_necessary()

        if self.duelmode:
            self.delete_saved_score_of(player)
            return

        player_count = self.count_connected_players()

        if player_count == MIN_ACTIVE_PLAYERS or player_count == MAX_ACTIVE_PLAYERS:
            self.center_print(DUEL_ARENA_ANNOUNCEMENT)
            self.msg(DUEL_ARENA_ANNOUNCEMENT)

    def switch_duelarena_if_necessary(self):
        self.checklists()

        if self.duelmode and not self.should_duelmode_be_activated():
            self.deactivate_duelarena_mode()
            return

        if not self.duelmode and self.should_duelmode_be_activated():
            self.activate_duelarena_mode()

    def delete_saved_score_of(self, player):
        if player.steam_id in self.scores:
            del self.scores[player.steam_id]

    def checklists(self):
        self.queue[:] = [sid for sid in self.queue if self.player(sid) and self.player(sid).ping < 990]
        self.psub[:] = [sid for sid in self.psub if self.player(sid) and self.player(sid).ping < 990]

    def should_duelmode_be_activated(self):
        player_count = self.count_connected_players()

        return player_count in range(MIN_ACTIVE_PLAYERS, MAX_ACTIVE_PLAYERS + 1) \
            and len(self.psub) >= MIN_ACTIVE_PLAYERS

    def deactivate_duelarena_mode(self):
        self.duelmode = False
        self.msg("DuelArena has been deactivated! You are free to join.")

    def activate_duelarena_mode(self):
        self.duelmode = True
        self.msg("DuelArena activated!")
        self.center_print("DuelArena activated!")
        if self.game and self.game.state == "in_progress":
            self.initduel = True

    def count_connected_players(self):
        return len(self.players())

    def handle_round_countdown(self, *args, **kwargs):
        if not self.duelmode:
            return

        self.center_print(self.round_announcement())

    def round_announcement(self):
        teams = self.teams()
        return "{} ^2vs {}".format(teams["red"][-1].name, teams["blue"][-1].name)

    # When a game is about to start and duelmode is active, initialize
    @minqlx.delay(3)
    def handle_game_countdown(self):
        self.undelayed_handle_game_countdown()

    def undelayed_handle_game_countdown(self):
        if not self.duelmode:
            return
        self.init_duel()

    def init_duel(self):
        self.checklists()

        self.insert_subscribed_players_to_queue_if_necessary()
        self.scores = {}

        player1 = self.player(self.queue.pop())
        player2 = self.player(self.queue.pop())
        self.move_players_to_teams(player1, player2)

        self.move_all_non_playing_players_to_spec(player1, player2)

        self.initduel = False

    def insert_subscribed_players_to_queue_if_necessary(self):
        for player in [steam_id for steam_id in self.psub if steam_id not in self.queue]:
            self.append_player_to_end_of_queue(player)

    def append_player_to_end_of_queue(self, player):
        self.queue.insert(0, player)

    def move_players_to_teams(self, player1, player2):
        teams = self.teams()

        if player1 in teams["red"]:
            if player2 not in teams["blue"]:
                self.put_player_on_team(player2, "blue")
            return

        if player1 in teams["blue"]:
            if player2 not in teams["red"]:
                self.put_player_on_team(player2, "red")
            return

        if player2 in teams["blue"]:
            self.put_player_on_team(player1, "red")
            return

        if player2 in teams["red"]:
            self.put_player_on_team(player1, "blue")
            return

        self.put_player_on_team(player1, "red")
        self.put_player_on_team(player2, "blue")

    def put_player_on_team(self, player, team):
        self.switching_players.append(player)
        player.put(team)

    def move_all_non_playing_players_to_spec(self, *players):
        teams = self.teams()

        for player in [player for player in teams['red'] + teams['blue'] if player not in players]:
            player.put("spectator")

    def handle_game_end(self, data):
        if not self.game:
            return
        if not self.duelmode:
            return

        # put both players back to the queue, winner first position, loser last position
        winner, loser = self.extract_winning_and_losing_team_from_game_end_data(data)

        teams = self.teams()

        self.append_player_to_end_of_queue(teams[loser][-1].steam_id)
        self.queue.append(teams[winner][-1].steam_id)

    def extract_winning_and_losing_team_from_game_end_data(self, data):
        if int(data['TSCORE1']) > int(data['TSCORE0']):
            return "blue", "red"
        return "red", "blue"

    @minqlx.delay(1.5)
    def handle_round_end(self, data):
        self.undelayed_handle_round_end(data)

    def undelayed_handle_round_end(self, data):
        # Not in CA? Do nothing
        if (not self.game) or (self.game.type_short != "ca"):
            return

        # Last round? Do nothing
        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.initduel:
            self.init_duel()
            return

        if not self.duelmode:
            return

        losing_team = self.extract_losing_team_from_round_end_data(data)
        if losing_team is None:
            return  # Draw? Do nothing

        next_player = self.next_player()

        if next_player is None:
            self.deactivate_duelarena_mode()
            return

        losing_player = self.weakest_player_on(losing_team)

        self.put_player_on_team(next_player, losing_team)
        self.save_scores(losing_player)
        self.put_player_to_spectators_and_back_in_duel_queue(losing_player)

    def extract_losing_team_from_round_end_data(self, data):
        if data["TEAM_WON"] == "RED":
            return "blue"
        if data["TEAM_WON"] == "BLUE":
            return "red"
        return None

    def next_player(self):
        next_player = self.player(self.queue.pop())

        teams = self.teams()

        while not next_player or next_player not in teams['spectator']:
            try:
                next_player = self.player(self.queue.pop())
            except IndexError:
                return None
        return next_player

    def weakest_player_on(self, losing_team):
        teams = self.teams()
        return teams[losing_team][-1]

    def save_scores(self, player):
        self.scores[player.steam_id] = player.score

    def put_player_to_spectators_and_back_in_duel_queue(self, losing_player):
        self.append_player_to_end_of_queue(losing_player.steam_id)
        losing_player.put("spectator")

    def cmd_duel(self, player, msg, channel):
        if self.count_connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!duel^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        self.checklists()

        if self.player_is_subscribed(player):
            self.unsubscribe_player(player)
            self.msg("{} ^7left DuelArena.".format(player.name))
            self.printqueue()
            if not self.should_duelmode_be_activated():
                self.deactivate_duelarena_mode()
            return

        self.subscribe_player(player)
        if not self.should_duelmode_be_activated():
            self.msg(
                "{} ^7entered the DuelArena queue. ^6{}^7 more players needed to start DuelArena. "
                "Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue."
                .format(player.name, MIN_ACTIVE_PLAYERS - len(self.psub)))
            self.printqueue()
            return

        self.msg(
            "{} ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.".format(player.name))
        self.printqueue()
        self.activate_duelarena_mode()

    def player_is_subscribed(self, player):
        return player.steam_id in self.psub

    def unsubscribe_player(self, player):
        if self.player_is_enqueued(player):
            self.queue.remove(player.steam_id)
        self.psub.remove(player.steam_id)

    def player_is_enqueued(self, player):
        return player.steam_id in self.queue

    def printqueue(self):
        if len(self.queue) == 0:
            self.msg("There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")
            return

        qstring = ""

        for steam_id in self.queue:
            player = self.player(steam_id)
            indicator = self.position_of_player_in_queue(player)
            place = "{}th".format(indicator)
            if indicator == 1:
                place = "1st"
            elif indicator == 2:
                place = "2nd"
            elif indicator == 3:
                place = "3rd"
            qstring = "^6{}^7: {} ".format(place, player.name) + qstring

        self.msg("DuelArena queue: {}".format(qstring))

    def position_of_player_in_queue(self, player):
        return len(self.queue) - self.queue.index(player.steam_id)

    def subscribe_player(self, player):
        if not self.player_is_enqueued(player):  # check: this condition will never (or shouldn't) be False.
            self.append_player_to_end_of_queue(player.steam_id)
        self.psub.append(player.steam_id)

    def cmd_printqueue(self, player, msg, channel):
        if self.count_connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!queue^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        self.printqueue()
