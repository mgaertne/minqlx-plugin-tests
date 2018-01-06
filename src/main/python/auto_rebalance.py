"""
This is a plugin created by ShiN0
Copyright (c) 2018 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one, except for the version related code.

This plugin automatically rebalances new-joiners at round start based upon the ratings in the balance plugin.

It's intended to run with the default balance plugin, and will print an error on every round countdown if the
balance plugin is not loaded together with this one.
"""
import statistics

import minqlx
from minqlx import Plugin

SUPPORTED_GAMETYPES = ("ca", "ctf", "dom", "ft", "tdm")


class auto_rebalance(minqlx.Plugin):
    """
    Auto rebalance plugin for minqlx

    Rebalances new players joined since the last round countdown based upon the ratings in the balance plugin to yield
    better balanced teams overall.

    Uses:
    * qlx_rebalanceMethod (default: "countdown") Describes the method for rebalancing. countdown will rebalance during
    round countdown all new players. teamswitch will rebalance on every switch to the red or blue team, if applicable.

    """
    def __init__(self):
        """
        default constructor, adds the plugin hooks and initializes variables used
        """
        super().__init__()
        self.last_new_player_id = None
        if not self.game or self.game.state != "in_progress":
            self.balanced_player_steam_ids = []
        else:
            teams = self.teams()
            self.balanced_player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

        self.set_cvar_once("qlx_rebalanceMethod", "countdown")

        self.rebalance_method = self.get_cvar("qlx_rebalanceMethod")

        self.add_hook("team_switch_attempt", self.handle_team_switch_attempt)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start, priority=minqlx.PRI_LOWEST)
        self.add_hook("game_countdown", self.handle_game_countdown, priority=minqlx.PRI_LOWEST)

        self.add_command("rebalancemethod", self.cmd_rebalance_method, permission=3, usage="[countdown|teamsswitch]")

        self.plugin_version = "{} Version: {}".format(self.name, "v0.0.4")
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

        if self.game.state != "in_progress":
            return minqlx.RET_NONE

        if old not in ["spectator"] or new not in ['red', 'blue', 'any']:
            return minqlx.RET_NONE

        if self.rebalance_method != "teamswitch":
            return minqlx.RET_NONE

        if "balance" not in self.plugins:
            Plugin.msg("^1balance^7 plugin not loaded, ^1auto rebalance^7 not possible.")
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        teams = self.teams()
        if len(teams["red"]) == len(teams["blue"]):
            Plugin.msg("^2auto_rebalance^7 found new joiner {}. Plugin might switch you "
                       "if someone else joins before next round start for better team balancing"
                       .format(player.name))
            self.last_new_player_id = player.steam_id
            return minqlx.RET_NONE

        if not self.last_new_player_id:
            return minqlx.RET_NONE

        last_new_player = Plugin.player(self.last_new_player_id)
        if not last_new_player:
            self.last_new_player_id = None
            return minqlx.RET_NONE

        Plugin.msg("^2auto_rebalance^7 will check for best team constellations for: {}"
                   .format(", ".join([last_new_player.name, player.name])))
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
            Plugin.msg("^2auto_rebalance^7 will switch {} to {} and make sure {} goes on {} (diff. ^6{}^7 vs. ^6{}^7)"
                       .format(last_new_player.name, self.format_team(other_than_last_players_team),
                               player.name, self.format_team(last_new_player.team),
                               alternative_diff, proposed_diff))
            last_new_player.put(other_than_last_players_team)
            if new in [last_new_player.team]:
                return minqlx.RET_NONE
            player.put(last_new_player.team)
            return minqlx.RET_STOP_EVENT

        Plugin.msg("^2auto_rebalance^7 will leave {} on {} and make sure {} goes on {} (diff. ^6{}^7 vs. ^6{}^7)"
                   .format(last_new_player.name, self.format_team(last_new_player.team),
                           player.name, self.format_team(other_than_last_players_team),
                           proposed_diff, alternative_diff))
        if new not in ["any", other_than_last_players_team]:
            player.put(other_than_last_players_team)
            return minqlx.RET_STOP_EVENT

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

    def handle_round_countdown(self, roundnumber):
        """
        The plugin's main logic lies in here. At round countdown, the players currently on teams will be compared to the
        ones from the previous round and put on the other team if that leads to better balanced averages for both teams.

        :param roundnumber: the round number that is about to start
        """
        if self.rebalance_method != "countdown":
            return

        if "balance" not in self.plugins:
            Plugin.msg("^1balance^7 plugin not loaded, ^1auto rebalance^7 not possible.")
            return

        if roundnumber == 1:
            return

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return

        teams = self.teams()
        new_red_players = [player for player in teams["red"]
                           if player.steam_id not in self.balanced_player_steam_ids]
        new_blue_players = [player for player in teams["blue"]
                            if player.steam_id not in self.balanced_player_steam_ids]

        # at most one more new player found, we have nothing to do for rebalancing
        if len(new_red_players) + len(new_blue_players) < 2:
            return

        # make sure the auto-balance feature of mybalance does not interfere
        last_player = None
        if len(teams["red"]) != len(teams["blue"]) and (len(new_red_players) + len(new_blue_players)) % 2 == 1 \
                and "mybalance" in self.plugins:
            last_player = self.plugins["mybalance"].algo_get_last()

        Plugin.msg("^2auto_rebalance^7 New players detected: {}"
                   .format(", ".join([player.name for player in new_red_players + new_blue_players])))

        playing_teams = {'red': teams['red'].copy(), 'blue': teams['blue'].copy()}
        new_players = {'red': [player for player in new_red_players if player != last_player],
                       'blue': [player for player in new_blue_players if player != last_player]}

        switches = self.collect_more_optimal_player_switches(playing_teams, new_players, gametype, last_player)
        self.perform_switches(switches)

    def collect_more_optimal_player_switches(self, teams, new_players, gametype, last_player=None):
        switch = self.suggest_switch(gametype, teams, new_players)
        if not switch:
            Plugin.msg("New team members already on optimal teams. Nothing to rebalance")
            return []

        switches = []

        while switch:
            p1 = switch[0][0]
            p2 = switch[0][1]
            switches.append(switch[0])
            teams["blue"].append(p1)
            teams["red"].append(p2)
            teams["blue"].remove(p2)
            teams["red"].remove(p1)
            new_players = {'red': [player for player in teams["red"]
                                   if player.steam_id not in self.balanced_player_steam_ids and
                                   player != last_player],
                           'blue': [player for player in teams["blue"]
                                    if player.steam_id not in self.balanced_player_steam_ids and
                                    player != last_player]}
            switch = self.suggest_switch(gametype, teams, new_players)
        return switches

    @minqlx.thread
    def perform_switches(self, switches):
        """
        performs collected player switches in its own thread to not interfere with other game logic

        :param switches: a list of player pairs that should be switched with each other
        """
        for switch in switches:
            Plugin.msg("^2auto_rebalance^7 switching {} with {} for better balanced teams."
                       .format(switch[0].name, switch[1].name))

            self.switch(switch[0], switch[1])

    def suggest_switch(self, gametype, teams, new_players):
        """
        Suggest a switch based on average team ratings.

        :param teams: a dictionary with the red and blue teams and their players.
        :param new_players: a list of players that should be considered for switching with each other.
        :param gametype: the gametype to derive the ratings for.

        :return a switch of player that would improve the team balance based upon average elo ratings,
        or None if teams are already well balanced among the new_players.
        """
        cur_diff = self.calculate_player_average_difference(gametype, teams["red"], teams["blue"])
        min_diff = 999999
        best_pair = None

        for red_p in new_players["red"]:
            for blue_p in new_players["blue"]:
                r = teams["red"].copy()
                b = teams["blue"].copy()
                b.append(red_p)
                r.remove(red_p)
                r.append(blue_p)
                b.remove(blue_p)
                diff = self.calculate_player_average_difference(gametype, r, b)
                if diff < min_diff:
                    min_diff = diff
                    best_pair = red_p, blue_p

        if min_diff < cur_diff:
            return best_pair, cur_diff - min_diff
        else:
            return None

    def team_average(self, gametype, team):
        """
        Calculates the average rating of a team.

        :param gametype: the gametype to determine the ratings for
        :param team: the list of players the average should be calculated for

        :return the average rating for the given team and gametype
        """
        if not team:
            return 0

        ratings = self.plugins["balance"].ratings

        team_elos = [ratings[p.steam_id][gametype]["elo"] for p in team]
        return statistics.mean(team_elos)

    def handle_round_start(self, roundnumber):
        """
        Remembers the steam ids of all players at round startup
        """
        teams = Plugin.teams()
        self.balanced_player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]
        self.last_new_player_id = None

    def handle_game_countdown(self):
        """
        When a new game starts, the steam ids of the previous rounds are re-initialized.
        """
        self.balanced_player_steam_ids = []

    def cmd_rebalance_method(self, player, msg, channel):
        """
        (Re-)sets the rebalance method, either during each team switch events or just at round start

        :param player: the player that initiated the command
        :param msg: the original message the player sent
        :param channel: the channel this hook was triggered from
        """
        if len(msg) < 2 or msg[1] not in ["countdown", "teamswitch"]:
            player.tell("Current rebalance method is: ^4{}^7".format(self.rebalance_method))
            return minqlx.RET_USAGE
        else:
            self.rebalance_method = msg[1]
            Plugin.set_cvar("qlx_rebalanceMethod", self.rebalance_method)
            player.tell("Rebalance method set to: ^4{}^7".format(self.rebalance_method))
