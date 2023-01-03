import pytest
import redis

from mockito import spy2, unstub, verify, mock, when  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import assert_that, equal_to

from minqlx_plugin_test import fake_player, assert_plugin_sent_to_console, setup_cvars

import minqlx
from minqlx import Plugin
from minqlx.database import Redis
from custom_modes_vote import custom_modes_vote


@pytest.fixture(name="mocked_db")
def _mocked_db():
    redis_mock = mock(spec=redis.StrictRedis)
    when(redis_mock).exists(any_).thenReturn(False)
    # noinspection PyPropertyAccess
    minqlx.database.Redis.r = redis_mock  # type: ignore

    yield redis_mock

    unstub()


class TestCustomModesVote:
    def setup_method(self):
        setup_cvars(
            {
                "qlx_modeVoteNewMapDefault": "vql",
            }
        )

        spy2(Plugin.callvote)
        spy2(minqlx.console_command)
        spy2(minqlx.client_command)

        self.plugin = custom_modes_vote()

    @staticmethod
    def teardown_method():
        unstub()

    def test_handle_map_change(self, mocked_db):
        self.plugin.database = Redis
        self.plugin.mode = "pql"

        self.plugin.handle_map_change("campgrounds", "ca")

        assert_that(self.plugin.mode, equal_to("vql"))

    def test_handle_map_change_already_in_default_mode(self, mocked_db):
        self.plugin.database = Redis
        self.plugin.mode = "vql"

        self.plugin.handle_map_change("campgrounds", "ca")

        verify(minqlx, times=0).console_command(any_)

    def test_handle_map_change_no_default_mode_configured(self):
        self.plugin.mode = "vql"
        self.plugin.default_mode = None

        self.plugin.handle_map_change("campgrounds", "ca")

        verify(minqlx, times=0).console_command(any_)

    def test_handle_vote_called_for_pql(self):
        voting_player = fake_player(123, "Voting Player", _id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "pql")

        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        verify(Plugin).callvote("mode pql", "mode pql")
        verify(minqlx).client_command(voting_player.id, "vote yes")
        assert_plugin_sent_to_console(matches(r".*called a vote\."))

    def test_handle_vote_called_for_unavailable_mode(self):
        voting_player = fake_player(123, "Voting Player", _id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "unavailable")

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_called_for_already_running_mode(self):
        voting_player = fake_player(123, "Voting Player", _id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "mode", "vql")

        assert_that(return_code, equal_to(minqlx.RET_STOP_ALL))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_called_for_not_for_mode_change(self):
        voting_player = fake_player(123, "Voting Player", _id=3)

        return_code = self.plugin.handle_vote_called(voting_player, "map", "campgrounds ca")

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        verify(Plugin, times=0).callvote(any_, any_)
        verify(minqlx, times=0).client_command(any_, any_)
        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_vote_ended_vote_passed(self):
        # noinspection PyTypeChecker
        self.plugin.handle_vote_ended(None, "mode", "pql", True)

        assert_that(self.plugin.mode, equal_to("pql"))

    def test_handle_vote_ended_vote_failed(self):
        # noinspection PyTypeChecker
        self.plugin.handle_vote_ended(None, "mode", "pql", False)

        assert_that(self.plugin.mode, equal_to("vql"))

    def test_handle_vote_ended_unavailable_mode_for_this_plugin(self):
        # noinspection PyTypeChecker
        self.plugin.handle_vote_ended(None, "mode", "unavailable", True)

        verify(minqlx, times=0).console_command(any_)

    def test_handle_vote_ended_not_vor_mode_vote(self):
        # noinspection PyTypeChecker
        self.plugin.handle_vote_ended(None, "map", "campgrounds ca", True)

        verify(minqlx, times=0).console_command(any_)

    def test_cmd_switch_mode_no_mode_given(self):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode"], None)

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    def test_cmd_switch_mode_too_many_parameters_given(self):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "asdf", "qwertz"], None)

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    def test_cmd_switch_mode_unavailable_mode(self):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "unavailable"], None)

        assert_that(return_code, equal_to(minqlx.RET_USAGE))

    def test_cmd_switch_mode_to_available_mode(self):
        # noinspection PyTypeChecker
        return_code = self.plugin.cmd_switch_mode(fake_player(123, "Admin"), ["!mode", "pql"], None)

        assert_that(return_code, equal_to(minqlx.RET_NONE))
        assert_that(self.plugin.mode, equal_to("pql"))
