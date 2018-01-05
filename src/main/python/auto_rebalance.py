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

        self.add_command("rebalanceMethod", self.cmd_rebalance_method, permission=3, usage="[countdown|teamsswitch]")

        self.plugin_version = "{} Version: {}".format(self.name, "v0.0.2")
        self.logger.info(self.plugin_version)

    def handle_team_switch_attempt(self, player, old, new):
        """
        Handles the case where a player switches from spectators to "red", "blue", or "any" team, and
        the resulting teams would be sub-optimal balanced.

        :param player: the player that attempted the switch
        :param old: the old team of the switching player
        :param new: the new team that swicthting player would be put onto

        :return minqlx.RET_NONE if the team switch should be allowed or minqlx.RET_STOP_EVENT if the switch should not
        be allowed, and we put the player on a better-suited teamö.
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
            self.last_new_player_id = player.steam_id
            return minqlx.RET_NONE

        if not self.last_new_player_id:
            return minqlx.RET_NONE

        last_new_player = Plugin.player(self.last_new_player_id)
        if not last_new_player:
            return minqlx.RET_NONE

        other_than_last_players_team = self.other_team(last_new_player.team)
        new_player_team = teams[other_than_last_players_team].copy()
        new_player_team.append(player)
        last_player_avg = self.team_average(teams[last_new_player.team], gametype)
        new_player_avg = self.team_average(new_player_team, gametype)
        proposed_diff = abs(last_player_avg - new_player_avg)

        alternative_team_a = [player for player in teams[last_new_player.team] if player != last_new_player]
        alternative_team_a.append(player)
        alternative_new_avg = self.team_average(alternative_team_a, gametype)
        alternative_team_b = teams[other_than_last_players_team].copy()
        alternative_team_b.append(last_new_player)
        alternative_last_avg = self.team_average(alternative_team_b, gametype)
        alternative_diff = abs(alternative_last_avg - alternative_new_avg)

        self.last_new_player_id = None
        if proposed_diff > alternative_diff:
            last_new_player.put(other_than_last_players_team)
            if new in [last_new_player.team]:
                return minqlx.RET_NONE
            player.put(last_new_player.team)
            return minqlx.RET_STOP_EVENT

        if new not in ["any", other_than_last_players_team]:
            player.put(other_than_last_players_team)
            return minqlx.RET_STOP_EVENT

        return minqlx.RET_NONE

    def other_team(self, team):
        if team == "red":
            return "blue"
        return "red"

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
            return minqlx.RET_NONE

        gametype = self.game.type_short
        if gametype not in SUPPORTED_GAMETYPES:
            return minqlx.RET_NONE

        if roundnumber == 1:
            return minqlx.RET_NONE

        teams = self.teams()

        new_red_players = [player for player in teams["red"]
                           if player.steam_id not in self.balanced_player_steam_ids]
        new_blue_players = [player for player in teams["blue"]
                            if player.steam_id not in self.balanced_player_steam_ids]

        if len(new_red_players) + len(new_blue_players) < 2:
            return

        # make sure the auto-balance feature of mybalance does not interfere
        last_player = None
        if len(teams["red"]) != len(teams["blue"]) and (len(new_red_players) + len(new_blue_players)) % 2 == 1 \
                and "mybalance" in self.plugins:
            last_player = self.plugins["mybalance"].algo_get_last()

        Plugin.msg("New players detected: {}"
                   .format(", ".join([player.name for player in new_red_players + new_blue_players])))

        new_players = {'red': [player for player in new_red_players if player != last_player],
                       'blue': [player for player in new_blue_players if player != last_player]}
        switch = self.suggest_switch(teams, new_players, gametype)
        if not switch:
            Plugin.msg("New team members already on optimal teams. Nothing to rebalance")
            return

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
            switch = self.suggest_switch(teams, new_players, gametype)

        self.perform_switches(switches)

    @minqlx.thread
    def perform_switches(self, switches):
        """
        pereforms collected player switches in its own thread to not interfere with other game logic

        :param switches: a list of player pairs that should be switched with each other
        """
        for switch in switches:
            self.switch(switch[0], switch[1])

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
        self.balanced_player_steam_ids = [player.steam_id for player in teams["red"] + teams["blue"]]
        self.last_new_player_id = None

    def handle_game_countdown(self):
        """
        When a new game starts, the steam ids of the previous rounds are re-initialized.
        """
        self.balanced_player_steam_ids = []

    def cmd_rebalance_method(self, player, msg, channel):
        if len(msg) < 2 or msg[1] not in ["countdown", "teamswitch"]:
            player.tell("Current rebalance method is: ^4{}^7".format(self.rebalance_method))
            return minqlx.RET_USAGE
        else:
            self.rebalance_method = msg[1]
            Plugin.set_cvar("qlx_rebalanceMethod", self.rebalance_method)
            player.tell("Rebalance method set to: ^4{}^7".format(self.rebalance_method))
