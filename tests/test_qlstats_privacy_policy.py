import time

import pytest
from mockito import unstub, mock, spy2, verify, when, when2  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import assert_that, equal_to, not_, contains_exactly

from undecorated import undecorated  # type: ignore

import requests
from requests import Response

from minqlx_plugin_test import (
    setup_cvars,
    fake_player,
    assert_plugin_sent_to_console,
    connected_players,
    assert_player_was_told,
    assert_player_received_center_print,
    assert_player_was_put_on,
)

import minqlx
from qlstats_privacy_policy import qlstats_privacy_policy, ConnectThread


class ThreadContextManager:
    def __init__(self, plugin):
        self.plugin = plugin

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        time.sleep(0.25)
        for thread in self.plugin.connectthreads.values():
            thread.join()


# noinspection PyPep8Naming
class TestQlstatsPrivacyPolicy:
    def setup_method(self):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "0",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
            }
        )
        self.setup_balance_playerprivacy([])
        self.plugin = qlstats_privacy_policy()

    @staticmethod
    def teardown_method():
        unstub()

    # noinspection PyMethodMayBeStatic
    def setup_balance_playerprivacy(self, player_privacy):
        player_info = {}
        for player, privacy in player_privacy:
            player_info[player.steam_id] = {"privacy": privacy}
        minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
            "balance"
        ] = mock({"player_info": player_info})

    @pytest.fixture
    def qlstats_response(self):
        spy2(minqlx.console_command)
        response = mock(Response)
        response.status_code = 200
        response.text = ""
        spy2(requests.get)
        when(requests).get(any_(), timeout=any_()).thenReturn(response)
        yield response
        unstub(response)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_plugin_disable(self):
        self.plugin.plugin_enabled = False
        connecting_player = fake_player(123, "Connecting Player")

        self.plugin.handle_player_connect(connecting_player)

        assert_plugin_sent_to_console(any, times=0)

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_player_connect_no_game_running(self):
        connecting_player = fake_player(123, "Connecting Player")

        self.plugin.handle_player_connect(connecting_player)

        assert_plugin_sent_to_console(any, times=0)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_no_balance_plugin(self, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        minqlx.Plugin._loaded_plugins.pop("balance")  # pylint: disable=protected-access
        connecting_player = fake_player(123, "Connecting Player")

        self.plugin.handle_player_connect(connecting_player)

        assert_that(self.plugin.plugin_enabled, equal_to(False))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_wrong_version_of_balance_plugin(self, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        minqlx.Plugin._loaded_plugins[  # pylint: disable=protected-access
            "balance"
        ] = mock(strict=True)
        connecting_player = fake_player(123, "Connecting Player")

        self.plugin.handle_player_connect(connecting_player)

        assert_that(self.plugin.plugin_enabled, equal_to(False))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect(self):
        connecting_player = fake_player(123, "Connecting Player")

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(self.plugin.plugins["balance"]).add_request(
            {connecting_player.steam_id: "ca"},
            self.plugin.callback_connect,
            minqlx.CHAT_CHANNEL,
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_fetches_elos_from_qlstats_connect_thread_still_alive(
        self,
    ):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        connect_thread = mock(ConnectThread)
        when(connect_thread).is_alive().thenReturn(True)
        self.plugin.connectthreads[connecting_player.steam_id] = connect_thread

        result = self.plugin.handle_player_connect(connecting_player)

        assert_that(result, equal_to("Fetching your qlstats settings..."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_postpones_connect_with_no_result(self):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        result = self.plugin.handle_player_connect(connecting_player)

        assert_that(result, equal_to("Fetching your qlstats settings..."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_dispatches_fetching_of_privacy_settings_from_qlstats(
        self,
    ):
        spy2(requests.get)
        when2(requests.get, any_(), timeout=any_()).thenReturn(None)

        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(requests).get(
            f"http://qlstats.net/belo/{connecting_player.steam_id}", timeout=any_()
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_logs_error_if_result_status_not_ok(self, qlstats_response):
        qlstats_response.status_code = 500

        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )
        self.plugin = qlstats_privacy_policy()

        connecting_player = fake_player(123, "Connecting Player")

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(minqlx).console_command(
            matches(".*QLStatsPrivacyError.*Invalid response code.*")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_logs_error_if_playerinfo_not_included(self, qlstats_response):
        when(qlstats_response).json().thenReturn({"invlied_response"})

        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(minqlx).console_command(
            matches(".*QLStatsPrivacyError.*Invalid response content.*")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_logs_error_if_steam_id_not_included(self, qlstats_response):
        when(qlstats_response).json().thenReturn({"playerinfo": {}})

        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(minqlx).console_command(
            matches(
                ".*QLStatsPrivacyError.*Response.*did not include.*requested player.*"
            )
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_logs_error_if_privacy_information_not_included(self, qlstats_response):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        when(qlstats_response).json().thenReturn(
            {"playerinfo": {str(connecting_player.steam_id): {}}}
        )

        with ThreadContextManager(self.plugin):
            self.plugin.handle_player_connect(connecting_player)

        verify(minqlx).console_command(
            matches(
                ".*QLStatsPrivacyError.*Response.*"
                "did not include.*privacy information.*"
            )
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_disallows_connect_with_wrong_privacy_settings(self, qlstats_response):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")

        when(qlstats_response).json().thenReturn(
            {"playerinfo": {str(connecting_player.steam_id): {"privacy": "private"}}}
        )

        with ThreadContextManager(self.plugin):
            returned = self.plugin.handle_player_connect(connecting_player)

        assert_that(
            returned,
            equal_to(
                "Error: Open qlstats.net, click Login/Sign-up, set privacy settings to "
                "public, anonymous, click save and reconnect!"
            ),
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_connect_allows_connect_with_right_privacy_settings(self, qlstats_response):
        setup_cvars(
            {
                "qlx_qlstatsPrivacyKick": "0",
                "qlx_qlstatsPrivacyBlock": "1",
                "qlx_qlstatsPrivacyWhitelist": "public, anonymous",
                "qlx_qlstatsPrivacyJoinAttempts": "5",
                "qlx_balanceApi": "belo",
            }
        )

        connecting_player = fake_player(123, "Connecting Player")
        self.setup_balance_playerprivacy([(connecting_player, "public")])

        when(qlstats_response).json().thenReturn(
            {"playerinfo": {str(connecting_player.steam_id): {"privacy": "public"}}}
        )

        with ThreadContextManager(self.plugin):
            returned = self.plugin.handle_player_connect(connecting_player)

        assert_that(returned, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_connect_players_plugin_disabled(self):
        self.plugin.plugin_enabled = False

        # noinspection PyTypeChecker
        self.plugin.callback_connect([123], None)

        assert_plugin_sent_to_console(any, times=0)

    def test_callback_connect_players_not_kicked(self):
        # noinspection PyTypeChecker
        self.plugin.callback_connect([123], None)

        assert_plugin_sent_to_console(any_, times=0)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_connect_player_has_exception(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.plugin.exceptions.add(not_kicked_player.steam_id)
        self.setup_balance_playerprivacy([(not_kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any_, any_(str)).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_connect_players_privacy_info_not_yet_available(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.setup_balance_playerprivacy({})
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any_, any_(str)).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_connect_player_gets_kicked_for_wrong_privacy_settings(self):
        self.plugin.kick_players = True
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.setup_balance_playerprivacy([(kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any_, any_(str)).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.callback_connect([kicked_player.steam_id], None)

        verify(self.plugin).delayed_kick(kicked_player.steam_id, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_connect_player_does_not_get_kicked_for_privacy_settings(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.setup_balance_playerprivacy([(not_kicked_player, "public")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any_, any_(str)).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any)

    @pytest.mark.usefixtures("game_in_progress")
    def test_callback_delayed_kick_kicks_player(self):
        undecorated(self.plugin.delayed_kick)(self.plugin, 123, "kicked")

        verify(minqlx.Plugin).kick(123, "kicked")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_gets_removed_from_exceptions(self):
        player = fake_player(123, "Test Player")
        self.plugin.exceptions.add(player.steam_id)

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(self.plugin.exceptions, not_(contains_exactly(player.steam_id)))  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_that_has_no_exception(self):
        player = fake_player(123, "Test Player")
        self.plugin.exceptions.add(456)

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(self.plugin.exceptions, equal_to({456}))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_clears_join_attempts(self):
        player = fake_player(123, "Test Player")
        self.plugin.join_attempts[player.steam_id] = 3

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(player.steam_id not in self.plugin.join_attempts, equal_to(True))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_no_balance_plugin(self, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        minqlx.Plugin._loaded_plugins.pop("balance")  # pylint: disable=protected-access
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_that(self.plugin.plugin_enabled, equal_to(False))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_plugin_disabled(self):
        self.plugin.plugin_enabled = False
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(
            switching_player, "spectator", "any"
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_team_switch_attempt_no_game_running(self):
        self.plugin = qlstats_privacy_policy()
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(
            switching_player, "spectator", "any"
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_has_exception_to_join(self):
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)
        self.plugin.exceptions.add(switching_player.steam_id)

        return_code = self.plugin.handle_team_switch_attempt(
            switching_player, "spectator", "any"
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_has_no_ratings(self):
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(
            switching_player, "spectator", "any"
        )

        assert_player_was_told(
            switching_player, matches("We couldn't fetch your ratings.*")
        )
        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}  # type: ignore

        return_code = self.plugin.handle_team_switch_attempt(
            specced_player, "spectator", "any"
        )

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(
            specced_player, matches(r"\^3Join not allowed.*")
        )
        assert_player_was_told(specced_player, matches(".*Open qlstats.net.*"))
        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        assert_that(
            specced_player.steam_id in self.plugin.join_attempts, equal_to(True)
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting_with_unlimited_join_attempts(
        self,
    ):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}  # type: ignore
        self.plugin.max_num_join_attempts = -1

        return_code = self.plugin.handle_team_switch_attempt(
            specced_player, "spectator", "any"
        )

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(
            specced_player, matches(r"\^3Join not allowed.*")
        )
        assert_player_was_told(specced_player, matches(r".*Open qlstats\.net.*"))
        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        assert_that(
            specced_player.steam_id not in self.plugin.join_attempts, equal_to(True)
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting_moved_to_spec(
        self,
    ):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}  # type: ignore

        self.plugin.handle_team_switch_attempt(specced_player, "red", "blue")

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(
            specced_player, matches(r"\^3Join not allowed.*")
        )
        assert_player_was_told(specced_player, matches(".*Open qlstats.net.*"))
        assert_player_was_put_on(specced_player, "spectator")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_with_max_join_attempts_equal_tokicked(
        self,
    ):
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.plugin.join_attempts[kicked_player.steam_id] = 0
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {kicked_player.steam_id: {"privacy": "private"}}  # type: ignore

        return_code = self.plugin.handle_team_switch_attempt(
            kicked_player, "spec", "blue"
        )

        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        verify(kicked_player).kick(any_())

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_join_attempts_are_decremented(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.join_attempts[specced_player.steam_id] = 3
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}  # type: ignore

        return_code = self.plugin.handle_team_switch_attempt(
            specced_player, "spectator", "blue"
        )

        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        assert_that(self.plugin.join_attempts[specced_player.steam_id], equal_to(2))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_with_correct_privacy_settings(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "public"}}  # type: ignore

        return_code = self.plugin.handle_team_switch_attempt(
            specced_player, "spectator", "blue"
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_team_switch_attempt_player_moved_to_spec_equal_tofine(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        # noinspection PyUnresolvedReferences
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}  # type: ignore

        return_code = self.plugin.handle_team_switch_attempt(
            specced_player, "red", "spectator"
        )

        assert_that(return_code, equal_to(minqlx.RET_NONE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_policy_exception_for_player_too_short(self, mock_channel):
        admin_player = fake_player(123, "Admin Player")
        connected_players(admin_player)

        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_policy_exception(
            admin_player, ["!except"], mock_channel
        )

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_policy_exception_for_connected_player(self, mock_channel):
        admin_player = fake_player(123, "Admin Player")
        exception_player = fake_player(456, "Excepted Player")
        connected_players(admin_player, exception_player)

        # noinspection PyTypeChecker
        self.plugin.cmd_policy_exception(
            admin_player, ["!except", "except"], mock_channel
        )

        assert_that(self.plugin.exceptions, equal_to({exception_player.steam_id}))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_policy_exception_for_no_matching_player(self, mock_channel):
        admin_player = fake_player(123, "Admin Player")
        connected_players(admin_player)

        # noinspection PyTypeChecker
        self.plugin.cmd_policy_exception(
            admin_player, ["!except", "except"], mock_channel
        )

        assert_player_was_told(admin_player, matches(".*Could not find player.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_policy_exception_for_more_than_one_matching_player(self, mock_channel):
        admin_player = fake_player(123, "Admin Player")
        exception_player = fake_player(456, "Excepted Player")
        connected_players(admin_player, exception_player)

        # noinspection PyTypeChecker
        self.plugin.cmd_policy_exception(
            admin_player, ["!except", "player"], mock_channel
        )

        assert_player_was_told(
            admin_player, matches(".*More than one matching spectator found.*")
        )

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_disable_policy_check(self, mock_channel):
        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        mock_channel.assert_was_replied(matches(".*QLStats policy check disabled.*"))
        assert_that(self.plugin.plugin_enabled, equal_to(False))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_with_no_balance_plugin(self, mock_channel):
        minqlx.Plugin._loaded_plugins.pop("balance")  # pylint: disable=protected-access
        self.plugin.plugin_enabled = False
        connected_players()

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        assert_that(self.plugin.plugin_enabled, equal_to(False))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_enables_policy_check(self, mock_channel):
        self.plugin.plugin_enabled = False
        connected_players()

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        assert_that(self.plugin.plugin_enabled, equal_to(True))
        mock_channel.assert_was_replied(matches(".*QLStats policy check enabled.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_moves_anonymous_players_to_spec(self, mock_channel):
        self.plugin.plugin_enabled = False
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(456, "Blue Player", "blue")
        connected_players(red_player, blue_player)
        self.setup_balance_playerprivacy(
            [(red_player, "public"), (blue_player, "private")]
        )

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        assert_player_was_put_on(red_player, "spectator", times=0)
        assert_player_was_told(red_player, any, times=0)
        assert_player_was_put_on(blue_player, "spectator")
        assert_player_was_told(blue_player, matches(".*Open qlstats.net.*"))
        assert_player_received_center_print(
            blue_player, matches(".*Join not allowed.*")
        )
        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_moves_unfetched_rated_players_to_spec(
        self, mock_channel
    ):
        self.plugin.plugin_enabled = False
        red_player = fake_player(123, "Red Player", "red")
        connected_players(
            red_player,
        )
        self.setup_balance_playerprivacy([])

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        assert_player_was_put_on(red_player, "spectator")
        assert_player_was_told(red_player, matches(".*couldn't fetch your ratings.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_kicks_players(self, mock_channel):
        self.plugin.plugin_enabled = False
        self.plugin.kick_players = True
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.setup_balance_playerprivacy([(kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any_, any_(str)).thenReturn(None)

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy"], mock_channel)

        verify(self.plugin).delayed_kick(kicked_player.steam_id, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_enabled(self, mock_channel):
        self.plugin.plugin_enabled = True

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy", "status"], mock_channel)

        mock_channel.assert_was_replied(matches(".*enabled.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_disabled(self, mock_channel):
        self.plugin.plugin_enabled = False

        # noinspection PyTypeChecker
        self.plugin.cmd_switch_plugin(None, ["!policy", "status"], mock_channel)

        mock_channel.assert_was_replied(matches(".*disabled.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_shows_usage(self, mock_channel):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_plugin(
            None, ["!policy", "asdf"], mock_channel
        )

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_switch_plugin_shows_usage_for_too_many_parameters(self, mock_channel):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_plugin(
            None, ["!policy", "too", "many", "parameters"], mock_channel
        )

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    @pytest.mark.usefixtures("game_in_progress")
    def test_remove_thread_removes_existing_connect_thread(self):
        # noinspection PyTypeChecker
        self.plugin.connectthreads[1234] = "asdf"

        undecorated(self.plugin.remove_thread)(self.plugin, 1234)

        assert_that(self.plugin.connectthreads, equal_to({}))

    @pytest.mark.usefixtures("game_in_progress")
    def test_remove_thread_does_nothing_if_thread_does_not_exist(self):
        # noinspection PyTypeChecker
        self.plugin.connectthreads[1234] = "asdf"

        undecorated(self.plugin.remove_thread)(self.plugin, 12345)

        assert_that(self.plugin.connectthreads, equal_to({1234: "asdf"}))
