from typing import Dict

import pytest
from minqlx_plugin_test import setup_cvars
from mockito import any_, mock, verify
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from qlstats_privacy_policy import qlstats_privacy_policy

scenarios("features/qlstats_privacy_policy.feature")


@pytest.fixture(name="player_info")
def _player_info():
    player_info: Dict[int, Dict[str, str]] = {}
    minqlx.Plugin._loaded_plugins["balance"] = mock({"player_info": player_info})
    yield player_info
    minqlx.Plugin._loaded_plugins.pop("balance", None)


@given(
    parsers.parse(
        'the qlstats_privacy_policy plugin is loaded with the whitelist "{whitelist}" and {attempts:d} join attempts'
    ),
    target_fixture="plugin",
)
def _plugin_loaded(player_info, whitelist, attempts):
    setup_cvars(
        {
            "qlx_commandPrefix": "!",
            "qlx_qlstatsPrivacyKick": "0",
            "qlx_qlstatsPrivacyBlock": "0",
            "qlx_qlstatsPrivacyWhitelist": whitelist,
            "qlx_qlstatsPrivacyJoinAttempts": str(attempts),
        }
    )
    return qlstats_privacy_policy()


@given(parsers.parse('QLStats.net lists Alice with the privacy setting "{privacy}"'))
def _alice_listed(player_info, players, privacy):
    player_info[players["Alice"].steam_id] = {"privacy": privacy}


@when_step(
    parsers.parse('Alice tries to join the "{team}" team from spectators'),
    target_fixture="join_allowed",
)
def _alice_tries_to_join(players, team):
    return minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(players["Alice"], "spectator", team)


@when_step(
    parsers.parse('Alice tries to join the "{team}" team from spectators {times:d} times'),
    target_fixture="join_allowed",
)
def _alice_tries_to_join_repeatedly(players, team, times):
    allowed: object = True
    for _ in range(times):
        allowed = minqlx.EVENT_DISPATCHERS["team_switch_attempt"].dispatch(players["Alice"], "spectator", team)
    return allowed


@then(parsers.parse('Alice is told "{text}"'))
def _alice_is_told(players, text):
    players["Alice"].assert_was_told(text)


@then("Alice is kicked")
def _alice_is_kicked(players):
    verify(players["Alice"]).kick(any_(str))
