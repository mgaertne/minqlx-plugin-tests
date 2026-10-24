"""Exercise isolated movement logic with synthetic players, without loading plugins."""

import ast
import math
import pathlib
import unittest
from datetime import datetime
from typing import Dict, List, NamedTuple


def isolated_movement_logic():
    path = pathlib.Path(__file__).resolve().parents[1] / "src/experimental/weird_stats.py"
    tree = ast.parse(path.read_bytes(), filename=str(path))
    position = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Position")
    distance = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "calculate_distance"
    )
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "weird_stats")
    methods: List[ast.stmt] = [
        node
        for node in plugin.body
        if isinstance(node, ast.FunctionDef) and node.name in {"handle_frame", "handle_round_start"}
    ]
    if len(methods) != 2:
        raise AssertionError("Expected frame and round-start handlers")
    isolated_class = ast.parse("class MovementLogic: pass").body[0]
    assert isinstance(isolated_class, ast.ClassDef)
    isolated_class.body = methods
    isolated = ast.Module(
        body=[position, distance, isolated_class],
        type_ignores=[],
    )
    namespace = {"NamedTuple": NamedTuple, "math": math, "datetime": datetime}
    exec(compile(ast.fix_missing_locations(isolated), str(path), "exec"), namespace)
    return namespace["MovementLogic"], namespace["Position"]


MovementLogic, Position = isolated_movement_logic()


class FakePlayer:
    def __init__(self, identifier, position=(0, 0, 0), alive=True):
        self.identifier = identifier
        self.coordinates = position
        self.alive = alive
        self.position_reads = 0
        self.identifier_reads = 0
        self.alive_reads = 0

    @property
    def steam_id(self):
        self.identifier_reads += 1
        return self.identifier

    @property
    def is_alive(self):
        self.alive_reads += 1
        return self.alive

    def position(self):
        self.position_reads += 1
        return self.coordinates


class WeirdStatsFrameTests(unittest.TestCase):
    def setUp(self):
        self.plugin = MovementLogic()
        self.plugin.in_round = True
        self.plugin.previous_positions = {}
        self.plugin.travelled_distances = {}
        self.teams: Dict[str, List[FakePlayer]] = {"red": [], "blue": [], "spectator": []}
        self.plugin.teams = lambda: self.teams

    def test_outside_round_does_not_query_teams_or_touch_movement_state(self):
        self.plugin.in_round = False
        self.plugin.previous_positions = {101: Position(1, 2, 3)}
        self.plugin.travelled_distances = {101: 12.0}
        self.plugin.teams = lambda: self.fail("No team query needed outside a round")

        self.plugin.handle_frame()

        self.assertEqual(self.plugin.previous_positions, {101: Position(1, 2, 3)})
        self.assertEqual(self.plugin.travelled_distances, {101: 12.0})

    def test_each_active_player_is_sampled_once_and_spectators_are_ignored(self):
        red = FakePlayer(101, (3, 4, 12))
        blue = FakePlayer(202, (0, 0, 8))
        spectator = FakePlayer(303, (100, 100, 100))
        self.teams.update(red=[red], blue=[blue], spectator=[spectator])
        self.plugin.previous_positions = {
            101: Position(0, 0, 0),
            202: Position(0, 0, 0),
        }

        self.plugin.handle_frame()

        self.assertEqual(self.plugin.travelled_distances, {101: 13.0, 202: 8.0})
        self.assertEqual(self.plugin.previous_positions[101], Position(3, 4, 12))
        self.assertEqual(self.plugin.previous_positions[202], Position(0, 0, 8))
        for player in (red, blue):
            self.assertEqual(player.position_reads, 1)
            self.assertEqual(player.identifier_reads, 1)
            self.assertEqual(player.alive_reads, 1)
        self.assertEqual(spectator.position_reads, 0)
        self.assertEqual(spectator.identifier_reads, 0)

    def test_first_sample_sets_origin_without_counting_spawn_distance(self):
        player = FakePlayer(101, (10000, 0, 0))
        self.teams["red"] = [player]

        self.plugin.handle_frame()
        self.assertEqual(self.plugin.travelled_distances, {101: 0.0})

        player.coordinates = (10003, 4, 0)
        self.plugin.handle_frame()
        self.assertEqual(self.plugin.travelled_distances, {101: 5.0})

    def test_movement_accumulates_across_frames_including_stationary_frames(self):
        player = FakePlayer(101, (3, 4, 12))
        self.teams["red"] = [player]
        self.plugin.previous_positions[101] = Position(0, 0, 0)
        self.plugin.travelled_distances[101] = 7.0

        self.plugin.handle_frame()
        player.coordinates = (3, 4, 0)
        self.plugin.handle_frame()
        self.plugin.handle_frame()

        self.assertEqual(self.plugin.travelled_distances[101], 32.0)
        self.assertEqual(player.position_reads, 3)

    def test_dead_player_loses_origin_but_retains_accumulated_distance(self):
        player = FakePlayer(101, (10000, 0, 0), alive=False)
        self.teams["red"] = [player]
        self.plugin.previous_positions[101] = Position(1, 2, 3)
        self.plugin.travelled_distances[101] = 12.0

        self.plugin.handle_frame()
        self.assertNotIn(101, self.plugin.previous_positions)
        self.assertEqual(self.plugin.travelled_distances[101], 12.0)
        self.assertEqual(player.position_reads, 0)
        self.plugin.handle_frame()  # Also safe when there is no origin to remove.

        player.alive = True
        self.plugin.handle_frame()
        self.assertEqual(self.plugin.travelled_distances[101], 12.0)
        player.coordinates = (10003, 4, 0)
        self.plugin.handle_frame()
        self.assertEqual(self.plugin.travelled_distances[101], 17.0)

    def test_jump_threshold_is_unchanged_and_rejected_jump_updates_origin(self):
        for jump, counted in [(799, 799.0), (800, 0.0), (801, 0.0)]:
            with self.subTest(jump=jump):
                player = FakePlayer(101, (jump, 0, 0))
                self.teams["red"] = [player]
                self.plugin.previous_positions = {101: Position(0, 0, 0)}
                self.plugin.travelled_distances = {101: 10.0}

                self.plugin.handle_frame()
                self.assertEqual(self.plugin.travelled_distances[101], 10.0 + counted)
                self.assertEqual(self.plugin.previous_positions[101], Position(jump, 0, 0))

                player.coordinates = (jump + 5, 0, 0)
                self.plugin.handle_frame()
                self.assertEqual(self.plugin.travelled_distances[101], 15.0 + counted)

    def test_round_start_resets_origin_without_discarding_match_distance(self):
        player = FakePlayer(101, (5000, 0, 0))
        self.teams["red"] = [player]
        self.plugin.in_round = False
        self.plugin.previous_positions[101] = Position(-5000, 0, 0)
        self.plugin.travelled_distances[101] = 42.0

        self.plugin.handle_frame()
        self.assertEqual(player.position_reads, 0)
        self.plugin.handle_round_start(2)
        self.assertTrue(self.plugin.in_round)
        self.assertEqual(self.plugin.previous_positions[101], Position(5000, 0, 0))

        player.coordinates = (5003, 4, 0)
        self.plugin.handle_frame()
        self.assertEqual(self.plugin.travelled_distances[101], 47.0)


if __name__ == "__main__":
    unittest.main()
