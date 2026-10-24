import pytest

from experimental.weird_stats import (
    PlayerStatsEntry,
    Position,
    WeaponStats,
    calculate_distance,
    convert_units_to_meters,
    determine_means_of_death,
    filter_stats_for_max_value,
    format_float,
    format_int,
    formatted_medal_fact,
    longest_shaftlamers_announcement,
    most_accurate_railbitches_announcement,
    most_honorable_haste_pickup_announcement,
    most_weapon_hits_announcement,
    random_medal_facts,
)


def test_weird_stats_format_and_distance_helpers():
    assert calculate_distance(Position(0, 0, 0), Position(3, 4, 0)) == 5
    assert format_float(1234.5) == "1.234,50"
    assert format_int(1234567) == "1.234.567"
    assert convert_units_to_meters(8) == 0.3048
    assert determine_means_of_death("HURT") == "void"
    assert determine_means_of_death("ROCKET") == "rocket"


def test_weird_stats_basic_formatting_helpers():
    assert calculate_distance(Position(0, 0, 0), Position(3, 4, 0)) == 5
    assert format_float(1234.5) == "1.234,50"
    assert format_int(1234567) == "1.234.567"
    assert convert_units_to_meters(8) == pytest.approx(0.3048)
    assert determine_means_of_death("HURT") == "void"
    assert determine_means_of_death("ROCKET") == "rocket"


def test_weapon_stats_properties_and_filtering():
    weapon = WeaponStats("RAILGUN", 1, 2, 3, 5, 4, 6, 10, 20)
    assert weapon.accuracy == 50
    assert weapon.shortname == "rg"
    assert filter_stats_for_max_value([1, 2, 2], lambda value: value) == [2, 2]
    assert filter_stats_for_max_value([], lambda value: value) == []


def test_player_stats_entry_sums_entries_and_combines_matching_rounds():
    first = {
        "TYPE": "PLAYER_STATS",
        "DATA": {
            "STEAM_ID": "123",
            "NAME": "Player",
            "MATCH_GUID": "match",
            "WARMUP": False,
            "KILLS": 2,
            "DAMAGE": {"DEALT": 10, "TAKEN": 4},
            "WEAPONS": {"RAILGUN": {"D": 1, "DG": 10, "DR": 4, "H": 5, "K": 2, "P": 1, "S": 10, "T": 20}},
        },
    }
    second = {
        "TYPE": "PLAYER_STATS",
        "DATA": {"STEAM_ID": "123", "NAME": "Player", "MATCH_GUID": "match", "WARMUP": False, "KILLS": 3},
    }
    stats = PlayerStatsEntry(first)
    stats.combine(PlayerStatsEntry(second))
    assert stats.kills == 5
    assert stats.damage.dealt == 10
    assert stats.weapons.railgun.accuracy == 50
    assert stats.name == "Player"


def test_player_stats_rejects_invalid_combinations():
    stats = PlayerStatsEntry({"TYPE": "PLAYER_STATS", "DATA": {"STEAM_ID": "1", "MATCH_GUID": "a", "WARMUP": False}})
    with pytest.raises(ValueError):
        PlayerStatsEntry({"TYPE": "OTHER", "DATA": {}})
    with pytest.raises(ValueError):
        stats.combine(
            PlayerStatsEntry({"TYPE": "PLAYER_STATS", "DATA": {"STEAM_ID": "2", "MATCH_GUID": "a", "WARMUP": False}})
        )


def test_railgun_announcement_handles_empty_and_positive_stats():
    empty = PlayerStatsEntry({"TYPE": "PLAYER_STATS", "DATA": {"STEAM_ID": "1", "NAME": "Empty"}})
    assert most_accurate_railbitches_announcement([empty]) is None
    positive = PlayerStatsEntry(
        {"TYPE": "PLAYER_STATS", "DATA": {"STEAM_ID": "1", "NAME": "Railer", "WEAPONS": {"RAILGUN": {"H": 5, "S": 10}}}}
    )
    assert "Railer" in most_accurate_railbitches_announcement([positive])


def test_weird_stats_announcements_cover_medals_and_weapon_facts():
    stats = PlayerStatsEntry(
        {
            "TYPE": "PLAYER_STATS",
            "DATA": {
                "STEAM_ID": "1",
                "NAME": "Player",
                "MEDALS": {"IMPRESSIVE": 2},
                "PICKUPS": {"HASTE": 3},
                "WEAPONS": {"LIGHTNING": {"D": 0, "DG": 0, "DR": 0, "H": 5, "K": 0, "P": 0, "S": 10, "T": 8}},
            },
        }
    )

    assert "impressive" in formatted_medal_fact([stats], "impressive")
    assert "Haste" in most_honorable_haste_pickup_announcement([stats])
    assert "Shaftlamer" in longest_shaftlamers_announcement([stats])
    assert most_weapon_hits_announcement([stats]) is not None
    assert random_medal_facts([stats], count=1)
