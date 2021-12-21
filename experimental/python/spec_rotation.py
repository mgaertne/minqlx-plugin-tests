import minqlx

from minqlx.database import Redis


class spec_rotation(minqlx.Plugin):
    def __init__(self):
        super().__init__()

        self.add_hook("map", self.handle_map_change)
        self.add_hook("client_command", self.handle_client_command)
        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("player_loaded", self.handle_player_loaded)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_start", self.handle_game_start)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)

        self.stats_snapshot = {}
        self.scheduled_switches = []
        self.spec_rotation = []
        self.score_snapshots = {}

        self.in_countdown = False

    def handle_map_change(self, mapname, factory):
        self.in_countdown = False
        self.stats_snapshot = {}
        self.scheduled_switches = []
        self.spec_rotation = []
        self.score_snapshots = {}

    def handle_client_command(self, player, command):
        @minqlx.thread
        def handler():
            if command == "team s":
                if player.steam_id in self.spec_rotation:
                    self.spec_rotation.remove(player.steam_id)
                    player.tell("You have been removed from the auto-rotation.")
                    player.center_print("You are set to spectate only")

        self.logger.debug("{}: {}".format(player, command))
        handler()

    def handle_team_switch_attempt(self, player, old_team, new_team):
        if not self.game or self.game.state != "in_progress":
            return

        teams = self.teams()

        if len(teams["red"]) != len(teams["blue"]):
            return

        if len(teams["red"]) == 1 or len(teams["blue"]) == 1:
            return

        if new_team in ["red", "blue", "any"] and len(self.spec_rotation) == 0:
            self.spec_rotation.append(player.steam_id)

        if new_team not in ["red", "blue", "any"] or player.steam_id not in self.spec_rotation:
            return

        player.tell(
            "{}^7, you will be automatically exchanged with the weakest player on the losing team next round.".format(
                player.name))
        return minqlx.RET_STOP_ALL

    def handle_team_switch(self, player, old_team, new_team):
        if not self.game:
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.in_countdown and old_team in ["red", "blue"] and new_team == "spectator":
            if player.steam_id not in self.spec_rotation:
                self.spec_rotation.append(player.steam_id)
            player.tell(
                "{}^7, you will automatically rotate with the weakest player on the losing team next round.".format(
                    player.name))

        if self.game.state != "in_progress":
            return

        if len(self.spec_rotation) == 0:
            return

        if player.steam_id in self.scheduled_switches:
            self.scheduled_switches.remove(player.steam_id)
            return

        teams = self.teams()
        if len(teams["red"]) == 1 or len(teams["blue"]) == 1:
            return

        if len(teams["red"]) == len(teams["blue"]):
            return

        if new_team in ["red", "blue"] and old_team == "spectator" and player.steam_id not in self.spec_rotation:
            other_team = self.other_team(new_team)
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, other_team,
                               msg="Disabling spec rotation since there are enough players now.")
            return

        if new_team == "spectator" and old_team in ["red", "blue"] and player.steam_id not in self.spec_rotation:
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, player.team)

    def switch_player(self, steam_id, team, msg=None):
        switching_player = self.player(steam_id)
        if not switching_player:
            return

        self.logger.debug("steam_id: {} team: {} snapshots: {}".format(steam_id, team, self.score_snapshots))
        if team == "spectator":
            self.score_snapshots[steam_id] = switching_player.score

        self.scheduled_switches.append(steam_id)
        switching_player.put(team)

        if msg is not None:
            switching_player.tell(msg)

        if steam_id not in self.score_snapshots or team == "spectator":
            return

        switching_player.score = self.score_snapshots[steam_id]

    @minqlx.delay(3)
    def handle_player_loaded(self, player):
        if not self.game or self.game.state != "in_progress":
            return

        teams = self.teams()
        if len(teams["red"]) != len(teams["blue"]):
            return

        if len(teams["red"]) == 1:
            return

        if len(self.spec_rotation) != 0:
            return

        player.tell(
            "{}, join to activate spec rotation! Player with fewest damage on losing team will be rotated with you."
            .format(player.name))

    def handle_player_disconnect(self, player, reason):
        if not self.game or self.game.state != "in_progress":
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if player.steam_id in self.spec_rotation:
            self.spec_rotation.remove(player.steam_id)
            return

        if player.team in ["red", "blue"] and len(self.spec_rotation) > 0:
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, player.team)

    def handle_game_countdown(self):
        self.in_countdown = True

        teams = self.teams()
        if len(teams["red"]) == 1 or len(teams["blue"]) == 1:
            return

        if len(teams["red"]) == len(teams["blue"]):
            return

        bigger_team = "blue"
        if len(teams["red"]) > len(teams["blue"]):
            bigger_team = "red"

        spec_player = self.find_player_to_spec(teams[bigger_team])
        self.spec_rotation.append(spec_player.steam_id)
        spec_player.put("spectator")

    def handle_game_start(self, data):
        self.logger.debug("game_start: {}".format(data))

        self.in_countdown = False

    def find_player_to_spec(self, players):
        return min(players, key=lambda _player: self.find_games_here(_player))

    def find_games_here(self, player):
        completed_key = "minqlx:players:{}:games_completed"

        if not self.db.exists(completed_key.format(player.steam_id)):
            return 0

        return int(self.db[completed_key.format(player.steam_id)])

    def handle_round_countdown(self, round_number):
        teams = self.teams()
        if len(teams["red"]) == 1 or len(teams["blue"]) == 1:
            return

        if len(teams["red"]) == len(teams["blue"]):
            return

        bigger_team = "blue"
        if len(teams["red"]) > len(teams["blue"]):
            bigger_team = "red"

        smaller_team = self.other_team(bigger_team)

        if len(self.spec_rotation) > 0:
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, smaller_team)
            return

    def handle_round_start(self, round_number):
        teams = self.teams()
        self.stats_snapshot = {player.steam_id: player.stats.damage_dealt for player in teams["red"] + teams["blue"]}

    def handle_round_end(self, data):
        if self.game is None:
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        teams = self.teams()
        if len(teams["red"]) <= 1 or len(teams["blue"]) <= 1:
            return

        if len(self.spec_rotation) == 0:
            return

        if len(self.stats_snapshot) == 0 and data["ROUND"] > 1:
            return

        winning_team = data['TEAM_WON'].lower()

        if winning_team == "draw":
            return

        losing_team = self.other_team(winning_team)

        player_to_replace = self.player_to_replace(losing_team)
        spec_player = self.player(player_to_replace)

        next_steam_id = self.spec_rotation.pop(0)
        next_player = self.player(next_steam_id)

        if next_player is None:
            return

        if next_player.team != "spectator":
            return

        self.msg(
            "Replacing player with fewest round damage on team {}^7 {}^7 with the next player from the rotation {}^7."
            .format(losing_team, spec_player.name, next_player.name))
        self.switch_player(next_steam_id, losing_team)
        self.spec_rotation.append(spec_player.steam_id)
        self.switch_player(spec_player.steam_id, "spectator",
                           msg="{}^7, you will automatically rotate with the weakest player "
                               "on the losing team next round."
                           .format(spec_player.name))

    def other_team(self, team):
        if team == "red":
            return "blue"
        if team == "blue":
            return "red"
        return "draw"

    def calculate_damage_deltas(self):
        returned = {}

        for steam_id in self.stats_snapshot:
            minqlx_player = self.player(steam_id)

            if minqlx_player is None:
                continue

            returned[steam_id] = minqlx_player.stats.damage_dealt - self.stats_snapshot[steam_id]

        return returned

    def player_to_replace(self, losing_team):
        damage_this_round = self.calculate_damage_deltas()

        teams = self.teams()

        losing_steam_ids = teams[losing_team]

        losing_steam_ids.sort(key=lambda player: self.damage_this_round(damage_this_round, player.steam_id))

        return losing_steam_ids[0]

    def damage_this_round(self, damages, steam_id):
        if steam_id not in damages:
            return 0

        return damages[steam_id]
