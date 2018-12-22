from minqlx_plugin_test import *

import unittest
from mockito import *
from mockito.matchers import *
from hamcrest import *

from undecorated import undecorated

from qlstats_privacy_policy import *


class qlstats_privacy_policy_tests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "qlx_qlstatsPrivacyKick": (False, bool),
            "qlx_qlstatsPrivacyWhitelist": (["public", "anonymous"], list),
            "qlx_qlstatsPrivacyJoinAttempts": (5, int)
        })
        setup_game_in_progress()
        self.setup_balance_playerprivacy([])
        self.plugin = qlstats_privacy_policy()

    def tearDown(self):
        unstub()

    def setup_balance_playerprivacy(self, player_privacy):
        player_info = {}
        for player, privacy in player_privacy:
            player_info[player.steam_id] = {"privacy": privacy}
        minqlx.Plugin._loaded_plugins["balance"] = mock({'player_info': player_info})

    def test_handle_player_connect_no_game_running(self):
        setup_no_game()
        connecting_player = fake_player(123, "Connecting Player")

        undecorated(self.plugin.handle_player_connect)(self.plugin, connecting_player)

        assert_plugin_sent_to_console(any, times=0)

    def test_handle_player_connect_no_balance_plugin(self):
        minqlx.Plugin._loaded_plugins.pop("balance")
        connecting_player = fake_player(123, "Connecting Player")

        undecorated(self.plugin.handle_player_connect)(self.plugin, connecting_player)

        assert_that(self.plugin.plugin_enabled, is_(False))

    def test_handle_player_connect_wrong_version_of_balance_plugin(self):
        minqlx.Plugin._loaded_plugins["balance"] = mock(strict=True)
        connecting_player = fake_player(123, "Connecting Player")

        undecorated(self.plugin.handle_player_connect)(self.plugin, connecting_player)

        assert_that(self.plugin.plugin_enabled, is_(False))

    def test_handle_player_connect(self):
        connecting_player = fake_player(123, "Connecting Player")
        self.setup_balance_playerprivacy([(connecting_player, "public")])

        undecorated(self.plugin.handle_player_connect)(self.plugin, connecting_player)

        verify(self.plugin.plugins["balance"]).add_request(
            {connecting_player.steam_id: 'ca'}, self.plugin.callback_connect, minqlx.CHAT_CHANNEL)

    def test_callback_connect_players_plugin_disabled(self):
        self.plugin.plugin_enabled = False

        self.plugin.callback_connect([123], None)

        assert_plugin_sent_to_console(any, times=0)

    def test_callback_connect_players_not_kicked(self):
        self.plugin.callback_connect([123], None)

        assert_plugin_sent_to_console(any, times=0)

    def test_callback_connect_player_has_exception(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.plugin.exceptions.add(not_kicked_player.steam_id)
        self.setup_balance_playerprivacy([(not_kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any, any(str)).thenReturn(None)

        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any)

    def test_callback_connect_players_privacy_info_not_yet_available(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.setup_balance_playerprivacy({})
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any, any(str)).thenReturn(None)

        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any)

    def test_callback_connect_player_gets_kicked_for_wrong_privacy_settings(self):
        self.plugin.kick_players = True
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.setup_balance_playerprivacy([(kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any, any(str)).thenReturn(None)

        self.plugin.callback_connect([kicked_player.steam_id], None)

        verify(self.plugin).delayed_kick(kicked_player.steam_id, any)

    def test_callback_connect_player_does_not_get_kicked_for_privacy_settings(self):
        self.plugin.kick_players = True
        not_kicked_player = fake_player(123, "Test Player")
        connected_players(not_kicked_player)
        self.setup_balance_playerprivacy([(not_kicked_player, "public")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any, any(str)).thenReturn(None)

        self.plugin.callback_connect([not_kicked_player.steam_id], None)

        verify(self.plugin, times=0).delayed_kick(not_kicked_player.steam_id, any)

    def test_callback_delayed_kick_kicks_player(self):
        undecorated(self.plugin.delayed_kick)(self.plugin, 123, "kicked")

        verify(minqlx.Plugin).kick(123, "kicked")

    def test_handle_player_disconnect_gets_removed_from_exceptions(self):
        player = fake_player(123, "Test Player")
        self.plugin.exceptions.add(player.steam_id)

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(self.plugin.exceptions, not_(contains(player.steam_id)))

    def test_handle_player_disconnect_that_has_no_exception(self):
        player = fake_player(123, "Test Player")
        self.plugin.exceptions.add(456)

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(self.plugin.exceptions, is_({456}))

    def test_handle_player_disconnect_clears_join_attempts(self):
        player = fake_player(123, "Test Player")
        self.plugin.join_attempts[player.steam_id] = 3

        self.plugin.handle_player_disconnect(player, "quit")

        assert_that(player.steam_id not in self.plugin.join_attempts, is_(True))

    def test_handle_team_switch_attempt_no_balance_plugin(self):
        minqlx.Plugin._loaded_plugins.pop("balance")
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_that(self.plugin.plugin_enabled, is_(False))

    def test_handle_team_switch_attempt_plugin_disabled(self):
        self.plugin.plugin_enabled = False
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_that(return_code, is_(None))

    def test_handle_team_switch_attempt_no_game_running(self):
        setup_no_game()
        self.plugin = qlstats_privacy_policy()
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_that(return_code, is_(None))

    def test_handle_team_switch_attempt_player_has_exception_to_join(self):
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)
        self.plugin.exceptions.add(switching_player.steam_id)

        return_code = self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_that(return_code, is_(None))

    def test_handle_team_switch_attempt_player_has_no_ratings(self):
        switching_player = fake_player(123, "Joining Player")
        connected_players(switching_player)

        return_code = self.plugin.handle_team_switch_attempt(switching_player, "spectator", "any")

        assert_player_was_told(switching_player, matches("We couldn't fetch your ratings.*"))
        assert_that(return_code, is_(minqlx.RET_STOP_ALL))

    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}

        return_code = self.plugin.handle_team_switch_attempt(specced_player, "spectator", "any")

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(specced_player, matches("\^3Join not allowed.*"))
        assert_player_was_told(specced_player, matches("Open qlstats.net.*"))
        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_that(specced_player.steam_id in self.plugin.join_attempts, is_(True))

    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting_with_unlimited_join_attempts(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}
        self.plugin.max_num_join_attempts = -1

        return_code = self.plugin.handle_team_switch_attempt(specced_player, "spectator", "any")

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(specced_player, matches("\^3Join not allowed.*"))
        assert_player_was_told(specced_player, matches("Open qlstats.net.*"))
        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_that(specced_player.steam_id not in self.plugin.join_attempts, is_(True))

    def test_handle_team_switch_attempt_player_has_forbidden_privacy_setting_moved_to_spec(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}

        self.plugin.handle_team_switch_attempt(specced_player, "red", "blue")

        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))
        assert_player_received_center_print(specced_player, matches("\^3Join not allowed.*"))
        assert_player_was_told(specced_player, matches("Open qlstats.net.*"))
        assert_player_was_put_on(specced_player, "spectator")

    def test_handle_team_switch_attempt_player_with_max_join_attempts_is_kicked(self):
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.plugin.join_attempts[kicked_player.steam_id] = 0
        self.plugin.plugins["balance"].player_info = {kicked_player.steam_id: {"privacy": "private"}}

        return_code = self.plugin.handle_team_switch_attempt(kicked_player, "spec", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(kicked_player).kick(any())

    def test_handle_team_switch_attempt_player_join_attempts_are_decremented(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.join_attempts[specced_player.steam_id] = 3
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}

        return_code = self.plugin.handle_team_switch_attempt(specced_player, "spectator", "blue")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        assert_that(self.plugin.join_attempts[specced_player.steam_id], is_(2))

    def test_handle_team_switch_attempt_player_with_correct_privacy_settings(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "public"}}

        return_code = self.plugin.handle_team_switch_attempt(specced_player, "spectator", "blue")

        assert_that(return_code, is_(None))

    def test_handle_team_switch_attempt_player_moved_to_spec_is_fine(self):
        specced_player = fake_player(123, "Test Player")
        connected_players(specced_player)
        self.plugin.plugins["balance"].player_info = {specced_player.steam_id: {"privacy": "private"}}

        return_code = self.plugin.handle_team_switch_attempt(specced_player, "red", "spectator")

        assert_that(return_code, is_(None))

    def test_cmd_policy_exception_for_player_too_short(self):
        admin_player = fake_player(123, "Admin Player")
        connected_players(admin_player)

        return_code = self.plugin.cmd_policy_exception(admin_player, ["!except"], minqlx.CHAT_CHANNEL)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_policy_exception_for_connected_player(self):
        admin_player = fake_player(123, "Admin Player")
        exception_player = fake_player(456, "Excepted Player")
        connected_players(admin_player, exception_player)

        self.plugin.cmd_policy_exception(admin_player, ["!except", "except"], minqlx.CHAT_CHANNEL)

        assert_that(self.plugin.exceptions, is_({exception_player.steam_id}))

    def test_cmd_policy_exception_for_no_matching_player(self):
        admin_player = fake_player(123, "Admin Player")
        connected_players(admin_player)

        self.plugin.cmd_policy_exception(admin_player, ["!except", "except"], minqlx.CHAT_CHANNEL)

        assert_player_was_told(admin_player, matches(".*Could not find player.*"))

    def test_cmd_policy_exception_for_more_than_one_matching_player(self):
        admin_player = fake_player(123, "Admin Player")
        exception_player = fake_player(456, "Excepted Player")
        connected_players(admin_player, exception_player)

        self.plugin.cmd_policy_exception(admin_player, ["!except", "player"], minqlx.CHAT_CHANNEL)

        assert_player_was_told(admin_player, matches(".*More than one matching spectator found.*"))

    def test_cmd_switch_plugin_disable_policy_check(self):
        reply_channel = mocked_channel()

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        assert_channel_was_replied(reply_channel, matches(".*QLStats policy check disabled.*"))
        assert_that(self.plugin.plugin_enabled, is_(False))

    def test_cmd_switch_plugin_with_no_balance_plugin(self):
        minqlx.Plugin._loaded_plugins.pop("balance")
        self.plugin.plugin_enabled = False
        reply_channel = mocked_channel()
        connected_players()

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        assert_that(self.plugin.plugin_enabled, is_(False))

    def test_cmd_switch_plugin_enables_policy_check(self):
        self.plugin.plugin_enabled = False
        reply_channel = mocked_channel()
        connected_players()

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        assert_that(self.plugin.plugin_enabled, is_(True))
        assert_channel_was_replied(reply_channel, matches(".*QLStats policy check enabled.*"))

    def test_cmd_switch_plugin_moves_anonymous_players_to_spec(self):
        self.plugin.plugin_enabled = False
        reply_channel = mocked_channel()
        red_player = fake_player(123, "Red Player", "red")
        blue_player = fake_player(456, "Blue Player", "blue")
        connected_players(red_player, blue_player)
        self.setup_balance_playerprivacy([
            (red_player, "public"),
            (blue_player, "private")])

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        assert_player_was_put_on(red_player, "spectator", times=0)
        assert_player_was_told(red_player, any, times=0)
        assert_player_was_put_on(blue_player, "spectator")
        assert_player_was_told(blue_player, matches("Open qlstats.net.*"))
        assert_player_received_center_print(blue_player, matches(".*Join not allowed.*"))
        assert_plugin_sent_to_console(matches(".*not allowed to join.*"))

    def test_cmd_switch_plugin_moves_unfetched_rated_players_to_spec(self):
        self.plugin.plugin_enabled = False
        reply_channel = mocked_channel()
        red_player = fake_player(123, "Red Player", "red")
        connected_players(red_player, )
        self.setup_balance_playerprivacy([])

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        assert_player_was_put_on(red_player, "spectator")
        assert_player_was_told(red_player, matches(".*couldn't fetch your ratings.*"))

    def test_cmd_switch_plugin_kicks_players(self):
        self.plugin.plugin_enabled = False
        self.plugin.kick_players = True
        reply_channel = mocked_channel()
        kicked_player = fake_player(123, "Test Player")
        connected_players(kicked_player)
        self.setup_balance_playerprivacy([(kicked_player, "private")])
        self.plugin.delayed_kick = mock()
        when(self.plugin).delayed_kick(any, any(str)).thenReturn(None)

        self.plugin.cmd_switch_plugin(None, ["!policy"], reply_channel)

        verify(self.plugin).delayed_kick(kicked_player.steam_id, any)

    def test_cmd_switch_plugin_enabled(self):
        self.plugin.plugin_enabled = True
        reply_channel = mocked_channel()

        self.plugin.cmd_switch_plugin(None, ["!policy", "status"], reply_channel)

        assert_channel_was_replied(reply_channel, matches(".*enabled.*"))

    def test_cmd_switch_plugin_disabled(self):
        self.plugin.plugin_enabled = False
        reply_channel = mocked_channel()

        self.plugin.cmd_switch_plugin(None, ["!policy", "status"], reply_channel)

        assert_channel_was_replied(reply_channel, matches(".*disabled.*"))

    def test_cmd_switch_plugin_shows_usage(self):
        reply_channel = mocked_channel()

        return_code = self.plugin.cmd_switch_plugin(None, ["!policy", "asdf"], reply_channel)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_switch_plugin_shows_usage_for_too_many_parameters(self):
        reply_channel = mocked_channel()

        return_code = self.plugin.cmd_switch_plugin(None, ["!policy", "too", "many", "parameters"], reply_channel)

        assert_that(return_code, is_(minqlx.RET_USAGE))