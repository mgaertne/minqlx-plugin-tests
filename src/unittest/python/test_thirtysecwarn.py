import random
import time
import unittest

from mockito import unstub, patch, verify  # type: ignore
from mockito.matchers import any_  # type: ignore
from hamcrest import assert_that, none, is_

from undecorated import undecorated  # type: ignore

from thirtysecwarn import thirtysecwarn

from minqlx_plugin_test import setup_plugin, setup_cvars, setup_cvar, setup_no_game, assert_plugin_played_sound, \
    setup_game_in_progress, setup_game_in_warmup


class TestThirtySecondWarnPlugin(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        self.warner = thirtysecwarn()
        setup_cvars({
            "qlx_thirtySecondWarnAnnouncer": "standard"
        })

    def tearDown(self):
        unstub()

    def test_standard(self):
        setup_cvar("qlx_thirtySecondWarnAnnouncer", "standard")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo/30_second_warning.ogg"))

    def test_female(self):
        setup_cvar("qlx_thirtySecondWarnAnnouncer", "female")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo_female/30_second_warning.ogg"))

    def test_evil(self):
        setup_cvar("qlx_thirtySecondWarnAnnouncer", "evil")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo_evil/30_second_warning.ogg"))

    def test_non_existing_reverts_to_standard(self):
        setup_cvar("qlx_thirtySecondWarnAnnouncer", "invalid")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo/30_second_warning.ogg"))

    # noinspection PyMethodMayBeStatic
    def hardcoded_choice(self, _seq):
        return "asdf", "randomvoice"

    def test_random(self):
        random.choice = self.hardcoded_choice
        setup_cvar("qlx_thirtySecondWarnAnnouncer", "random")
        assert_that(self.warner.get_announcer_sound(), is_("randomvoice"))

    def test_plays_no_sound_when_game_is_not_running_anymore(self):
        setup_no_game()

        undecorated(self.warner.play_thirty_second_warning)(self.warner, 4)

        assert_plugin_played_sound(any_(str), times=0)

    def test_plays_no_sound_when_game_is_not_clan_arena(self):
        setup_game_in_progress(game_type="ft")

        undecorated(self.warner.play_thirty_second_warning)(self.warner, 4)

        assert_plugin_played_sound(any_(str), times=0)

    def test_plays_no_sound_when_game_not_in_progress(self):
        setup_game_in_warmup()

        undecorated(self.warner.play_thirty_second_warning)(self.warner, 4)

        assert_plugin_played_sound(any_(str), times=0)

    def test_plays_no_sound_when_next_round_started(self):
        calling_round_number = 4
        setup_game_in_progress(game_type="ca")
        self.warner.timer_round_number = calling_round_number + 1

        undecorated(self.warner.play_thirty_second_warning)(self.warner, calling_round_number)

        assert_plugin_played_sound(any_(str), times=0)

    def test_plays_sound_when_round_still_running(self):
        warner_thread_name = "test_plays_sound_when_round_still_running1"
        setup_game_in_progress(game_type="ca")
        self.warner.warner_thread_name = warner_thread_name

        undecorated(self.warner.play_thirty_second_warning)(self.warner, warner_thread_name)

        assert_plugin_played_sound(any_(str))

    def test_game_start_initializes_timer_round_number(self):
        self.warner.warner_thread_name = "test_game_start_initializes_timer_round_number1"

        self.warner.handle_game_start(None)

        assert_that(self.warner.warner_thread_name, none())

    def test_round_end_increases_round_number(self):
        self.warner.warner_thread_name = "test_round_end_increases_round_number1"

        self.warner.handle_round_end(None)

        assert_that(self.warner.warner_thread_name, none())

    def test_warntimer_sets_thread_name(self):
        setup_cvar("roundtimelimit", "180")
        patch(time.sleep, lambda _int: None)

        undecorated(self.warner.warntimer)(self.warner)

        assert_that(self.warner.warner_thread_name, any_(str))

    def test_warntimer_waits_until_30_seconds_before_roundtimelimit(self):
        setup_cvar("roundtimelimit", "180")
        patch(time.sleep, lambda _int: None)

        undecorated(self.warner.warntimer)(self.warner)

        verify(time).sleep(150)
