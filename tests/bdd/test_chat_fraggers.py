from types import SimpleNamespace

from minqlx_plugin_test import kill_data, setup_cvars
from mockito import any_, forget_invocations, verify
from pytest_bdd import given, parsers, scenarios, then
from pytest_bdd import when as when_step

import minqlx
from chat_fraggers import chat_fraggers

scenarios("features/chat_fraggers.feature")

WEAPONS = ("g", "mg", "sg", "gl", "rl", "lg", "rg", "pg", "bfg", "gh", "ng", "pl", "cg", "hmg")
MELEE_WEAPON = 15


@given(
    parsers.parse("the chat_fraggers plugin is loaded with a threshold of {threshold:d} damage"),
    target_fixture="plugin",
)
def _plugin_loaded(threshold):
    setup_cvars(
        {
            "qlx_chatFraggers_punishment_threshold": str(threshold),
            "qlx_chatFraggers_warning_text": "^1Shoot Chatters = Insta-Ban",
            "qlx_chatFraggers_punish_text": "^1You have been warned!",
        }
    )
    return chat_fraggers()


def _stand_on_team(player, team, chatting):
    player.team = team
    player.health = 100
    player.armor = 50
    player.is_alive = True
    player.state = SimpleNamespace(is_chatting=chatting)


@given(parsers.parse('{name:w} is on the "{team}" team'))
def _is_on_team(players, name, team):
    _stand_on_team(players[name], team, chatting=False)


@given(parsers.parse('{name:w} is on the "{team}" team and is chatting'))
def _is_chatting_on_team(players, name, team):
    _stand_on_team(players[name], team, chatting=True)


@given(parsers.parse("{name:w} is dead"))
def _is_dead(players, name):
    players[name].is_alive = False


@given(parsers.parse("{name:w} has {health:d} health"))
def _has_health(players, name, health):
    players[name].health = health


@given(parsers.parse("{name:w} starts over"))
def _starts_over(players, name):
    players[name].health = 100
    players[name].armor = 50
    forget_invocations(players[name])


@given("a new round is counting down")
def _new_round(plugin):
    minqlx.EVENT_DISPATCHERS["round_countdown"].dispatch(2)


@given(parsers.parse("{attacker:w} damaged {target:w} with {damage:d} points"))
def _damaged(plugin, players, attacker, target, damage):
    minqlx.EVENT_DISPATCHERS["damage"].dispatch(players[target], players[attacker], damage, 0, 0)


@when_step(parsers.parse("{attacker:w} damages {target:w} with {damage:d} points"))
def _damages(plugin, players, attacker, target, damage):
    minqlx.EVENT_DISPATCHERS["damage"].dispatch(players[target], players[attacker], damage, 0, 0)


@when_step(parsers.parse("{killer:w} kills {victim:w}"))
def _kills(plugin, players, killer, victim):
    minqlx.EVENT_DISPATCHERS["kill"].dispatch(players[victim], players[killer], kill_data())


@when_step(parsers.parse("{victim:w} dies without a killer"))
def _dies_alone(plugin, players, victim):
    minqlx.EVENT_DISPATCHERS["kill"].dispatch(players[victim], None, kill_data())


@then(parsers.parse('{name:w} sees "{text}"'))
def _sees(players, name, text):
    verify(players[name], atleast=1).center_print(text)


@then(parsers.parse("{name:w} sees no message"))
def _sees_nothing(players, name):
    verify(players[name], times=0).center_print(any_)


@then(parsers.parse("{name:w} is punished"))
def _is_punished(players, name):
    player = players[name]
    assert (player.health, player.armor) == (1, 0)
    verify(player).weapons(**dict.fromkeys(WEAPONS, False))
    verify(player).weapon(MELEE_WEAPON)


@then(parsers.parse("{name:w} is not punished"))
def _is_not_punished(players, name):
    player = players[name]
    assert (player.health, player.armor) == (100, 50)
    verify(player, times=0).weapon(any_)
