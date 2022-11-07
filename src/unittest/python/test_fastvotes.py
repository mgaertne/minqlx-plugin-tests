import unittest

from minqlx_plugin_test import setup_plugin, setup_cvars, fake_player, connected_players

from mockito import spy2, unstub, when2, verify  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import assert_that, instance_of, is_

from minqlx import Plugin
from fastvotes import fastvotes, ThresholdFastVoteStrategy, ParticipationFastVoteStrategy


class FastVotesTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "qlx_fastvoteTypes": "map",
            "qlx_fastvoteStrategy": "threshold",
            "qlx_fastvoteThresholdFastPassDiff": "6",
            "qlx_fastvoteThresholdFastFailDiff": "5",
            "qlx_fastvoteParticipationPercentage": "0.67"
        })
        spy2(Plugin.force_vote)
        spy2(Plugin.current_vote_count)

        self.plugin = fastvotes()

    def tearDown(self):
        unstub()

    # noinspection PyMethodMayBeStatic
    def setup_vote_in_progress(self):
        spy2(Plugin.is_vote_active)
        when2(Plugin.is_vote_active).thenReturn(True)

    # noinspection PyMethodMayBeStatic
    def current_vote_count_is(self, number_yes, number_no):
        when2(Plugin.current_vote_count).thenReturn((number_yes, number_no))

    def test_resolve_strategy_for_unknown_strategy(self):
        with self.assertRaises(ValueError) as context:
            self.plugin.resolve_strategy_for_fastvote("unknown")

        exception = context.exception
        assert_that(exception.args, matches(".*unknown value.*"))

    def test_resolve_strategy_for_threshold(self):
        strategy = self.plugin.resolve_strategy_for_fastvote("threshold")

        assert_that(strategy, instance_of(ThresholdFastVoteStrategy))

    def test_resolve_strategy_for_participation(self):
        strategy = self.plugin.resolve_strategy_for_fastvote("participation")

        assert_that(strategy, instance_of(ParticipationFastVoteStrategy))

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
        verify(Plugin, times=0).force_vote(any_)

    def test_process_vote_player_votes_on_an_untracked_vote(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = False
        self.current_vote_count_is(1, 5)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin, times=0).force_vote(any_)

    def test_process_vote_current_vote_count_not_available(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        when2(Plugin.current_vote_count).thenReturn(None)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(True))
        verify(Plugin, times=0).force_vote(any_)

    def test_process_vote_threshold_player_votes_yes_total_vote_count_does_not_meet_threshold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(1, 2)

        self.plugin.process_vote(fake_player(123, "Any Player"), True)

        assert_that(self.plugin.track_vote, is_(True))
        verify(Plugin, times=0).force_vote(any_)

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
        verify(Plugin, times=0).force_vote(any_)

    def test_process_vote_threshold_player_votes_no_and_hits_vote_threshold(self):
        self.setup_vote_in_progress()
        self.plugin.track_vote = True
        self.current_vote_count_is(1, 5)

        self.plugin.process_vote(fake_player(123, "Any Player"), False)

        assert_that(self.plugin.track_vote, is_(False))
        verify(Plugin).force_vote(False)


class ParticipationFastVoteStrategyTests(unittest.TestCase):

    def setUp(self):
        setup_cvars({
            "qlx_fastvoteParticipationPercentage": "0.67"
        })
        self.strategy = ParticipationFastVoteStrategy()

        connected_players(fake_player(123, "Player1"),
                          fake_player(456, "Player2"),
                          fake_player(789, "Player3"),
                          fake_player(321, "Player4"),
                          fake_player(654, "Player5"),
                          fake_player(987, "Player6"))

    def test_evaluate_participation_vote_threshold_not_met(self):
        result = self.strategy.evaluate_votes(3, 1)

        assert_that(result, is_(None))

    def test_evaluate_participation_vote_threshold_met_for_pass(self):
        result = self.strategy.evaluate_votes(4, 1)

        assert_that(result, is_(True))

    def test_evaluate_participation_vote_threshold_met_for_fail(self):
        result = self.strategy.evaluate_votes(1, 4)

        assert_that(result, is_(False))

    def test_evaluate_participation_vote_vote_draw(self):
        connected_players(fake_player(123, "Player1"),
                          fake_player(456, "Player2"),
                          fake_player(789, "Player3"),
                          fake_player(321, "Player4"),
                          fake_player(654, "Player5"),
                          fake_player(987, "Player6"),
                          fake_player(135, "Player7"),
                          fake_player(246, "Player8"))

        result = self.strategy.evaluate_votes(3, 3)

        assert_that(result, is_(None))
