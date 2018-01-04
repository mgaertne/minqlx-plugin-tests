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

from balance import SUPPORTED_GAMETYPES


class auto_rebalance(minqlx.Plugin):
    """
    Auto rebalance plugin for minqlx

    Rebalances new players joined since the last round countdown based upon the ratings in the balance plugin to yield
    better balanced teams overall.
    """
    def __init__(self):
        """
        default constructor, adds the plugin hooks and initializes variables used
        """
        super().__init__()
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("round_start", self.handle_round_start, priority=minqlx.PRI_LOWEST)
        self.add_hook("game_countdown", self.handle_game_countdown, priority=minqlx.PRI_LOWEST)

        self.previous_round_player_steam_ids = []

        self.plugin_version = "{} Version: {}".format(self.name, "v0.0.1")
        self.logger.info(self.plugin_version)

    def handle_round_countdown(self, roundnumber):
        """
        The plugin's main logic lies in here. At round countdown, the players currently on teams will be compared to the
        ones from the previous round and put on the other team if that leads to better balanced averages for both teams.

        :param roundnumber: the round number that is about to start
        """
        if "balance" not in self.plugins:
            Plugin.msg("^1balance^7 plugin not loaded, ^1auto rebalance^7 not possible.")
            return

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return

        teams = self.teams()
        new_red_players = [player for player in teams["red"]
                           if player.steam_id not in self.previous_round_player_steam_ids]
        new_blue_players = [player for player in teams["blue"]
                            if player.steam_id not in self.previous_round_player_steam_ids]

        if len(new_red_players) + len(new_blue_players) < 2:
            return

        Plugin.msg("New players detected: {}"
                   .format(", ".join([player.name for player in new_red_players + new_blue_players])))

        new_players = {'red': new_red_players,
                       'blue': new_blue_players}
        switch = self.suggest_switch(teams, new_players, gametype)
        if not switch:
            Plugin.msg("New team members already on optimal teams. Nothing to rebalance")
            return

        while switch:
            p1 = switch[0][0]
            p2 = switch[0][1]
            self.switch(p1, p2)
            teams["blue"].append(p1)
            teams["red"].append(p2)
            teams["blue"].remove(p2)
            teams["red"].remove(p1)
            new_players = {'red': [player for player in teams["red"]
                                   if player.steam_id not in self.previous_round_player_steam_ids],
                           'blue': [player for player in teams["blue"]
                                    if player.steam_id not in self.previous_round_player_steam_ids]}
            switch = self.suggest_switch(teams, new_players, gametype)

    def suggest_switch(self, teams, new_players, gametype):
        """Suggest a switch based on average team ratings."""
        avg_red = self.team_average(teams["red"], gametype)
        avg_blue = self.team_average(teams["blue"], gametype)
        cur_diff = abs(avg_red - avg_blue)
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
                avg_red = self.team_average(r, gametype)
                avg_blue = self.team_average(b, gametype)
                diff = abs(avg_red - avg_blue)
                if diff < min_diff:
                    min_diff = diff
                    best_pair = (red_p, blue_p)

        if min_diff < cur_diff:
            return (best_pair, cur_diff - min_diff)
        else:
            return None

    def team_average(self, team, gametype):
        """Calculates the average rating of a team."""
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
        self.previous_round_player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]

    def handle_game_countdown(self):
        """
        When a new game starts, the steam ids of the previous rounds are re-initialized.
        """
        self.previous_round_player_steam_ids = []
