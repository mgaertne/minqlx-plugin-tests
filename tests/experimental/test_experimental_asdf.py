from types import SimpleNamespace
from unittest.mock import Mock

import minqlx
from experimental.asdf import Weapon, WeaponStatsEntry, asdf, identify_reply_channel


def test_weapon_maps_names_to_ammo_types():
    assert Weapon("MACHINEGUN").ammo_type() == "mg"
    assert Weapon("rocket").weapon_name() == "RL"
    assert Weapon("unknown").ammo_type() == "other"


def test_weapon_stats_entry_accuracy_and_repr():
    entry = WeaponStatsEntry(Weapon("ROCKET"), 2, 3, 40, 20, 10, 5, 1, 30)

    assert entry.accuracy() == 50
    assert "RL: K:2" in repr(entry)
    assert WeaponStatsEntry(Weapon("ROCKET"), 0, 0, 0, 0, 0, 0, 0, 0).accuracy() == 0


def test_asdf_calculates_damage_deltas_and_team_totals():
    plugin = asdf()
    red = SimpleNamespace(steam_id=1, stats=SimpleNamespace(damage_dealt=30))
    plugin.stats_snapshot = {1: 10, 2: 5}
    plugin.player = lambda steam_id: red if steam_id == 1 else None
    plugin.teams = lambda: {"red": [red], "blue": []}

    assert plugin.calculate_damage_deltas() == {1: 20}
    plugin.calculate_team_round_damages()
    assert plugin.red_overall_damage == 20
    assert plugin.blue_overall_damage == 0


def test_identify_reply_channel_maps_team_channels():
    assert identify_reply_channel(minqlx.RED_TEAM_CHAT_CHANNEL) == minqlx.CHAT_CHANNEL
    channel = Mock()
    assert identify_reply_channel(channel) is channel
