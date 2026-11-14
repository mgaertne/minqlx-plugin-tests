from minqlx_plugin_test import setup_cvar
from mockito import any_, verify, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from custom_votes import custom_votes

scenarios("features/custom_votes.feature")


@given("the custom_votes plugin is loaded", target_fixture="plugin")
def _plugin_loaded():
    setup_cvar("g_allowSpecVote", "1")
    when2(minqlx.get_configstring, 9).thenReturn("")
    when2(minqlx.callvote, any_, any_).thenReturn(None)
    when2(minqlx.client_command, any_, any_).thenReturn(True)
    return custom_votes()


@given("spectators are not allowed to call votes")
def _spectators_not_allowed():
    setup_cvar("g_allowSpecVote", "0")


@given(parsers.parse('{name:w} is on the "{team}" team'))
def _is_on_team(players, name, team):
    players[name].team = team


@given(parsers.parse('a vote "{vote}" is running'))
def _vote_is_running(vote):
    when2(minqlx.get_configstring, 9).thenReturn(vote)


@when_step(parsers.parse('Alice calls the vote "{vote}"'), target_fixture="vote_called_result")
def _alice_calls_vote(plugin, players, vote):
    name, _, args = vote.partition(" ")
    return minqlx.EVENT_DISPATCHERS["vote_called"].dispatch(players["Alice"], name, args)


@then(parsers.parse('the vote "{command}" is started as "{display}"'))
def _vote_is_started(command, display):
    verify(minqlx).callvote(command, display)


@then("no vote is started")
def _no_vote_is_started():
    verify(minqlx, times=0).callvote(any_, any_)


@then("Alice votes yes for it")
def _alice_votes_yes(players):
    verify(minqlx).client_command(players["Alice"].id, "vote yes")


@then(parsers.parse('Alice is told "{text}"'))
def _alice_is_told(players, text):
    players["Alice"].assert_was_told(text.replace("\\n", "\n"))


@then("the vote is taken over by the plugin")
def _vote_is_taken_over(vote_called_result):
    assert vote_called_result is False


@then("the vote is passed on to the server")
def _vote_is_passed_on(vote_called_result):
    assert vote_called_result is not False
