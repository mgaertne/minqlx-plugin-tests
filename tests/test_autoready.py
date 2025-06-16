import time
import random
from datetime import datetime, timedelta

import pytest
from hamcrest import assert_that, equal_to, not_, is_

# noinspection PyProtectedMember
from mockito import unstub, mock, when, any_, verify, spy2, when2
from undecorated import undecorated

from minqlx_plugin_test import (
    setup_cvars,
    fake_player,
    connected_players,
    assert_plugin_center_printed,
    assert_plugin_played_sound,
)

from minqlx import Plugin, PlayerStats

import autoready
from autoready import CountdownThread, RandomIterator


@pytest.mark.usefixtures("cvars")
@pytest.mark.parametrize(
    "cvars",
    [
        "zmq_stats_enable=1,"
        "qlx_autoready_min_players=10,"
        "qlx_autoready_autostart_delay=180,"
        "qlx_autoready_min_seconds=30,"
        "qlx_autoready_timer_visible=60,"
        "qlx_autoready_disable_manual_readyup=0"
    ],
    indirect=True,
)
class TestAutoReady:
    @pytest.fixture(autouse=True)
    def timer(self):
        timer_ = mock(spec=CountdownThread, strict=False)
        when(timer_).start().thenReturn(None)
        when(timer_).stop().thenReturn(None)
        when(timer_).is_alive().thenReturn(False)
        when(autoready).CountdownThread(any_(int), timed_actions=any_(dict)).thenReturn(timer_)
        yield timer_
        unstub(timer_)

    @pytest.fixture
    def alive_timer(self, timer):
        when(timer).is_alive().thenReturn(True)
        yield timer
        unstub(timer)

    def setup_method(self):
        self.plugin = autoready.autoready()
        self.plugin.make_sure_game_really_starts = lambda _: None

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_readyup_by_default(self):
        player = fake_player(1, "Readying Player", team="red")
        connected_players(
            player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        return_val = self.plugin.handle_client_command(player, "readyup")

        assert_that(return_val, equal_to(True))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_disallows_readyup_when_configured(self):
        setup_cvars(
            {
                "zmq_stats_enable": "1",
                "qlx_autoready_min_players": "10",
                "qlx_autoready_autostart_delay": "180",
                "qlx_autoready_min_seconds": "30",
                "qlx_autoready_timer_visible": "60",
                "qlx_autoready_disable_manual_readyup": "1",
            }
        )

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(
            player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        return_val = plugin.handle_client_command(player, "readyup")

        assert_that(return_val, equal_to(False))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_readyup_when_configured_with_too_few_players(
        self,
    ):
        setup_cvars(
            {
                "zmq_stats_enable": "1",
                "qlx_autoready_min_players": "10",
                "qlx_autoready_autostart_delay": "180",
                "qlx_autoready_min_seconds": "30",
                "qlx_autoready_timer_visible": "60",
                "qlx_autoready_disable_manual_readyup": "1",
            }
        )

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(
            player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
        )

        return_val = plugin.handle_client_command(player, "readyup")

        assert_that(return_val, equal_to(True))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_other_commands(self):
        setup_cvars(
            {
                "zmq_stats_enable": "1",
                "qlx_autoready_min_players": "10",
                "qlx_autoready_autostart_delay": "180",
                "qlx_autoready_min_seconds": "30",
                "qlx_autoready_timer_visible": "60",
                "qlx_autoready_disable_manual_readyup": "1",
            }
        )

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(
            player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        return_val = plugin.handle_client_command(player, "score")

        assert_that(return_val, equal_to(True))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_map_change_with_no_running_timer(self, alive_timer):
        self.plugin.handle_map_change("campgrounds", "ca")

        verify(alive_timer, times=0).stop()
        assert_that(self.plugin.current_timer, equal_to(-1))

    def test_handle_map_change_with_expired_timer(self, timer):
        self.plugin.timer = timer
        self.plugin.handle_map_change("campgrounds", "ca")

        verify(timer, times=0).stop()
        assert_that(self.plugin.current_timer, equal_to(-1))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_map_change_stops_timer_and_remembers_remaining_seconds(self, alive_timer):
        alive_timer.seconds_left = 42
        self.plugin.timer = alive_timer

        self.plugin.handle_map_change("campgrounds", "ca")

        verify(alive_timer).stop()
        assert_that(self.plugin.current_timer, equal_to(42))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_game_countdown_with_no_timer(self, alive_timer):
        self.plugin.handle_game_countdown()

        verify(alive_timer, times=0).stop()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_game_countdown_resets_current_timer(self, timer):
        timer.seconds_left = 21
        self.plugin.timer = timer

        self.plugin.current_timer = 45

        self.plugin.handle_game_countdown()

        verify(timer).stop()
        assert_that(self.plugin.current_timer, equal_to(21))
        assert_that(self.plugin.timer, equal_to(timer))

    @pytest.mark.usefixtures("game_in_countdown")
    def test_handle_game_start_with_no_timer(self, timer):
        self.plugin.timer = None

        # noinspection PyTypeChecker
        self.plugin.handle_game_start({})

        verify(timer, times=0).stop()

    @pytest.mark.usefixtures("game_in_countdown")
    def test_handle_game_start_clears_current_timer(self, timer):
        timer.seconds_left = 21
        self.plugin.timer = timer

        self.plugin.current_timer = 45

        # noinspection PyTypeChecker
        self.plugin.handle_game_start({})

        verify(timer).stop()
        assert_that(self.plugin.current_timer, equal_to(-1))
        assert_that(self.plugin.timer, equal_to(None))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_team_switch_with_no_game(self, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        verify(timer, times=0).start()

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_with_game_not_in_warmup(self, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        verify(timer, times=0).start()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_player_switching_to_spec(self, timer):
        self.plugin.timer = timer

        switching_player = fake_player(1, "Switching Player", team="red")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "red", "spectator")

        verify(timer, times=0).start()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_timer_already_started(self, alive_timer):
        self.plugin.timer = alive_timer
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        verify(alive_timer, times=0).start()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_with_too_few_players(self, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        verify(timer, times=0).start()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_starts_autoready_timer(self, timer):
        self.plugin.timer = timer

        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        verify(timer).start()
        assert_that(self.plugin.current_timer, equal_to(180))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_restarts_autoready_timer_after_mapchange(self):
        self.plugin.current_timer = 42
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        assert_that(self.plugin.current_timer, equal_to(42))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_restarts_autoready_timer_after_close_call_mapchange(
        self,
    ):
        self.plugin.current_timer = 21
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(
            switching_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
        )

        self.plugin.handle_team_switch(switching_player, "spectator", "red")

        assert_that(self.plugin.current_timer, equal_to(30))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_player_disconnect_with_no_game(self):
        self.plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player)

        self.plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert_that(self.plugin.current_timer, equal_to(42))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_while_game_not_in_warmup(self):
        self.plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player)

        self.plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert_that(self.plugin.current_timer, equal_to(42))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_in_warmup_with_too_many_players(self):
        self.plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(
            disconnecting_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
            fake_player(9, "Other Player", team="red"),
            fake_player(10, "Other Player", team="blue"),
            fake_player(11, "Other Player", team="red"),
            fake_player(12, "Other Player", team="blue"),
        )

        self.plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert_that(self.plugin.current_timer, equal_to(42))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_disables_countdown_timer(self):
        self.plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(
            disconnecting_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
        )

        self.plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert_that(self.plugin.current_timer, equal_to(-1))

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_with_running_timer(self, alive_timer):
        self.plugin.timer = alive_timer
        self.plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(
            disconnecting_player,
            fake_player(2, "Other Player", team="blue"),
            fake_player(3, "Other Player", team="red"),
            fake_player(4, "Other Player", team="blue"),
            fake_player(5, "Other Player", team="red"),
            fake_player(6, "Other Player", team="blue"),
            fake_player(7, "Other Player", team="red"),
            fake_player(8, "Other Player", team="blue"),
        )

        self.plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        verify(alive_timer).stop()
        assert_that(self.plugin.timer, equal_to(None))
        assert_that(self.plugin.current_timer, equal_to(-1))

    def test_make_sure_game_really_starts_timer_no_longer_valid(self, alive_timer):
        plugin = autoready.autoready()
        plugin.timer = None

        undecorated(plugin.make_sure_game_really_starts)(plugin, "campgrounds")

        verify(alive_timer, times=0).stop()

    def test_make_sure_game_really_starts_map_changed_in_between(self, alive_timer, game_in_warmup):
        spy2(time.sleep)
        when2(time.sleep, ...).thenReturn(None)
        game_in_warmup.map = "thunderstruck"

        plugin = autoready.autoready()
        plugin.timer = alive_timer

        undecorated(plugin.make_sure_game_really_starts)(plugin, "campgrounds")

        verify(alive_timer, times=0).stop()

    def test_make_sure_game_really_starts_game_still_in_warmup(self, alive_timer, game_in_warmup):
        spy2(time.sleep)
        when2(time.sleep, ...).thenReturn(None)
        game_in_warmup.map = "campgrounds"
        connected_players()

        plugin = autoready.autoready()
        plugin.timer = alive_timer

        undecorated(plugin.make_sure_game_really_starts)(plugin, "campgrounds")

        verify(alive_timer).stop()
        verify(autoready).CountdownThread(30, timed_actions=any_())
        verify(alive_timer).start()

    # noinspection PyUnresolvedReferences,PyPropertyAccess
    def test_make_sure_game_really_starts_specs_non_responding_players(self, alive_timer, game_in_warmup):
        spy2(time.sleep)
        when2(time.sleep, ...).thenReturn(None)
        game_in_warmup.map = "campgrounds"
        pending_player1 = fake_player(1, "pending red player", team="red")
        pending_player1.stats = mock(spec=PlayerStats)
        pending_player1.stats.ping = -1
        pending_player2 = fake_player(42, "pending blue player", team="blue")
        pending_player2.stats = mock(spec=PlayerStats)
        pending_player2.stats.ping = -1
        other_red_player = fake_player(123, "asdf", team="red")
        other_red_player.stats = mock(spec=PlayerStats)
        other_red_player.stats.ping = 42
        other_blue_player = fake_player(456, "qwertz", team="blue")
        other_blue_player.stats = mock(spec=PlayerStats)
        other_blue_player.stats.ping = 120
        spec_player = fake_player(789, "spec", team="spectator")
        spec_player.stats = mock(spec=PlayerStats)
        spec_player.stats.ping = 11

        connected_players(
            other_red_player,
            pending_player2,
            other_blue_player,
            pending_player1,
            spec_player,
        )

        plugin = autoready.autoready()
        plugin.timer = alive_timer

        undecorated(plugin.make_sure_game_really_starts)(plugin, "campgrounds")

        pending_player1.assert_was_put_on("spectator")
        pending_player2.assert_was_put_on("spectator")

    def test_display_countdown_above_30(self):
        autoready.display_countdown(121)

        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^32^7:^301")

    def test_display_countdown_below_30(self):
        autoready.display_countdown(25)

        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^125")

    def test_blink(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)

        autoready.blink(8)

        verify(time).sleep(0.4)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108")

    def test_warning_blink(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)

        autoready.warning_blink(30, "thirty_second_warning")

        verify(time).sleep(0.4)
        assert_plugin_played_sound("thirty_second_warning")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^130")

    def test_double_blink(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)

        autoready.double_blink(8)

        verify(time, times=2).sleep(0.2)
        verify(time).sleep(0.3)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108", times=2)

    def test_shuffle_double_blink_when_diff_larger_than_one_player(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)
        spy2(Plugin.shuffle)
        when2(Plugin.shuffle).thenReturn(None)

        connected_players(
            fake_player(1, "Red Player1", team="red"),
            fake_player(2, "Red Player2", team="red"),
            fake_player(3, "Red Player3", team="red"),
            fake_player(4, "Red Player4", team="red"),
            fake_player(5, "Blue Player1", team="blue"),
            fake_player(6, "Blue Player2", team="blue"),
            fake_player(7, "Blue Player3", team="blue"),
            fake_player(8, "Blue Player4", team="blue"),
            fake_player(9, "Blue Player5", team="blue"),
            fake_player(10, "Blue Player10", team="blue"),
        )

        autoready.shuffle_double_blink(10)

        verify(time, times=2).sleep(0.2)
        verify(time).sleep(0.3)
        verify(Plugin).shuffle()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^110", times=2)

    def test_shuffle_double_blink_when_diff_one_player(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)
        spy2(Plugin.shuffle)
        when2(Plugin.shuffle).thenReturn(None)

        connected_players(
            fake_player(1, "Red Player1", team="red"),
            fake_player(2, "Red Player2", team="red"),
            fake_player(3, "Red Player3", team="red"),
            fake_player(4, "Red Player4", team="red"),
            fake_player(5, "Blue Player1", team="blue"),
            fake_player(6, "Blue Player2", team="blue"),
            fake_player(7, "Blue Player3", team="blue"),
            fake_player(8, "Blue Player4", team="blue"),
            fake_player(9, "Blue Player5", team="blue"),
        )

        autoready.shuffle_double_blink(10)

        verify(time, times=2).sleep(0.2)
        verify(time).sleep(0.3)
        verify(Plugin, times=0).shuffle()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^110", times=2)

    def test_wear_off_double_blink(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)

        autoready.wear_off_double_blink(8)

        verify(time, times=2).sleep(0.2)
        verify(time).sleep(0.3)
        assert_plugin_played_sound("sound/items/wearoff.ogg")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108", times=2)

    def test_allready(self):
        spy2(Plugin.allready)
        when2(Plugin.allready).thenReturn(None)

        autoready.allready(0)

        verify(Plugin).allready()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^20^7:^200")


class TestCountdownThread:
    def setup_method(self):
        spy2(time.sleep)
        when2(time.sleep, any_(float)).thenReturn(None)

        self.mocked_function42 = mock()
        self.mocked_function21 = mock()
        timed_test_actions = {42: self.mocked_function42, 21: self.mocked_function21}
        self.countdown_thread = CountdownThread(125, timed_actions=timed_test_actions)
        self.fake_thread_runtime = datetime(year=2022, month=4, day=4, hour=11, minute=11, second=11)
        self.countdown_thread._now = self.fake_thread_runtime

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_seconds_left_when_thread_has_not_been_started(self):
        assert_that(self.countdown_thread.seconds_left, equal_to(self.countdown_thread.duration))

    def test_seconds_left_when_thread_has_been_stopped_before(self):
        self.countdown_thread._remaining = 7

        assert_that(self.countdown_thread.seconds_left, equal_to(7))

    def test_seconds_left_when_thread_is_current_running(self):
        test_target_time = self.fake_thread_runtime + timedelta(seconds=11, milliseconds=999, microseconds=999)
        self.countdown_thread._target_time = test_target_time

        assert_that(self.countdown_thread.seconds_left, equal_to(11))

    def test_stop_when_thread_is_not_running(self):
        self.countdown_thread.stop()

        assert_that(self.countdown_thread.seconds_left, equal_to(self.countdown_thread.duration))

    def test_stop_when_target_time_is_unset(self):
        spy2(self.countdown_thread.is_alive)
        when2(self.countdown_thread.is_alive).thenReturn(True)

        self.countdown_thread.stop()

        assert_that(self.countdown_thread.seconds_left, equal_to(self.countdown_thread.duration))

    def test_stop_when_thread_is_running(self):
        spy2(self.countdown_thread.is_alive)
        when2(self.countdown_thread.is_alive).thenReturn(True)

        test_target_time = self.fake_thread_runtime + timedelta(seconds=11, milliseconds=999, microseconds=999)
        self.countdown_thread._target_time = test_target_time

        self.countdown_thread.stop()

        assert_that(self.countdown_thread.seconds_left, equal_to(11))

    def test_determine_timed_action_for_several_combinations(self):
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(42)
        assert_that(func_result, is_(self.mocked_function42))
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(41)
        assert_that(func_result, is_(self.mocked_function21))
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(21)
        assert_that(func_result, is_(self.mocked_function21))
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(20)
        assert_that(func_result, not_(is_(self.mocked_function42)))
        assert_that(func_result, not_(is_(self.mocked_function21)))

    def test_run_inner_loop_function(self):
        test_target_time = self.fake_thread_runtime + timedelta(seconds=35)
        self.countdown_thread._target_time = test_target_time

        self.countdown_thread.run_loop_step()

        verify(self.mocked_function21, times=1).__call__(any_(int))
        verify(time).sleep(0.0)

    def test_calculate_target_time(self):
        target_datetime = self.countdown_thread.calculate_target_time()

        assert_that(target_datetime, equal_to(self.fake_thread_runtime + timedelta(seconds=125)))


class TestRandomIterator:
    def setup_method(self):
        self.sequence = [1, 2, 3]
        self.random_sequence = [2, 1, 3]

        spy2(random.sample)
        when(random).sample(any_(list), any_(int)).thenReturn(self.random_sequence)

        self.random_iterator = RandomIterator(self.sequence)

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_random_iterator(self):
        returned_sequence: list[int] = []
        for i in range(6):
            returned_sequence.append(next(self.random_iterator))

        assert_that(returned_sequence, equal_to(2 * self.random_sequence))
        verify(random, times=2).sample(self.sequence, 3)
