from operator import itemgetter
from typing import Optional

import minqlx  # type: ignore
from minqlx import Player

SteamId = int


def other_team(team: str) -> str:
    if team == "red":
        return "blue"
    if team == "blue":
        return "red"
    return "draw"


def color_format_team(team: str) -> str:
    if team == "red":
        return f"^1{team}^7"

    if team == "blue":
        return f"^4{team}^7"

    return team


def damage_this_round(damages: dict[SteamId, int], steam_id: int):
    if steam_id not in damages:
        return 0

    return damages[steam_id]


# noinspection PyPep8Naming
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

        self.stats_snapshot: dict[SteamId, int] = {}
        self.scheduled_switches: list[SteamId] = []
        self.spec_rotation: list[SteamId] = []
        self.team_score_snapshots: dict[SteamId, int] = {}
        self.score_snapshots: dict[SteamId, int] = {}

        self.in_countdown: bool = False

    def handle_map_change(self, _mapname: str, _factory: str) -> None:
        self.in_countdown = False
        self.stats_snapshot = {}
        self.scheduled_switches = []
        self.spec_rotation = []
        self.team_score_snapshots = {}
        self.score_snapshots = {}

    def handle_client_command(self, player: Player, command: str):
        @minqlx.thread
        def handler():
            if command == "team s":
                if player.steam_id in self.spec_rotation:
                    self.spec_rotation.remove(player.steam_id)
                    player.tell("You have been removed from the spec rotation.")

        if not self.spec_rotation_plugin_is_enabled():
            return

        handler()

    def spec_rotation_plugin_is_enabled(self) -> bool:
        for autospec_plugin in ["balancetwo", "mybalance"]:
            if autospec_plugin in self.plugins:
                plugin = minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
                    autospec_plugin
                ]
                # noinspection PyUnresolvedReferences
                if plugin.last_action == "ignore":  # type: ignore
                    return False

        return True

    def handle_team_switch_attempt(
        self, player: Player, _old_team: str, new_team: str
    ) -> int:
        if not self.spec_rotation_plugin_is_enabled():
            return minqlx.RET_NONE

        if not self.game or self.game.state not in ["in_progress"]:
            return minqlx.RET_NONE

        teams = self.teams()

        if len(teams["red"]) != len(teams["blue"]):
            return minqlx.RET_NONE

        if new_team in ["red", "blue", "any"] and len(self.spec_rotation) == 0:
            self.spec_rotation.append(player.steam_id)
            player.tell(
                f"{player.name}^7, we added you to the spec rotation "
                f"and you will automatically rotate with the weakest player on the losing team."
            )

        if (
            new_team not in ["red", "blue", "any"]
            or player.steam_id not in self.spec_rotation
        ):
            return minqlx.RET_NONE

        return minqlx.RET_STOP_ALL

    def handle_team_switch(self, player: Player, old_team: str, new_team: str) -> None:
        if not self.spec_rotation_plugin_is_enabled():
            return

        if not self.game:
            return

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if (
            self.in_countdown
            and old_team in ["red", "blue"]
            and new_team == "spectator"
        ):
            if player.steam_id not in self.spec_rotation:
                self.spec_rotation.append(player.steam_id)
            player.tell(
                f"{player.name}^7, you will automatically rotate "
                f"with the weakest player on the losing team next round."
            )

        if self.game.state not in ["in_progress", "countdown"]:
            return

        if len(self.spec_rotation) == 0:
            return

        if player.steam_id in self.scheduled_switches:
            self.scheduled_switches.remove(player.steam_id)
            return

        teams = self.teams()
        if len(teams["red"]) == len(teams["blue"]):
            return

        if new_team in ["red", "blue"] and old_team == "spectator":
            if player.steam_id in self.team_score_snapshots:
                current_team_score = getattr(self.game, f"{new_team}_score")
                new_player_team_score = self.team_score_snapshots[player.steam_id]

                if new_player_team_score > current_team_score:
                    self.game.addteamscore(
                        new_team, new_player_team_score - current_team_score
                    )

            if player.steam_id not in self.spec_rotation:
                the_other_team = other_team(new_team)
                next_steam_id = self.spec_rotation.pop(0)
                self.switch_player(next_steam_id, the_other_team)
                self.msg("Disabling spec rotation since there are enough players now.")
                return

        if (
            new_team == "spectator"
            and old_team in ["red", "blue"]
            and player.steam_id not in self.spec_rotation
        ):
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, player.team)

    def switch_player(
        self, steam_id: SteamId, team: str, msg: Optional[str] = None
    ) -> None:
        switching_player = self.player(steam_id)
        if not switching_player:
            return

        self.scheduled_switches.append(steam_id)
        switching_player.put(team)

        if msg is not None:
            switching_player.tell(msg)

        if steam_id not in self.score_snapshots or team == "spectator":
            return

        switching_player.score = self.score_snapshots[steam_id]

    @minqlx.delay(3)
    def handle_player_loaded(self, player: Player) -> None:
        if not self.spec_rotation_plugin_is_enabled():
            return

        if not self.game or self.game.state != "in_progress":
            return

        teams = self.teams()
        if len(teams["red"]) != len(teams["blue"]):
            return

        if len(self.spec_rotation) != 0:
            return

        player.tell(
            f"{player.name}, join to activate spec rotation! "
            f"Player with fewest damage on losing team will be rotated with you."
        )

    def handle_player_disconnect(self, player: Player, _reason: str) -> None:
        if not self.spec_rotation_plugin_is_enabled():
            return

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

    @minqlx.delay(10)
    def handle_game_countdown(self) -> None:
        self.in_countdown = True

        self.team_score_snapshots = {}

        if not self.spec_rotation_plugin_is_enabled():
            return

        teams = self.teams()
        if len(teams["red"]) == len(teams["blue"]):
            return

        for player in teams["red"] + teams["blue"]:
            self.spec_rotation.append(player.steam_id)

    def handle_game_start(self, _data: dict) -> None:
        self.in_countdown = False

        teams = self.teams()
        for player in teams["red"] + teams["blue"]:
            if player.steam_id in self.spec_rotation:
                self.spec_rotation.remove(player.steam_id)

    def handle_round_countdown(self, _round_number: int) -> None:
        if not self.spec_rotation_plugin_is_enabled():
            return

        teams = self.teams()

        if len(teams["red"]) == len(teams["blue"]):
            return

        bigger_team = "blue"
        if len(teams["red"]) > len(teams["blue"]):
            bigger_team = "red"

        smaller_team = other_team(bigger_team)

        if len(self.spec_rotation) > 0:
            next_steam_id = self.spec_rotation.pop(0)
            self.switch_player(next_steam_id, smaller_team)
            return

        spec_player = self.find_player_to_spec(teams[bigger_team])
        self.spec_rotation.append(spec_player.steam_id)
        spec_player.tell(
            f"{spec_player.name}^7, we added you to the spec rotation and you will automatically rotate "
            f"with the weakest player on the losing team."
        )

    def find_player_to_spec(self, players: list[Player]) -> Player:
        return min(players, key=self.find_games_here)

    def find_games_here(self, player: Player) -> int:
        completed_key = f"minqlx:players:{player.steam_id}:games_completed"

        if self.db is None or not self.db.exists(completed_key):
            return 0

        return int(self.db[completed_key])

    def handle_round_start(self, _round_number: int) -> None:
        teams = self.teams()
        self.stats_snapshot = {
            player.steam_id: player.stats.damage_dealt
            for player in teams["red"] + teams["blue"]
        }

    def handle_round_end(self, data: dict) -> None:
        if not self.spec_rotation_plugin_is_enabled():
            return

        if self.game is None:
            return

        teams = self.teams()

        for team in ["red", "blue"]:
            current_team_score = getattr(self.game, f"{team}_score")
            team_scores = [
                self.team_score_snapshots[player.steam_id]
                for player in teams[team]
                if player.steam_id in self.team_score_snapshots
            ]
            max_team_score = max(team_scores, default=0)
            if max_team_score > current_team_score:
                self.game.addteamscore(team, max_team_score - current_team_score)

        for player in teams["red"] + teams["blue"]:
            self.team_score_snapshots[player.steam_id] = getattr(
                self.game, f"{player.team}_score"
            )
            self.score_snapshots[player.steam_id] = player.score

        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            if (
                len(teams["red"]) == 1
                and len(teams["blue"]) == 1
                and len(self.team_score_snapshots) > 2
            ):
                self.print_scores()
            return

        if len(teams["red"]) < 1 or len(teams["blue"]) < 1:
            return

        if len(self.spec_rotation) == 0:
            return

        if len(self.stats_snapshot) == 0 and data["ROUND"] > 1:
            return

        winning_team = data["TEAM_WON"].lower()

        if winning_team == "draw":
            return

        losing_team = other_team(winning_team)

        player_to_replace = self.player_to_replace(losing_team)
        spec_player = self.player(player_to_replace)

        next_steam_id = self.spec_rotation.pop(0)
        next_player = self.player(next_steam_id)

        if spec_player is None:
            return

        if next_player is None:
            return

        if next_player.team != "spectator":
            return

        self.msg(
            f"Replacing player with fewest round damage on team {color_format_team(losing_team)} "
            f"{spec_player.name}^7 with the next player from the rotation {next_player.name}^7."
        )

        if len(teams["red"]) == 1 and len(teams["blue"]) == 1:
            if next_steam_id not in self.team_score_snapshots:
                self.game.addteamscore(
                    losing_team, -getattr(self.game, f"{losing_team}_score")
                )
            else:
                self.game.addteamscore(
                    losing_team,
                    self.team_score_snapshots[next_steam_id]
                    - getattr(self.game, f"{losing_team}_score"),
                )

        self.switch_player(next_steam_id, losing_team)
        self.spec_rotation.append(spec_player.steam_id)
        self.switch_player(
            spec_player.steam_id,
            "spectator",
            msg=f"{spec_player.name}^7, you will automatically rotate with the weakest player "
            f"on the losing team next round.",
        )

    def print_scores(self) -> None:
        self.msg("DuelArena results:")
        place = 0
        prev_score = -1
        for steam_id, score in sorted(
            self.team_score_snapshots.items(), key=itemgetter(1), reverse=True
        ):
            if score != prev_score:
                place += 1
            prev_score = score
            player = self.player(steam_id)
            if player and len(player.name) != 0:
                self.msg(f"Place ^3{place}.^7 {player.name} ^7(Wins:^2{score}^7)")

    def calculate_damage_deltas(self) -> dict[SteamId, int]:
        returned = {}

        for steam_id in self.stats_snapshot:
            minqlx_player = self.player(steam_id)

            if minqlx_player is None:
                continue

            returned[steam_id] = (
                minqlx_player.stats.damage_dealt - self.stats_snapshot[steam_id]
            )

        return returned

    def player_to_replace(self, losing_team: str) -> Player:
        round_damage = self.calculate_damage_deltas()

        teams = self.teams()

        losing_steam_ids = teams[losing_team]

        losing_steam_ids.sort(
            key=lambda player: damage_this_round(round_damage, player.steam_id)
        )

        return losing_steam_ids[0]
