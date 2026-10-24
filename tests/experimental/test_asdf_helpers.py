import pytest

from experimental.asdf import Weapon, WeaponStatsEntry


@pytest.mark.parametrize(
    "name, ammo", [("MACHINEGUN", "mg"), ("ROCKET", "rl"), ("CHAINGUN", "cg"), ("unknown", "other")]
)
def test_weapon_ammo_types(name, ammo):
    weapon = Weapon(name)
    assert weapon.ammo_type() == ammo
    assert weapon.weapon_name() == ammo.upper()


def test_weapon_stats_entry_accuracy_and_repr():
    entry = WeaponStatsEntry(Weapon("railgun"), 1, 2, 3, 4, 10, 5, 6, 7)
    assert entry.accuracy() == 50
    assert entry.name == "RG"
    assert "RG" in repr(entry)
    assert WeaponStatsEntry(Weapon("railgun"), 0, 0, 0, 0, 0, 0, 0, 0).accuracy() == 0
