from types import SimpleNamespace

from showdown import ALL_WEAPONS, random_iterator, showdown


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


def test_random_iterator_serves_every_element_before_repeating():
    iterator = random_iterator(["g", "gl", "rl"])

    assert sorted(next(iterator) for _ in range(3)) == ["g", "gl", "rl"]
    assert sorted(next(iterator) for _ in range(3)) == ["g", "gl", "rl"]


def test_weapon_is_identified_by_short_name_long_name_and_alias_ignoring_case():
    pummel = next(weapon for weapon in ALL_WEAPONS if weapon.shortname == "g")

    assert all(pummel.is_identified_by(text) for text in ["g", " G ", "pummel", "Gauntlet"])
    assert not pummel.is_identified_by("rl")
