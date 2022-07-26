import unittest

from minqlx_plugin_test import setup_plugin, setup_cvars, fake_player, assert_plugin_sent_to_console  # type: ignore

from mockito import spy2, unstub, verify  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import assert_that, is_

import minqlx
from minqlx import Plugin
from custom_modes_vote import custom_modes_vote


class CustomModesVoteTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()

        setup_cvars({
            "qlx_modeVoteNewMapDefault": "vql",
        })
        spy2(Plugin.callvote)
        spy2(minqlx.console_command)
        spy2(minqlx.client_command)

        self.plugin = custom_modes_vote()

    def tearDown(self):
        unstub()

    def test_handle_map_change(self):
        self.plugin.mode = "pql"

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.mode, is_("vql"))

    def test_handle_map_change_already_in_default_mode(self):
        self.plugin.mode = "vql"

        self.plugin.handle_map_change("campgrounds", "ca")

        verify(minqlx, times=0).console_command(any_)

    def test_handle_map_change_no_default_mode_configured(self):
        self.plugin.mode = "vql"
        self.plugin.default_mode = None

        self.plugin.handle_map_change("campgrounds", "ca")

        verify(minqlx, times=0).console_command(any_)

    def test_handle_vote_called_for_pql(self):
        voting_player = fake_player(123, "Voting Player", id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "pql")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(Plugin).callvote("mode pql", "mode pql")
        verify(minqlx).client_command(voting_player.id, "vote yes")
        assert_plugin_sent_to_console(matches(r".*called a vote\."))

    def test_handle_vote_called_for_unavailable_mode(self):
        voting_player = fake_player(123, "Voting Player", id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "unavailable")

        assert_that(return_code, is_(minqlx.RET_NONE))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_called_for_already_running_mode(self):
        voting_player = fake_player(123, "Voting Player", id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "vql")

        assert_that(return_code, is_(minqlx.RET_STOP_ALL))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_called_for_not_for_mode_change(self):
        voting_player = fake_player(123, "Voting Player", id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "map", "campgrounds ca")

        assert_that(return_code, is_(minqlx.RET_NONE))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_ended_vote_passed(self):
        self.plugin.handle_vote_ended(None, "mode", "pql", True)

        assert_that(self.plugin.mode, is_("pql"))

    def test_handle_vote_ended_vote_failed(self):
        self.plugin.handle_vote_ended(None, "mode", "pql", False)

        assert_that(self.plugin.mode, is_("vql"))

    def test_handle_vote_ended_unavailable_mode_for_this_plugin(self):
        self.plugin.handle_vote_ended(None, "mode", "unavailable", True)

        verify(minqlx, times=0).console_command(any_)

    def test_handle_vote_ended_not_vor_mode_vote(self):
        self.plugin.handle_vote_ended(None, "map", "campgrounds ca", True)

        verify(minqlx, times=0).console_command(any_)

    def test_cmd_switch_mode_no_mode_given(self):
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_switch_mode_too_many_parameters_given(self):
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "asdf", "qwertz"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_switch_mode_unavailable_mode(self):
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "unavailable"], None)

        assert_that(return_code, is_(minqlx.RET_USAGE))

    def test_cmd_switch_mode_to_available_mode(self):
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "pql"], None)

        assert_that(return_code, is_(minqlx.RET_NONE))
        assert_that(self.plugin.mode, is_("pql"))
