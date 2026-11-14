from minqlx_plugin_test import setup_cvars
from mockito import any_, verify, when2
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from custom_modes_vote import custom_modes_vote
from minqlx import Plugin

scenarios("features/custom_modes_vote.feature")


@given(
    parsers.parse('the custom_modes_vote plugin is loaded with "{mode}" as the default mode'),
    target_fixture="plugin",
)
def _plugin_loaded(mode):
    setup_cvars({"qlx_commandPrefix": "!", "qlx_modeVoteNewMapDefault": mode})
    when2(minqlx.console_command, any_).thenReturn(None)
    when2(minqlx.client_command, any_, any_).thenReturn(True)
    when2(Plugin.callvote, any_, any_).thenReturn(None)
    return custom_modes_vote()


@given(parsers.parse('the server runs in "{mode}" mode'))
def _server_runs_in(plugin, mode):
    plugin.mode = mode


@given(parsers.parse('a vote "{vote}" is running'))
def _vote_is_running(vote):
    when2(minqlx.get_configstring, 9).thenReturn(vote)
    when2(minqlx.get_configstring, 10).thenReturn("5")
    when2(minqlx.get_configstring, 11).thenReturn("1")


@when_step("a new map is loaded")
def _new_map_is_loaded(plugin):
    minqlx.EVENT_DISPATCHERS["map"].dispatch("campgrounds", "ca")


@when_step(parsers.parse('Alice calls the vote "{vote}"'), target_fixture="vote_called_result")
def _alice_calls_vote(players, vote):
    name, args = vote.split(" ", 1)
    return minqlx.EVENT_DISPATCHERS["vote_called"].dispatch(players["Alice"], name, args)


@when_step("the vote passes")
def _vote_passes():
    minqlx.EVENT_DISPATCHERS["vote_ended"].dispatch(True)


@when_step("the vote fails")
def _vote_fails():
    minqlx.EVENT_DISPATCHERS["vote_ended"].dispatch(False)


@then(parsers.parse('the server console is set to "{command}"'))
def _console_is_set(command):
    verify(minqlx).console_command(command)


@then("the server console is not changed")
def _console_is_not_changed():
    verify(minqlx, times=0).console_command(any_)


@then("the vote is taken over by the plugin")
def _vote_is_taken_over(vote_called_result):
    assert vote_called_result is False


@then("the vote is passed on to the server")
def _vote_is_passed_on(vote_called_result):
    assert vote_called_result is not False


@then("Alice votes yes for it")
def _alice_votes_yes(players):
    verify(Plugin).callvote("mode pql", "mode pql")
    verify(minqlx).client_command(players["Alice"].id, "vote yes")


@then("no vote is started")
def _no_vote_is_started():
    verify(Plugin, times=0).callvote(any_, any_)
