from minqlx import NonexistentGameError

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

class TestDuelArena(unittest.TestCase):

    def setUp(self):
        self.plugin = duelarena()
        spy2(self.plugin.msg)
        when2(self.plugin.msg, ANY(str)).thenReturn(None)
        spy2(self.plugin.center_print)
        when2(self.plugin.center_print, ANY(str)).thenReturn(None)
        self.plugin.player = mock(spec=minqlx.Player, strict=False)
        self.mock_game = mock(spec=minqlx.Game, strict=False)
        self.setupGameInProgress()
        self.activateDuelArenaMode()

    def tearDown(self):
        unstub()

    def fakePlayer(self, id, name, team="spectator", ping=0):
        player = mock(spec=minqlx.Player, strict=False)
        player.steam_id = id
        player.name = name
        player.team = team
        player.ping = ping
        return player

    def connectedPlayers(self, *players):
        patch(self.plugin.players, lambda: players)
        for player in players:
            when2(self.plugin.player, player.steam_id).thenReturn(player)

    def subscribedPlayerIds(self, *ids):
        for id in ids:
            self.plugin.psub.insert(0, id)

    def playerIdsInQueue(self, *ids):
        for id in ids:
            self.plugin.queue.insert(0, id)

    def deactivateDuelArenaMode(self):
        self.plugin.duelmode = False

    def activateDuelArenaMode(self):
        self.plugin.duelmode = True

    def activateInitDuelArenaMode(self):
        self.plugin.initmode = True

    def setupNoGame(self):
        when2(minqlx.Game).thenRaise(NonexistentGameError("Tried to instantiate a game while no game is active."))

    def setupGameInWarmup(self):
        when2(minqlx.Game).thenReturn(self.mock_game)
        self.mock_game.state = "warmup"

    def setupGameInProgress(self, game_type="ca", roundlimit=8, red_score=0, blue_score=0):
        when2(minqlx.Game).thenReturn(self.mock_game)
        self.mock_game.state = "in_progress"
        self.mock_game.type_short = game_type
        self.mock_game.roundlimit = roundlimit
        self.mock_game.red_score = red_score
        self.mock_game.blue_score = blue_score

    def assert_duelarena_deactivated(self):
        assert_that(self.plugin.duelmode, is_(False))

    def assert_duelarena_activated(self):
        assert_that(self.plugin.duelmode, is_(True))

    def assert_duelarena_about_to_initialize(self):
        assert_that(self.plugin.initduel, is_(True))

    def assert_duelarena_finished_to_initialize(self):
        assert_that(self.plugin.initduel, is_(False))


    def test_enqueue_players(self):
        self.playerIdsInQueue(1, 2, 3)

        assert_that(self.plugin.queue, contains(3, 2, 1))

    def test_switch_player_with_no_duelmode_active(self):
        self.deactivateDuelArenaMode()

        return_code = self.plugin.handle_team_switch_event(self.fakePlayer(123, "Fake Player"), "don't care",
                                                           "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_with_no_active_game(self):
        self.setupNoGame()

        return_code = self.plugin.handle_team_switch_event(self.fakePlayer(123, "Fake Player"), "don't care", "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_with_no_game_in_warmup(self):
        self.setupGameInWarmup()

        return_code = self.plugin.handle_team_switch_event(self.fakePlayer(123, "Fake Player"), "don't care", "don't care")

        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_to_red_initiated_by_plugin(self):
        self.plugin.player_red = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(self.plugin.player_red, "don't care", "don't care")

        assert_that(self.plugin.player_red, is_(None))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_switch_player_to_blue_initiated_by_plugin(self):
        self.plugin.player_blue = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(self.plugin.player_blue, "don't care", "don't care")

        assert_that(self.plugin.player_blue, is_(None))
        assert_that(return_code, is_not(minqlx.RET_STOP_ALL))

    def test_unallowed_switch_from_spec_to_red(self):
        switching_player = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(switching_player).tell(ANY(str))

    def test_unallowed_switch_from_spec_to_blue(self):
        switching_player = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "spectators", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(switching_player).tell(ANY(str))

    def test_unallowed_switch_from_blue_to_red(self):
        switching_player = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "blue", "red")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(switching_player).tell(ANY(str))

    def test_unallowed_switch_from_red_to_blue(self):
        switching_player = self.fakePlayer(123, "Fake Player")

        return_code = self.plugin.handle_team_switch_event(switching_player, "red", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(switching_player).tell(ANY(str))

    def test_2nd_player_connects(self):
        connecting_player = self.fakePlayer(2, "Player 2")
        self.connectedPlayers(self.fakePlayer(1, "Player 1"), connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        self.assert_duelarena_deactivated()

    def test_3rd_player_connects(self):
        connecting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(self.fakePlayer(1, "Player 1"), self.fakePlayer(2, "Player 2"), connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        verify(self.plugin).msg("Type ^6!d ^7for DuelArena!")
        verify(self.plugin).center_print("Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_4th_player_connects(self):
        self.deactivateDuelArenaMode()
        connecting_player = self.fakePlayer(4, "Player 4")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        verify(self.plugin, times=0).msg(ANY(str))
        verify(self.plugin, times=0).center_print(ANY(str))
        self.assert_duelarena_deactivated()

    def test_5th_player_connects_when_duelarena_deactivated(self):
        self.deactivateDuelArenaMode()
        connecting_player = self.fakePlayer(5, "Player 5")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        verify(self.plugin).msg("Type ^6!d ^7for DuelArena!")
        verify(self.plugin).center_print("Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_5th_player_connects_when_duelarena_activated(self):
        connecting_player = self.fakePlayer(5, "Player 5")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        verify(self.plugin).msg("DuelArena has been deactivated! You are free to join.")
        verify(self.plugin, times=0).center_print(ANY(str))
        self.assert_duelarena_deactivated()

    def test_6th_player_connects(self):
        self.deactivateDuelArenaMode()
        connecting_player = self.fakePlayer(6, "Player 6")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"),
            connecting_player)

        self.plugin.undelayed_handle_player_connected(connecting_player)

        verify(self.plugin, times=0).msg(ANY(str))
        verify(self.plugin, times=0).center_print(ANY(str))
        self.assert_duelarena_deactivated()

    def test_handle_round_count_when_duelarena_activated(self):
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"),
            self.fakePlayer(4, "Player 4"))

        self.plugin.handle_round_countdown()

        verify(self.plugin).center_print("Player 3 ^2vs Player 1")

    def test_handle_round_count_when_duelarena_deactivated(self):
        self.deactivateDuelArenaMode()
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"),
            self.fakePlayer(4, "Player 4"))

        self.plugin.handle_round_countdown()

        verify(self.plugin, times=0).center_print(ANY(str))

    def test_handle_player_disconnect_broadcast_when_minimum_players_are_left(self):
        self.deactivateDuelArenaMode()
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"))

        self.plugin.undelayed_handle_player_disco(self.fakePlayer(4, "Player 4"), "ragequit")

        verify(self.plugin).msg("Type ^6!d ^7for DuelArena!")
        verify(self.plugin).center_print("Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_handle_player_disconnect_deactivates_duelarena(self):
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"))
        self.subscribedPlayerIds(1, 2, 4)

        self.plugin.undelayed_handle_player_disco(self.fakePlayer(4, "Player 4"), "ragequit")

        verify(self.plugin).msg("DuelArena has been deactivated! You are free to join.")
        self.assert_duelarena_deactivated()
        assert_that(self.plugin.psub, is_([2, 1]))

    def test_handle_player_disconnect_activates_duelarena(self):
        self.deactivateDuelArenaMode()
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 6, 3, 4)
        self.playerIdsInQueue(1, 2, 6, 3, 4)
        when2(self.plugin.player, 6).thenReturn(None)

        self.plugin.undelayed_handle_player_disco(self.fakePlayer(6, "Player 6"), "ragequit")

        verify(self.plugin).msg("DuelArena activated!")
        verify(self.plugin).center_print("DuelArena activated!")
        self.assert_duelarena_activated()
        self.assert_duelarena_about_to_initialize()
        assert_that(self.plugin.psub, is_([4, 3, 2, 1]))

    def test_handle_player_disconnect_broadcasts_duelarena(self):
        self.deactivateDuelArenaMode()
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "blue"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3", "red"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))

        self.plugin.undelayed_handle_player_disco(self.fakePlayer(6, "Player 6"), "ragequit")

        verify(self.plugin).msg("Type ^6!d ^7for DuelArena!")
        verify(self.plugin).center_print("Type ^6!d ^7for DuelArena!")
        self.assert_duelarena_deactivated()

    def test_game_countdown_inits_duelarena_when_activated_and_moved_players_to_right_teams(self):
        red_player = self.fakePlayer(1, "Player 1", "blue")
        blue_player = self.fakePlayer(2, "Player 2")
        speccing_player = self.fakePlayer(3, "Player 3", "red")
        self.connectedPlayers(
            red_player,
            blue_player,
            speccing_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(1, 2, 3, 4)

        self.plugin.undelayed_handle_game_countdown()

        assert_that(self.plugin.player_red, is_(red_player))
        assert_that(self.plugin.player_blue, is_(blue_player))
        verify(blue_player).put("red")
        verify(speccing_player).put("spectator")
        self.assert_duelarena_finished_to_initialize()
        assert_that(self.plugin.queue, is_([4, 3]))


    def test_game_countdown_inits_duelarena_when_activated_and_keeps_red_player_on_red_team(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(4, 3, 2, 1)

        self.plugin.undelayed_handle_game_countdown()

        assert_that(self.plugin.player_red, is_(red_player))
        assert_that(self.plugin.player_blue, is_(blue_player))
        verify(blue_player, times=0).put("blue")
        self.assert_duelarena_finished_to_initialize()
        assert_that(self.plugin.queue, is_([4, 3]))

    def test_move_players_to_teams_players_already_on_right_team(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3"))

        self.plugin.move_players_to_teams()

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player, times=0).put(ANY(str))

    def test_move_players_to_teams_players_on_opposing_teams(self):
        red_player = self.fakePlayer(1, "Player 1", "blue")
        blue_player = self.fakePlayer(2, "Player 2", "red")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3"))

        self.plugin.move_players_to_teams()

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player, times=0).put(ANY(str))

    def test_move_players_to_teams_players_on_blue_team(self):
        red_player = self.fakePlayer(1, "Player 1", "blue")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player).put("red")

    def test_move_players_to_teams_players_on_red_team(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "red")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player).put("blue")

    def test_move_players_to_teams_one_player_speccing(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "spectator")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player).put("blue")

    def test_move_players_to_teams_both_players_speccing(self):
        red_player = self.fakePlayer(1, "Player 1", "spectator")
        blue_player = self.fakePlayer(2, "Player 2", "spectator")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3", "red"))

        self.plugin.move_players_to_teams()

        verify(red_player).put("red")
        verify(blue_player).put("blue")

    def test_move_non_players_to_spec_from_blue_team(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "red")
        speccing_player = self.fakePlayer(3, "Player 3", "blue")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            speccing_player)

        self.plugin.move_all_non_playing_players_to_spec()

        verify(speccing_player).put("spectator")

    def test_move_non_players_to_spec_from_red_team(self):
        red_player = self.fakePlayer(1, "Player 1", "blue")
        blue_player = self.fakePlayer(2, "Player 2", "red")
        speccing_player = self.fakePlayer(3, "Player 3", "red")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            speccing_player)

        self.plugin.move_all_non_playing_players_to_spec()

        verify(speccing_player).put("spectator")

    def test_move_non_players_to_spec_from_red_and_blue_team(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "red")
        speccing_player1 = self.fakePlayer(3, "Player 3", "blue")
        speccing_player2 = self.fakePlayer(4, "Player 4", "red")
        self.plugin.player_red = red_player
        self.plugin.player_blue = blue_player
        self.connectedPlayers(
            red_player,
            blue_player,
            speccing_player1,
            speccing_player2)

        self.plugin.move_all_non_playing_players_to_spec()

        verify(speccing_player1).put("spectator")
        verify(speccing_player2).put("spectator")

    def test_game_end_with_no_active_game(self):
        self.setupNoGame()

        self.plugin.handle_game_end(None)

        verifyNoUnwantedInteractions()

    def test_game_end_with_deactivated_duelarena(self):
        self.deactivateDuelArenaMode()

        self.plugin.handle_game_end(None)

        verifyNoUnwantedInteractions()

    def test_game_end_with_activated_duelarena_red_team_won_stores_players_back_in_queue(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.handle_game_end({"TSCORE0": 8, "TSCORE1": 2})

        assert_that(self.plugin.queue, is_([blue_player.steam_id, 4, 3, red_player.steam_id]))

    def test_game_end_with_activated_duelarena_blue_team_won_stores_players_back_in_queue(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        self.connectedPlayers(
            red_player,
            blue_player,
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.handle_game_end({"TSCORE0": 5, "TSCORE1": 8})

        assert_that(self.plugin.queue, is_([red_player.steam_id, 4, 3, blue_player.steam_id]))

    def test_round_end_with_no_active_game(self):
        self.setupNoGame()

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with_no_ca_active(self):
        self.setupGameInProgress(game_type="ft")

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_red_team_hit_roundlimit(self):
        self.setupGameInProgress(roundlimit=8, red_score=8, blue_score=5)

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_blue_team_hit_roundlimit(self):
        self.setupGameInProgress(roundlimit=8, red_score=1, blue_score=8)

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with__duelarena_deactived(self):
        self.deactivateDuelArenaMode()

        self.plugin.undelayed_handle_round_end(None)

        verifyNoUnwantedInteractions()

    def test_round_end_with_duel_arena_about_to_init(self):
        self.deactivateDuelArenaMode()
        self.activateInitDuelArenaMode()

        self.plugin.undelayed_handle_round_end(None)

        self.assert_duelarena_finished_to_initialize()

    def test_round_end_with_red_player_won_duel(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        next_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            red_player,
            blue_player,
            next_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "RED"})

        verify(next_player).put("blue")
        assert_that(self.plugin.player_blue, is_(next_player))
        verify(blue_player).put("spectator")
        assert_that(self.plugin.queue, is_([blue_player.steam_id, 4]))

    def test_round_end_with_blue_player_won_duel(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        next_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            red_player,
            blue_player,
            next_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "BLUE"})

        verify(next_player).put("red")
        assert_that(self.plugin.player_red, is_(next_player))
        verify(red_player).put("spectator")
        assert_that(self.plugin.queue, is_([red_player.steam_id, 4]))

    def test_round_end_with_next_player_not_a_spectator_cancels_duelarena(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        next_player = self.fakePlayer(3, "Player 3", "free")
        self.connectedPlayers(
            red_player,
            blue_player,
            next_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "RED"})

        self.assert_duelarena_deactivated()

    def test_round_end_with_draw(self):
        red_player = self.fakePlayer(1, "Player 1", "red")
        blue_player = self.fakePlayer(2, "Player 2", "blue")
        next_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            red_player,
            blue_player,
            next_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(1, 2, 3, 4)
        self.playerIdsInQueue(3, 4)

        self.plugin.undelayed_handle_round_end({"TEAM_WON": "DRAW"})

        verify(red_player, times=0).put(ANY(str))
        verify(blue_player, times=0).put(ANY(str))
        verify(next_player, times=0).put(ANY(str))
        assert_that(self.plugin.queue, is_([4, 3]))

    def test_duel_cmd_with_too_many_connected_players(self):
        requesting_player = self.fakePlayer(6, "Player 6")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"),
            requesting_player)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(requesting_player).tell("^6!duel^7 command not available with ^66^7 or more players connected")

    def test_duel_cmd_second_player_subscribes(self):
        self.deactivateDuelArenaMode()
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(2)
        self.playerIdsInQueue(2)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7entered the DuelArena queue. ^61^7 more players needed to start DuelArena. Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 3 ")
        assert_that(self.plugin.queue, is_([3, 2]))
        assert_that(self.plugin.psub, is_([2, 3]))
        self.assert_duelarena_deactivated()

    def test_duel_cmd_third_player_subscribes(self):
        self.deactivateDuelArenaMode()
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(2, 1)
        self.playerIdsInQueue(2, 1)
        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 3 ")
        assert_that(self.plugin.queue, is_([3, 1, 2]))
        assert_that(self.plugin.psub, is_([1, 2, 3]))
        self.assert_duelarena_activated()

    def test_duel_cmd_fourth_player_subscribes(self):
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(2, 1, 5)
        self.playerIdsInQueue(2, 1, 5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 2 ^62nd^7: Player 1 ^63rd^7: Player 5 ^64th^7: Player 3 ")
        assert_that(self.plugin.queue, is_([3, 5, 1, 2]))
        assert_that(self.plugin.psub, is_([5, 1, 2, 3]))
        self.assert_duelarena_activated()

    def test_duel_cmd_fourth_player_unsubscribes(self):
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "red"),
            self.fakePlayer(2, "Player 2", "blue"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(3, 2, 1, 5)
        self.playerIdsInQueue(3, 5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7left DuelArena.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 5 ")
        assert_that(self.plugin.psub, is_([5, 1, 2]))
        assert_that(self.plugin.queue, is_([5]))
        self.assert_duelarena_activated()

    def test_duel_cmd_player_not_in_queue_unsubscribes(self):
        requesting_player = self.fakePlayer(3, "Player 3", "red")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2", "blue"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(3, 2, 1, 5)
        self.playerIdsInQueue(1, 5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7left DuelArena.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 1 ^62nd^7: Player 5 ")
        assert_that(self.plugin.psub, is_([5, 1, 2]))
        assert_that(self.plugin.queue, is_([5, 1]))
        self.assert_duelarena_activated()

    def test_duel_cmd_third_player_unsubscribes(self):
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1", "red"),
            self.fakePlayer(2, "Player 2", "blue"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.subscribedPlayerIds(3, 1, 5)
        self.playerIdsInQueue(3, 5)

        self.plugin.cmd_duel(requesting_player, "!d", None)

        verify(self.plugin).msg("Player 3 ^7left DuelArena.")
        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 5 ")
        verify(self.plugin).msg("DuelArena has been deactivated! You are free to join.")
        assert_that(self.plugin.psub, is_([5, 1]))
        assert_that(self.plugin.queue, is_([5]))
        self.assert_duelarena_deactivated()

    def test_print_empty_queue(self):
        requesting_player = self.fakePlayer(1, "Player 1")
        self.connectedPlayers(requesting_player)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        verify(self.plugin).msg("There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")

    def test_print_queue_with_players(self):
        requesting_player = self.fakePlayer(3, "Player 3")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            requesting_player,
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"))
        self.playerIdsInQueue(1, 2, 3, 4, 5)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        verify(self.plugin).msg("DuelArena queue: ^61st^7: Player 1 ^62nd^7: Player 2 ^63rd^7: Player 3 ^64th^7: Player 4 ^65th^7: Player 5 ")

    def test_print_queue_with_too_many_connected_players(self):
        requesting_player = self.fakePlayer(6, "Player 6")
        self.connectedPlayers(
            self.fakePlayer(1, "Player 1"),
            self.fakePlayer(2, "Player 2"),
            self.fakePlayer(3, "Player 3"),
            self.fakePlayer(4, "Player 4"),
            self.fakePlayer(5, "Player 5"),
            requesting_player)
        self.playerIdsInQueue(1, 2, 3, 4, 5)

        self.plugin.cmd_printqueue(requesting_player, "!q", None)

        verify(requesting_player).tell("^6!queue^7 command not available with ^66^7 or more players connected")


# DuelArena will start automatically if at least 3 players
# opted in (!duel or !d) to the queue.
# DuelArena will be deactivated automatically if connected players
# exceed the player_limit (default 5), or if there are only 2 players left, or
# if too many players opted out.

import minqlx

MIN_ACTIVE_PLAYERS = 3  # with <3 connected and subscribed players we deactive DuelArena
MAX_ACTIVE_PLAYERS = 5  # with >5 connected players we deactivate DuelArena

class duelarena(minqlx.Plugin):

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
        self.player_red = None  # force spec exception for this player
        self.player_blue = None  # force spec exception for this player

    # Don't allow players to join manually when DuelArena is active
    def handle_team_switch_event(self, player, old, new):
        if not self.duelmode: return
        if not self.game: return
        if self.game.state == "warmup": return

        # If we initiated this switch, allow it
        if player == self.player_red:
            self.player_red = None
            return

        if player == self.player_blue:
            self.player_blue = None
            return

        # If they wanted to join a team, halt this hook at enginge-level and other hooks from being called
        if new in ['red', 'blue']:
            player.tell(
                "Server is in DuelArena mode. You will automatically join. Type ^6!duel ^7or ^6!d ^7to enter or to leave the queue")
            return minqlx.RET_STOP_ALL

    # When a player connects, display them a message and check if we should switch duel arena
    @minqlx.delay(4)
    def handle_player_connect(self, player):
        self.undelayed_handle_player_connected(player)

    def undelayed_handle_player_connected(self, player):
        playercount = self.connected_players()

        if playercount == 3 or (playercount == 5 and not self.duelmode):
            self.center_print("Type ^6!d ^7for DuelArena!")
            self.msg("Type ^6!d ^7for DuelArena!")

        self.duelarena_switch("p_connect_hook")

    def handle_round_countdown(self, *args, **kwargs):

        if self.duelmode:
            teams = self.teams()
            self.center_print("{} ^2vs {}".format(teams["red"][-1].name, teams["blue"][-1].name))

    @minqlx.delay(3)
    def handle_player_disco(self, player, reason):
        self.undelayed_handle_player_disco()

    def undelayed_handle_player_disco(self, player, reason):
        playercount = self.connected_players()

        # If it wasn't activated yet and we have right amount of players: broadcast
        if not self.duelmode and playercount == MIN_ACTIVE_PLAYERS:
            self.center_print("Type ^6!d ^7for DuelArena!")
            self.msg("Type ^6!d ^7for DuelArena!")

        # Potentially remove him from the subbed list
        if player.steam_id in self.psub:
            self.psub.remove(player.steam_id)

        # Turn duelarena on/off depending on the players
        self.duelarena_switch("p_disco_hook")

        # if duelmode is not yet actived after the switch, and we have the right amount of players: broadcast
        if not self.duelmode and playercount == MAX_ACTIVE_PLAYERS:
            self.center_print("Type ^6!d ^7for DuelArena!")
            self.msg("Type ^6!d ^7for DuelArena!")

    # When a game is about to start and duelmode is active, initialize
    @minqlx.delay(3)
    def handle_game_countdown(self):
        self.undelayed_handle_game_countdown()

    def undelayed_handle_game_countdown(self):
        if self.duelmode:
            self.init_duel()

    def handle_game_end(self, data):

        if not self.game: return

        if not self.duelmode: return

        # put both players back to the queue, winner first position, loser last position
        winner, loser = self.extract_winning_and_losing_team_from_game_end_data(data)

        teams = self.teams()

        self.queue.insert(0, teams[loser][-1].steam_id)
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
        if (self.game is None) or (self.game.type_short != "ca"): return

        # Last round? Do nothing
        if self.game.roundlimit in [self.game.blue_score, self.game.red_score]:
            return

        if self.initduel:
            self.init_duel()
            return

        if not self.duelmode:
            return

        losing_team = self.extract_losing_team_from_round_end_data(data)
        if not losing_team:
            return  # Draw? Do nothing

        next_player = self.player(self.queue.pop())

        teams = self.teams()

        if next_player not in teams['spectator']:
            self.duelmode = False # next_player not on the list of spectators? Deactivate DuelArena
            return

        losing_player = teams[losing_team][-1]

        self.put_player_on_team(next_player, losing_team)
        self.put_player_to_spectators_and_back_in_duel_queue(losing_player)

    def extract_losing_team_from_round_end_data(self, data):
        if data["TEAM_WON"] == "RED": return "blue"
        if data["TEAM_WON"] == "BLUE": return "red"
        return None

    def put_player_on_team(self, next_player, losing_team):
        if losing_team == "red": self.player_red = next_player
        if losing_team == "blue": self.player_blue = next_player
        next_player.put(losing_team)

    def put_player_to_spectators_and_back_in_duel_queue(self, losing_player):
        self.queue.insert(0, losing_player.steam_id)
        losing_player.put("spectator")

    def cmd_duel(self, player, msg, channel):

        if self.connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!duel^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        if player.steam_id not in self.psub:
            if player.steam_id not in self.queue: self.queue.insert(0, player.steam_id)
            self.psub.append(player.steam_id)
            countdown = 3 - len(self.psub)
            if not self.duelmode and countdown > 0:
                self.msg(
                    "{} ^7entered the DuelArena queue. ^6{}^7 more players needed to start DuelArena. Type ^6!duel ^73or ^6!d ^7to enter DuelArena queue.".format(
                        player.name, countdown))
            else:
                self.msg(
                    "{} ^7entered the DuelArena. Type ^6!duel ^7or ^6!d ^7to join DuelArena queue.".format(player.name))
        elif player.steam_id in self.psub:
            if player.steam_id in self.queue: self.queue.remove(player.steam_id)
            self.psub.remove(player.steam_id)
            self.msg("{} ^7left DuelArena.".format(player.name))

        self.printqueue()
        self.duelarena_switch("duel_command")

    def cmd_printqueue(self, player, msg, channel):

        if self.connected_players() > MAX_ACTIVE_PLAYERS:
            player.tell(
                "^6!queue^7 command not available with ^6{}^7 or more players connected".format(MAX_ACTIVE_PLAYERS + 1))
            return

        self.printqueue()

    def printqueue(self):

        if len(self.queue) == 0:
            self.msg("There's no one in the queue yet. Type ^6!d ^7or ^6!duel ^7to enter the queue.")

        qstring = ""

        for s_id in self.queue:
            p = self.player(s_id)
            indicator = len(self.queue) - self.queue.index(s_id)
            place = "{}th".format(indicator)
            if indicator == 1:
                place = "1st"
            elif indicator == 2:
                place = "2nd"
            elif indicator == 3:
                place = "3rd"
            qstring = "^6{}^7: {} ".format(place, p.name) + qstring

        self.msg("DuelArena queue: {}".format(qstring))

    def init_duel(self):

        self.checklists()

        for _p in self.psub:
            if _p not in self.queue:
                self.queue.insert(0, _p)

        self.player_red = self.player(self.queue.pop())
        self.player_blue = self.player(self.queue.pop())

        self.move_players_to_teams()

        self.move_all_non_playing_players_to_spec()

        self.initduel = False

    def move_players_to_teams(self):

        teams = self.teams()

        if self.player_red in teams["red"]:
            if self.player_blue not in teams["blue"]:
                self.player_blue.put("blue")
            return

        if self.player_red in teams["blue"]:
            if self.player_blue not in teams["red"]:
                self.player_blue.put("red")
            return

        if self.player_blue in teams["blue"]:
            self.player_red.put("red")
            return

        if self.player_blue in teams["red"]:
            self.player_red.put("blue")
            return

        self.player_red.put("red")
        self.player_blue.put("blue")

    def move_all_non_playing_players_to_spec(self):

        teams = self.teams()

        for _p in teams['red'] + teams['blue']:
            if _p != self.player_red and _p != self.player_blue:
                _p.put("spectator")

    def duelarena_switch(self, caller):

        self.checklists()

        if self.duelmode:
            player_count = self.connected_players()
            if player_count > MAX_ACTIVE_PLAYERS or player_count < MIN_ACTIVE_PLAYERS or len(
                    self.psub) < MIN_ACTIVE_PLAYERS:
                self.duelmode = False
                self.msg("DuelArena has been deactivated! You are free to join.")
        elif not self.duelmode:
            if len(self.psub) >= MIN_ACTIVE_PLAYERS and len(self.psub) <= MAX_ACTIVE_PLAYERS:
                self.duelmode = True
                self.msg("DuelArena activated!")
                self.center_print("DuelArena activated!")
                if self.game and self.game.state == "in_progress":
                    self.initduel = True

        minqlx.console_command(
            "echo duelarena_switch ({}), duelmode={}, playercount={}, len_psub={}, initduel={}".format(caller,
                                                                                                       self.duelmode,
                                                                                                       self.connected_players(),
                                                                                                       len(self.psub),
                                                                                                       self.initduel))

    def checklists(self):
        self.queue[:] = [sid for sid in self.queue if self.player(sid) and self.player(sid).ping < 990]
        self.psub[:] = [sid for sid in self.psub if self.player(sid) and self.player(sid).ping < 990]

    ## Helper functions
    def connected_players(self):
        teams = self.teams()
        players = int(len(teams["red"] + teams["blue"] + teams["spectator"] + teams["free"]))
        return players
