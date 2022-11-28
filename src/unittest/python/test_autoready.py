import time
import random
from datetime import datetime, timedelta
from unittest.mock import call, NonCallableMock, patch, Mock

import pytest
from pytest_mock import MockerFixture

# noinspection PyProtectedMember
from mockito import unstub  # type: ignore

from minqlx_plugin_test import setup_cvars, setup_plugin, fake_player, connected_players, \
    assert_plugin_center_printed, assert_plugin_played_sound

from minqlx import Plugin

import autoready
from autoready import CountdownThread, RandomIterator


class TestAutoReady:

    @pytest.fixture
    def timer(self, mocker: MockerFixture):
        timer_ = mocker.Mock(spec=CountdownThread)
        mocker.spy(timer_, "start")
        mocker.spy(timer_, "stop")
        mocker.patch("autoready.CountdownThread", return_value=timer_)
        return timer_

    @pytest.fixture
    def alive_timer(self, mocker, timer):
        mocker.patch.object(timer, "is_alive", return_value=True)
        return timer

    @pytest.fixture
    def plugin(self, mocker):
        mocker.patch("autoready.CountdownThread", new_callable=NonCallableMock)
        return autoready.autoready()

    @staticmethod
    def setup_method():
        setup_plugin()
        setup_cvars({
            "zmq_stats_enable": "1",
            "qlx_autoready_min_players": "10",
            "qlx_autoready_autostart_delay": "180",
            "qlx_autoready_min_seconds": "30",
            "qlx_autoready_timer_visible": "60",
            "qlx_autoready_disable_manual_readyup": "0"
        })

    @staticmethod
    def teardown_method():
        unstub()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_readyup_by_default(self, plugin):
        player = fake_player(1, "Readying Player", team="red")
        connected_players(player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        return_val = plugin.handle_client_command(player, "readyup")

        assert return_val

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_disallows_readyup_when_configured(self):
        setup_cvars({
            "zmq_stats_enable": "1",
            "qlx_autoready_min_players": "10",
            "qlx_autoready_autostart_delay": "180",
            "qlx_autoready_min_seconds": "30",
            "qlx_autoready_timer_visible": "60",
            "qlx_autoready_disable_manual_readyup": "1"
        })

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        return_val = plugin.handle_client_command(player, "readyup")

        assert not return_val

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_readyup_when_configured_with_too_few_players(self):
        setup_cvars({
            "zmq_stats_enable": "1",
            "qlx_autoready_min_players": "10",
            "qlx_autoready_autostart_delay": "180",
            "qlx_autoready_min_seconds": "30",
            "qlx_autoready_timer_visible": "60",
            "qlx_autoready_disable_manual_readyup": "1"
        })

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"))

        return_val = plugin.handle_client_command(player, "readyup")

        assert return_val

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_client_command_allows_other_commands(self):
        setup_cvars({
            "zmq_stats_enable": "1",
            "qlx_autoready_min_players": "10",
            "qlx_autoready_autostart_delay": "180",
            "qlx_autoready_min_seconds": "30",
            "qlx_autoready_timer_visible": "60",
            "qlx_autoready_disable_manual_readyup": "1"
        })

        plugin = autoready.autoready()

        player = fake_player(1, "Readying Player", team="red")
        connected_players(player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        return_val = plugin.handle_client_command(player, "score")

        assert return_val

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_map_change_with_no_running_timer(self, plugin, timer):
        plugin.handle_map_change("campgrounds", "ca")

        timer.stop.assert_not_called()
        assert plugin.current_timer == -1

    def test_handle_map_change_with_expired_timer(self, mocker, plugin, timer):
        plugin.timer = timer
        with mocker.patch.object(timer, "is_alive", return_value=False):
            plugin.handle_map_change("campgrounds", "ca")

        timer.stop.assert_not_called()
        assert plugin.current_timer == -1

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_map_change_stops_timer_and_remembers_remaining_seconds(self, plugin, alive_timer):
        alive_timer.seconds_left = 42
        plugin.timer = alive_timer

        plugin.handle_map_change("campgrounds", "ca")

        alive_timer.stop.assert_called_once()
        assert plugin.current_timer == 42

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_game_countdown_with_no_timer(self, plugin, timer):
        plugin.handle_game_countdown()

        timer.stop.assert_not_called()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_game_countdown_resets_current_timer(self, plugin, timer):
        plugin.timer = timer

        plugin.current_timer = 45

        plugin.handle_game_countdown()

        timer.stop.assert_called_once()
        assert plugin.current_timer == -1
        assert plugin.timer is None

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_team_switch_with_no_game(self, plugin, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        timer.start.assert_not_called()

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_with_game_not_in_warmup(self, plugin, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        timer.start.assert_not_called()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_player_switching_to_spec(self, plugin, timer):
        switching_player = fake_player(1, "Switching Player", team="red")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "red", "spectator")

        timer.start.assert_not_called()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_timer_already_started(self, plugin, alive_timer):
        plugin.timer = alive_timer
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        alive_timer.start.assert_not_called()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_with_too_few_players(self, plugin, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        timer.start.assert_not_called()

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_starts_autoready_timer(self, plugin, timer):
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        timer.start.assert_called_once()
        assert plugin.current_timer == 180

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_restarts_autoready_timer_after_mapchange(self, plugin, timer):
        plugin.current_timer = 42
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        assert plugin.current_timer == 42

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_team_switch_restarts_autoready_timer_after_close_call_mapchange(self, plugin, timer):
        plugin.current_timer = 21
        switching_player = fake_player(1, "Switching Player", team="spectator")
        connected_players(switching_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"),
                          fake_player(9, "Other Player", team="red"),
                          fake_player(10, "Other Player", team="blue"))

        plugin.handle_team_switch(switching_player, "spectator", "red")

        assert plugin.current_timer == 30

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_player_disconnect_with_no_game(self, plugin):
        plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player)

        plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert plugin.current_timer == 42

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_while_game_not_in_warmup(self, plugin):
        plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player)

        plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert plugin.current_timer == 42

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_in_warmup_with_too_many_players(self, plugin):
        plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player,
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
                          fake_player(12, "Other Player", team="blue"))

        plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert plugin.current_timer == 42

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_disables_countdown_timer(self, plugin):
        plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"))

        plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        assert plugin.current_timer == -1

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_player_disconnect_with_running_timer(self, plugin, alive_timer):
        plugin.timer = alive_timer
        plugin.current_timer = 42
        disconnecting_player = fake_player(1, "Disconnecting Player")
        connected_players(disconnecting_player,
                          fake_player(2, "Other Player", team="blue"),
                          fake_player(3, "Other Player", team="red"),
                          fake_player(4, "Other Player", team="blue"),
                          fake_player(5, "Other Player", team="red"),
                          fake_player(6, "Other Player", team="blue"),
                          fake_player(7, "Other Player", team="red"),
                          fake_player(8, "Other Player", team="blue"))

        plugin.handle_player_disconnect(disconnecting_player, "ragequit")

        alive_timer.stop.assert_called_once()
        assert plugin.timer is None
        assert plugin.current_timer == -1

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_display_countdown_above_30(self):
        autoready.display_countdown(121)

        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^32^7:^301")

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_display_countdown_below_30(self):
        autoready.display_countdown(25)

        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^125")

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_blink(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")

        autoready.blink(8)

        sleep_spy.assert_called_once_with(0.4)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108")

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_warning_blink(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")

        autoready.warning_blink(30, "thirty_second_warning")

        sleep_spy.assert_called_once_with(0.4)
        assert_plugin_played_sound("thirty_second_warning")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^130")

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_double_blink(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")

        autoready.double_blink(8)

        calls = [call(0.2), call(0.3), call(0.2)]
        sleep_spy.assert_has_calls(calls)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108", times=2)

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_shuffle_double_blink_when_diff_larger_than_one_player(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")
        shuffle_spy = mocker.spy(Plugin, "shuffle")

        connected_players(fake_player(1, "Red Player1", team="red"),
                          fake_player(2, "Red Player2", team="red"),
                          fake_player(3, "Red Player3", team="red"),
                          fake_player(4, "Red Player4", team="red"),
                          fake_player(5, "Blue Player1", team="blue"),
                          fake_player(6, "Blue Player2", team="blue"),
                          fake_player(7, "Blue Player3", team="blue"),
                          fake_player(8, "Blue Player4", team="blue"),
                          fake_player(9, "Blue Player5", team="blue"),
                          fake_player(10, "Blue Player10", team="blue"))

        autoready.shuffle_double_blink(10)

        calls = [call(0.2), call(0.3), call(0.2)]
        sleep_spy.assert_has_calls(calls)
        shuffle_spy.assert_called_once()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^110", times=2)

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_shuffle_double_blink_when_diff_one_player(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")
        shuffle_spy = mocker.spy(Plugin, "shuffle")

        connected_players(fake_player(1, "Red Player1", team="red"),
                          fake_player(2, "Red Player2", team="red"),
                          fake_player(3, "Red Player3", team="red"),
                          fake_player(4, "Red Player4", team="red"),
                          fake_player(5, "Blue Player1", team="blue"),
                          fake_player(6, "Blue Player2", team="blue"),
                          fake_player(7, "Blue Player3", team="blue"),
                          fake_player(8, "Blue Player4", team="blue"),
                          fake_player(9, "Blue Player5", team="blue"))

        autoready.shuffle_double_blink(10)

        calls = [call(0.2), call(0.3), call(0.2)]
        sleep_spy.assert_has_calls(calls)
        shuffle_spy.assert_not_called()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^110", times=2)

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_wear_off_double_blink(self, mocker):
        mocker.patch("time.sleep")
        sleep_spy = mocker.spy(time, "sleep")

        autoready.wear_off_double_blink(8)

        calls = [call(0.2), call(0.3), call(0.2)]
        sleep_spy.assert_has_calls(calls)
        assert_plugin_played_sound("sound/items/wearoff.ogg")
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^1 ^7:^1  ", times=2)
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^10^7:^108", times=2)

    # noinspection PyMethodMayBeStatic
    @pytest.mark.usefixtures("game_in_warmup")
    def test_allready(self, mocker):
        mocker.patch("minqlx.Plugin.allready")
        allready_spy = mocker.spy(Plugin, "allready")

        autoready.allready(0)

        allready_spy.assert_called_once()
        assert_plugin_center_printed("Match will ^2auto-start^7 in\n^20^7:^200")


# noinspection PyPep8Naming
class TestCountdownThread:
    def setup_method(self):
        patch("time.sleep", return_value=None)

        self.mocked_function42 = Mock()
        self.mocked_function21 = Mock()
        timed_test_actions = {42: self.mocked_function42, 21: self.mocked_function21}
        self.countdown_thread = CountdownThread(125, timed_actions=timed_test_actions)  # type: ignore
        self.fake_thread_runtime = datetime(year=2022, month=4, day=4, hour=11, minute=11, second=11)
        self.countdown_thread._now = self.fake_thread_runtime  # pylint: disable=W0212

    @staticmethod
    def teardown_method():
        unstub()

    def test_seconds_left_when_thread_has_not_been_started(self):
        assert self.countdown_thread.seconds_left == self.countdown_thread.duration

    def test_seconds_left_when_thread_has_been_stopped_before(self):
        self.countdown_thread._remaining = 7  # pylint: disable=W0212

        assert self.countdown_thread.seconds_left == 7

    def test_seconds_left_when_thread_is_current_running(self):
        test_target_time = self.fake_thread_runtime + timedelta(seconds=11, milliseconds=999, microseconds=999)
        self.countdown_thread._target_time = test_target_time  # pylint: disable=W0212

        assert self.countdown_thread.seconds_left == 11

    def test_stop_when_thread_is_not_running(self):
        self.countdown_thread.stop()

        assert self.countdown_thread.seconds_left == self.countdown_thread.duration

    def test_stop_when_target_time_is_unset(self, mocker):
        mocker.patch.object(self.countdown_thread, "is_alive", return_value=True)

        self.countdown_thread.stop()

        assert self.countdown_thread.seconds_left == self.countdown_thread.duration

    def test_stop_when_thread_is_running(self, mocker):
        mocker.patch.object(self.countdown_thread, "is_alive", return_value=True)
        test_target_time = self.fake_thread_runtime + timedelta(seconds=11, milliseconds=999, microseconds=999)
        self.countdown_thread._target_time = test_target_time  # pylint: disable=W0212

        self.countdown_thread.stop()

        assert self.countdown_thread.seconds_left == 11

    def test_determine_timed_action_for_several_combinations(self):
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(42)
        assert func_result == self.mocked_function42
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(41)
        assert func_result == self.mocked_function21
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(21)
        assert func_result == self.mocked_function21
        func_result = self.countdown_thread.determine_timed_action_for_remaining_seconds(20)
        assert func_result != self.mocked_function42
        assert func_result != self.mocked_function21

    def test_run_inner_loop_function(self, mocker):
        sleep_spy = mocker.spy(time, "sleep")
        test_target_time = self.fake_thread_runtime + timedelta(seconds=35)
        self.countdown_thread._target_time = test_target_time  # pylint: disable=W0212

        self.countdown_thread.run_loop_step()

        self.mocked_function21.assert_called_once()
        sleep_spy.assert_called_once_with(0.0)

    def test_calculate_target_time(self):
        target_datetime = self.countdown_thread.calculate_target_time()

        assert target_datetime == self.fake_thread_runtime + timedelta(seconds=125)


# noinspection PyPep8Naming
class TestRandomIterator:

    sequence = [1, 2, 3]
    random_sequence = [2, 1, 3]

    @pytest.fixture
    def random_iterator(self, mocker):
        mocker.patch("random.sample", return_value=self.random_sequence)
        self.sample_spy = mocker.spy(random, "sample")
        return iter(RandomIterator(self.sequence))

    def test_random_iterator(self, random_iterator):
        returned_sequence: list[int] = []
        for i in range(6):
            returned_sequence.append(next(random_iterator))

        assert returned_sequence == 2 * self.random_sequence
        calls = [call(self.sequence, 3), call(self.sequence, 3)]
        self.sample_spy.assert_has_calls(calls)
