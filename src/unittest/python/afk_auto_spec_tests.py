from minqlx_plugin_test import *

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from afk_auto_spec import *


class AfkAutoSpecTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "zmq_stats_enable": ("0", None),
            "qlx_autoSpecWarmup": (False, bool)
        })
        setup_game_in_progress()

        self.plugin = afk_auto_spec()

    def tearDown(self):
        unstub()

    def test_handle_player_inactive_player_is_put_to_spec(self):
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        self.plugin.handle_player_inactive(idle_player)

        assert_player_was_put_on(idle_player, "spectator")

    def test_handle_player_inactive_player_speccing_player_is_announced(self):
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        self.plugin.handle_player_inactive(idle_player)

        assert_plugin_sent_to_console(matches(".*Putting Idle Player.* to spec for inactivity."))

    def test_handle_player_inactive_stops_further_event_processing(self):
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        returned = self.plugin.handle_player_inactive(idle_player)

        assert_that(returned, is_(minqlx.RET_STOP_ALL))

    def test_handle_player_inactive_with_no_game_does_nothing(self):
        setup_no_game()
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        self.plugin.handle_player_inactive(idle_player)

        assert_player_was_put_on(idle_player, "spectator", times=0)

    def test_handle_player_inactive_during_warmup_does_nothing(self):
        setup_game_in_warmup()
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        self.plugin.handle_player_inactive(idle_player)

        assert_player_was_put_on(idle_player, "spectator", times=0)

    def test_handle_player_inactive_during_warmup_with_warmup_spec_enabled(self):
        setup_game_in_warmup()
        self.plugin.spec_warmup = True
        idle_player = fake_player(42, "Idle Player", "red")
        connected_players(idle_player)

        self.plugin.handle_player_inactive(idle_player)

        assert_player_was_put_on(idle_player, "spectator")
