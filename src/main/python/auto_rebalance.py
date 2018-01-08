"""
This is a plugin created by ShiN0
Copyright (c) 2018 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one, except for the version related code.

This plugin automatically rebalances new-joiners at round start based upon the ratings in the balance plugin.

It's intended to run with the default balance plugin, and will print an error on every round countdown if the
balance plugin is not loaded together with this one.
"""
import minqlx
from minqlx import Plugin

DEFAULT_RATING = 1500
SUPPORTED_GAMETYPES = ("ca", "ctf", "dom", "ft", "tdm", "duel", "ffa")


class auto_rebalance(minqlx.Plugin):
    """
    Auto rebalance plugin for minqlx

    Rebalances new players joined since the last round countdown based upon the ratings in the balance plugin to yield
    better balanced teams overall.

    Uses:
    * qlx_rebalanceScoreDiffThreshold (default: "3") The difference between red team score and blue team score
    threshold that will trigger a team switch suggestion at round end.
    * qlx_rebalanceWinningStreakThreshold (default: "3") The Threshold when a team is on a winning streak for
    winning this amount of round in a row that will trigger a team switch suggestion at round end.

    """
    def __init__(self):
        """
        default constructor, adds the plugin hooks and initializes variables used
        """
        super().__init__()
        self.last_new_player_id = None

        Plugin.set_cvar_once("qlx_rebalanceScoreDiffThreshold", "3")
        Plugin.set_cvar_once("qlx_rebalanceWinningStreakThreshold", "3")

        self.rebalance_score_diff_suggestion_threshold = Plugin.get_cvar("qlx_rebalanceScoreDiffThreshold", int)
        self.rebalance_winning_streak_suggestion_threshold = Plugin.get_cvar("qlx_rebalanceWinningStreakThreshold", int)

        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)
        self.add_hook("round_start", self.handle_round_start, priority=minqlx.PRI_LOWEST)
        self.add_hook("round_end", self.handle_round_end, priority=minqlx.PRI_LOWEST)
        self.add_hook("game_start", self.handle_game_start)
        self.winning_teams = []

        self.plugin_version = "{} Version: {}".format(self.name, "v0.0.9")
        self.logger.info(self.plugin_version)

    def handle_team_switch_attempt(self, player, old, new):
        """
        Handles the case where a player switches from spectators to "red", "blue", or "any" team, and
        the resulting teams would be sub-optimal balanced.

        :param player: the player that attempted the switch
        :param old: the old team of the switching player
        :param new: the new team that swicthting player would be put onto

        :return minqlx.RET_NONE if the team switch should be allowed or minqlx.RET_STOP_EVENT if the switch should not
        be allowed, and we put the player on a better-suited team.
        """
        if not self.game:
            return minqlx.RET_NONE

        if self.last_new_player_id == player.steam_id and new in ["spectator", "free"]:
            self.last_new_player_id = None

        if self.game.state != "in_progress":
            return minqlx.RET_NONE

        if old not in ["spectator", "free"] or new not in ['red', 'blue', 'any']:
            return minqlx.RET_NONE

        if "balance" not in self.plugins:
            Plugin.msg("^1balance^7 plugin not loaded, ^1auto rebalance^7 not possible.")
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        teams = self.teams()
        if len(teams["red"]) == len(teams["blue"]):
            self.last_new_player_id = player.steam_id
            return minqlx.RET_NONE

        if not self.last_new_player_id:
            return minqlx.RET_NONE

        last_new_player = Plugin.player(self.last_new_player_id)
        if not last_new_player:
            self.last_new_player_id = None
            return minqlx.RET_NONE

        other_than_last_players_team = self.other_team(last_new_player.team)
        new_player_team = teams[other_than_last_players_team].copy() + [player]
        proposed_diff = self.calculate_player_average_difference(gametype,
                                                                 teams[last_new_player.team].copy(),
                                                                 new_player_team)

        alternative_team_a = [player for player in teams[last_new_player.team] if player != last_new_player] + \
                             [player]
        alternative_team_b = teams[other_than_last_players_team].copy() + [last_new_player]
        alternative_diff = self.calculate_player_average_difference(gametype,
                                                                    alternative_team_a,
                                                                    alternative_team_b)

        self.last_new_player_id = None
        if proposed_diff > alternative_diff:
            last_new_player.tell(
                "{}, you have been moved to {} to maintain team balance.".format(last_new_player.clean_name,
                                                                                 self.format_team(
                                                                                     other_than_last_players_team)))
            last_new_player.put(other_than_last_players_team)
            if new in [last_new_player.team]:
                return minqlx.RET_NONE
            player.tell("{}, you have been moved to {} to maintain team balance.".format(player.clean_name,
                                                                                         self.format_team(
                                                                                             last_new_player.team)))
            player.put(last_new_player.team)
            return minqlx.RET_STOP_ALL

        if new not in ["any", other_than_last_players_team]:
            player.put(other_than_last_players_team)
            return minqlx.RET_STOP_ALL

        return minqlx.RET_NONE

    def other_team(self, team):
        """
        Calculates the other playing team based upon the provided team string.

        :param team: the team the other playing team should be determined for

        :return the other playing team based upon the provided team string
        """
        if team == "red":
            return "blue"
        return "red"

    def format_team(self, team):
        if team == "red":
            return "^1red^7"
        if team == "blue":
            return "^4blue^7"

        return "^3{}^7".format(team)

    def calculate_player_average_difference(self, gametype, team1, team2):
        """
        calculates the difference between the team averages of the two provided teams for the given gametype

        the result will be absolute, i.e. always be greater then or equal to 0

        :param gametype: the gametype to calculate the teams' averages for
        :param team1: the first team to calculate the team averages for
        :param team2: the second team to calculate the team averages for

        :return the absolute difference between the two team's averages
        """
        team1_avg = self.team_average(gametype, team1)
        team2_avg = self.team_average(gametype, team2)
        return abs(team1_avg - team2_avg)

    def team_average(self, gametype, team):
        """
        Calculates the average rating of a team.

        :param gametype: the gametype to determine the ratings for
        :param team: the list of players the average should be calculated for

        :return the average rating for the given team and gametype
        """
        if not team or len(team) == 0:
            return 0

        ratings = self.plugins["balance"].ratings

        average = 0
        for p in team:
            if p.steam_id not in ratings:
                average += DEFAULT_RATING
            else:
                average += ratings[p.steam_id][gametype]["elo"]
        average /= len(team)

        return average

    def handle_round_start(self, roundnumber):
        """
        Remembers the steam ids of all players at round startup
        """
        self.last_new_player_id = None

    @minqlx.delay(1.5)
    def handle_round_end(self, data):
        if not self.game:
            return minqlx.RET_NONE

        winning_team = data["TEAM_WON"].lower()
        self.winning_teams.append(winning_team)

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return minqlx.RET_NONE

        if abs(self.game.red_score - self.game.blue_score) < self.rebalance_score_diff_suggestion_threshold and \
                not self.team_is_on_a_winning_streak(winning_team):
            return minqlx.RET_NONE

        teams = self.teams()
        if len(teams["red"]) != len(teams["blue"]):
            return minqlx.RET_NONE

        if 'balance' in minqlx.Plugin._loaded_plugins:
            b = Plugin._loaded_plugins['balance']
            players = dict([(p.steam_id, gametype) for p in teams["red"] + teams["blue"]])
            b.add_request(players, b.callback_teams, minqlx.CHAT_CHANNEL)

    def team_is_on_a_winning_streak(self, team):
        return self.winning_teams[-self.rebalance_winning_streak_suggestion_threshold:] == \
            self.rebalance_winning_streak_suggestion_threshold * [team]

    def handle_game_start(self):
        self.winning_teams = []
