from minqlx_plugin_test import *

from mockito import *
from hamcrest import *
import unittest

from thirtysecwarn import *

class TestDuelArenaWorker(unittest.TestCase):

    def setUp(self):
        self.warner = thirtysecwarn()
        setup_plugin(self.warner)
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "standard")

    def tearDown(self):
        unstub()

    def test_standard(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "standard")
        assert_that(self.warner.get_announcer_sound(), "sound/vo/30_second_warning.ogg")

    def test_female(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "female")
        assert_that(self.warner.get_announcer_sound(), "sound/vo_female/30_second_warning.ogg")

    def test_evil(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "evil")
        assert_that(self.warner.get_announcer_sound(), "sound/vo_evil/30_second_warning.ogg")

    def test_non_existing_reverts_to_standard(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "invalid")
        assert_that(self.warner.get_announcer_sound(), "sound/vo/30_second_warning.ogg")

    def test_random(self):
        random.seed(42)
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "random")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo/30_second_warning.ogg"))

    def test_plays_no_sound_when_game_is_not_running_anymore(self):
        setup_no_game()

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_no_sound_when_game_is_not_clan_arena(self):
        setup_game_in_progress(game_type="ft")

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_no_sound_when_game_not_in_progress(self):
        setup_game_in_warmup()

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))


    def test_plays_no_sound_when_next_round_started(self):
        calling_round_number = 4
        setup_game_in_progress(game_type="ca")
        self.warner.timer_round_number = calling_round_number + 1

        self.warner.undelayed_player_thirty_second_warning(calling_round_number)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_sound_when_round_still_running(self):
        calling_round_number = 4
        setup_game_in_progress(game_type="ca")
        self.warner.timer_round_number = calling_round_number

        self.warner.undelayed_player_thirty_second_warning(calling_round_number)

        verify(self.warner).play_sound(any(str))

    def test_game_start_initializes_timer_round_number(self):
        self.warner.timer_round_number = 7

        self.warner.handle_game_start(None)

        assert_that(self.warner.timer_round_number, is_(0))

    def test_round_end_increases_round_number(self):
        self.warner.timer_round_number = 4

        self.warner.handle_round_end(None)

        assert_that(self.warner.timer_round_number, is_(5))

