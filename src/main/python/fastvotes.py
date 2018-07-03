import minqlx

from minqlx import Plugin


class fastvotepass(minqlx.Plugin):
    """
    This plugin modifies the default vote pass or fail behavior with customizeable logic.

    Uses:
    * qlx_fastvoteTypes (default: "map, kick") Vote types this plugin will care about.
    * qlx_fastvoteStrategy (default: "threshold") The strategy used to process faster pass/fail votes.
    Currently available options: threshold, participation

    For the threshold strategy, you may set/modify these additional cvars:
    * qlx_fastvoteThresholdFastPassDiff (default: 6) passes the callvote at this yes-no difference
    * qlx_fastvoteThresholdFastFailDiff (default: 5) fails the callvote at this no-yes difference

    For the participation strategy, you may set/modify this additional cvar:
    * qlx_fastvoteParticipationPercentage (default: 67) Passes/Fails the vote when the given percentage of currently
    connected players has participated and the result is not a draw.
    """

    def __init__(self):
        super().__init__()

        self.set_cvar_once("qlx_fastvoteTypes", "map, kick")
        self.set_cvar_once("qlx_fastvoteStrategy", "threshold")

        self.fastvote_types = self.get_cvar("qlx_fastvoteTypes", list)

        self.add_hook("vote", self.process_vote, priority=minqlx.PRI_LOWEST)
        self.add_hook("vote_called", self.handle_vote, priority=minqlx.PRI_LOWEST)
        self.add_hook("vote_ended", self.handle_vote_ended, priority=minqlx.PRI_LOWEST)

        self.track_vote = False

    def resolve_strategy_for_fastvote(self, strategy):
        return ThresholdFastVoteStrategy()

    def handle_vote(self, player, vote, args):
        if vote.lower() in self.fastvote_types:
            self.track_vote = True

    def handle_vote_ended(self, votes, vote, args, passed):
        self.track_vote = False

    def process_vote(self, player, yes):
        if not self.track_vote:
            return

        if not Plugin.is_vote_active():
            self.track_vote = False
            return

        votes = Plugin.current_vote_count()

        if not votes:
            return

        yes_votes = votes[0] + 1 if yes else votes[0]
        no_votes = votes[1] if yes else votes[1] + 1

        strategy = self.get_cvar("qlx_fastvoteStrategy", str)
        fastvote_strategy = self.resolve_strategy_for_fastvote(strategy)

        eval_result = fastvote_strategy.evaluate_votes(yes_votes, no_votes)
        if eval_result is None:
            return

        self.track_vote = False
        Plugin.force_vote(eval_result)


class ThresholdFastVoteStrategy:

    def __init__(self):
        Plugin.set_cvar_once("qlx_fastvoteThresholdFastPassDiff", 6)
        Plugin.set_cvar_once("qlx_fastvoteThresholdFastFailDiff", 5)

        self.threshold_fast_pass_diff = Plugin.get_cvar("qlx_fastvoteThresholdFastPassDiff", int)
        self.threshold_fast_fail_diff = Plugin.get_cvar("qlx_fastvoteThresholdFastFailDiff", int)

    def evaluate_votes(self, yes_votes, no_votes):
        diff = yes_votes - no_votes

        if diff >= self.threshold_fast_pass_diff:
            return True

        if diff <= -self.threshold_fast_fail_diff:
            return False

        return None


class ParticipationFastVoteStrategy:

    def __init__(self):
        Plugin.set_cvar_once("qlx_fastvoteParticipationPercentage", 67)

        self.participation_percentage = Plugin.get_cvar("qlx_fastvoteParticipationPercentage", int)

    def evaluate_votes(self, yes_votes, no_votes):
        num_connected_players = len(Plugin.players())

        current_participation = (yes_votes + no_votes)/num_connected_players * 100

        if current_participation >= self.participation_percentage:
            if yes_votes != no_votes:
                return yes_votes > no_votes

        return None
