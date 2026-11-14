from minqlx_plugin_test import setup_cvars
from mockito import any_, verify, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from fastvotes import fastvotes

scenarios("features/fastvotes.feature")


@given(parsers.parse('the fastvotes plugin is loaded with the "{strategy}" strategy'), target_fixture="plugin")
def _plugin_loaded(strategy):
    setup_cvars(
        {
            "qlx_fastvoteTypes": "map, kick",
            "qlx_fastvoteStrategy": strategy,
            "qlx_fastvoteThresholdFastPassDiff": "6",
            "qlx_fastvoteThresholdFastFailDiff": "5",
            "qlx_fastvoteParticipationPercentage": "0.67",
        }
    )
    when2(minqlx.force_vote, any_).thenReturn(True)
    return fastvotes()


@given(parsers.parse('a "{vote}" vote is running with {yes:d} yes and {no:d} no votes'))
def _vote_is_running(plugin, vote, yes, no):
    when2(minqlx.get_configstring, 9).thenReturn(f"{vote} campgrounds")
    when2(minqlx.get_configstring, 10).thenReturn(str(yes))
    when2(minqlx.get_configstring, 11).thenReturn(str(no))
    minqlx.EVENT_DISPATCHERS["vote_started"].dispatch(vote, "campgrounds")


@given("the vote is over")
def _vote_is_over():
    when2(minqlx.get_configstring, 9).thenReturn("")


@when_step(parsers.parse("{name:w} votes {answer}"))
def _votes(players, name, answer):
    minqlx.EVENT_DISPATCHERS["vote"].dispatch(players[name], answer == "yes")


@then("the vote is passed immediately")
def _vote_is_passed():
    verify(minqlx).force_vote(True)


@then("the vote is passed immediately once")
def _vote_is_passed_once():
    verify(minqlx, times=1).force_vote(True)


@then("the vote is failed immediately")
def _vote_is_failed():
    verify(minqlx).force_vote(False)


@then("the vote is left running")
def _vote_is_left_running():
    verify(minqlx, times=0).force_vote(any_)
