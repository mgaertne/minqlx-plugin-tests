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
            "qlx_qlstatsPrivacyWhitelist": (["public", "anonymous"], list)
        })
        setup_game_in_progress()
        self.plugin = qlstats_privacy_policy()

    def tearDown(self):
        unstub()

    def setup_balance_playerprivacy(self, player_privacy):
        player_info = {}
        for player, privacy in player_privacy:
            player_info[player.steam_id] = {"privacy": privacy}
        self.plugin._loaded_plugins["balance"]  = mock({'player_info': player_info})

    def setup_no_balance_plugin(self):
        if "balance" in self.plugin._loaded_plugins:
            del self.plugin._loaded_plugins["balance"]

    def test_handle_player_connect(self):
        connecting_player = fake_player(123, "Connecting Player")
        self.setup_balance_playerprivacy([(connecting_player, "public")])

        undecorated(self.plugin.handle_player_connect)(self.plugin, connecting_player)

        verify(self.plugin._loaded_plugins["balance"]).add_request(
            {connecting_player.steam_id: 'ca'}, self.plugin.callback_connect, minqlx.CHAT_CHANNEL)

    def test_handle_player_connect_no_balance_plugin(self):
        self.setup_no_balance_plugin()

        undecorated(self.plugin.handle_player_connect)(self.plugin, fake_player(123, "Connecting Player"))

        assert_plugin_sent_to_console(matches(".*Couldn't fetch ratings.*"))

    def test_callback_connect_players_not_kicked(self):
        self.plugin.callback_connect([], None)

        assert_plugin_sent_to_console(any, times=0)
