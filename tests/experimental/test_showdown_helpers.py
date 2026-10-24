from types import SimpleNamespace

from experimental.showdown import showdown


def test_showdown_pure_helpers():
    plugin = showdown.__new__(showdown)
    alive = SimpleNamespace(is_alive=True)
    dead = SimpleNamespace(is_alive=False)
    assert plugin.alive_players([alive, dead]) == [alive]
    assert plugin.other_team("red") == "blue"
    assert plugin.other_team("blue") == "red"
    assert plugin.other_team("spectator") is None


def test_showdown_reactivation_conditions():
    plugin = showdown.__new__(showdown)
    plugin.min_opp = 1
    plugin.showdown_activated = True
    assert plugin.should_reactivate_normal_game([], [])
    assert not plugin.should_reactivate_normal_game([1, 2], [])
    plugin.showdown_activated = False
    assert not plugin.should_reactivate_normal_game([], [])
