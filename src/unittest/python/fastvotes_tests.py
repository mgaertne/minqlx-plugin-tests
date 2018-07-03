from minqlx_plugin_test import *

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from fastvotepass import *


class FastVotePassTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "qlx_fastvoteTypes": (["map"], list),
            "qlx_fastvoteStrategy": ("threshold", str),
            "qlx_fastvoteThresholdFastPassDiff": (6, int),
            "qlx_fastvoteThresholdFastFailDiff": (5, int)
        })
        spy2(Plugin.force_vote)
        spy2(Plugin.current_vote_count)

        self.plugin = fastvotepass()

    def tearDown(self):
        unstub()

    def setup_vote_in_progress(self):
        spy2(Plugin.is_vote_active)
        when2(Plugin.is_vote_active).thenReturn(True)

    def test_handle_vote_map_vote_called_tracks_votes(self):
        self.plugin.track_vote = False

        self.plugin.handle_vote(fake_player(123, "Any Player"), "map", "thunderstruck")

        assert_that(self.plugin.track_vote, is_(True))

    def test_handle_vote_map_vote_called_with_mixed_cases(self):
        self.plugin.track_vote = False

        self.plugin.handle_vote(fake_player(123, "Any Player"), "mAP", "theatreofpain")

        assert_that(self.plugin.track_vote, is_(True))

    def test_handle_vote_kick_player_is_not_tracked(self):
        self.plugin.track_vote = False

        self.plugin.handle_vote(fake_player(123, "Any Player"), "kick", "Fake Player")

        assert_that(self.plugin.track_vote, is_(False))

    def test_handle_vote_ended_resets_tracking(self):
        self.plugin.track_vote = True

        self.plugin.handle_vote_ended([3, 2], "map", "campgrounds", True)

        assert_that(self.plugin.track_vote, is_(False))

    def test_process_vote_with_no_active_vote_running(self):
        when2(Plugin.is_vote_active).thenReturn(False)
        self.plugin.track_vote = True

        self.plugin.process_vote(fake_player(123, "Any Player"), True)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin, times=0).force_vote(any)

    def test_process_vote_player_votes_on_an_untracked_vote(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = False
        self.current_vote_count_is(1, 5)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin, times=0).force_vote(any)

    def current_vote_count_is(self, number_yes, number_no):
        when2(Plugin.current_vote_count).thenReturn((number_yes, number_no))

    def test_process_vote_threshold_player_votes_yes_total_vote_count_does_not_meet_threshold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(1, 2)

        self.plugin.process_vote(fake_player(123, "Any Player"), True)

        assert_that(self.plugin.track_vote, is_(True))
        verify(Plugin, times=0).force_vote(any)

    def test_process_vote_threshold_player_votes_yes_and_hits_vote_threshold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(6, 1)

        self.plugin.process_vote(fake_player(123, "Any Player"), True)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin).force_vote(True)

    def test_process_vote_threshold_player_votes_no_and_does_not_meet_threashold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(1, 2)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(True))
        verify(Plugin, times=0).force_vote(any)

    def test_process_vote_threshold_player_votes_no_and_hits_vote_threshold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(1, 5)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin).force_vote(False)
