from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from minqlx import (
        DeathData,
        GameEndData,
        GameStartData,
        KillData,
        PlayerStatsStats,
        RoundEndData,
        StatsData,
    )

# Event data with just the keys the code under test reads, typed as the TypedDicts of the minqlx stubs. These names
# exist for type checkers only, so the helpers are the place that refers to them.


def game_start_data(**items: Any) -> "GameStartData":
    return cast("GameStartData", items)


def game_end_data(**items: Any) -> "GameEndData":
    return cast("GameEndData", items)


def round_end_data(**items: Any) -> "RoundEndData":
    return cast("RoundEndData", items)


def kill_data(**items: Any) -> "KillData":
    return cast("KillData", items)


def death_data(**items: Any) -> "DeathData":
    return cast("DeathData", items)


def stats_data(stats_type: str, data: dict) -> "StatsData":
    return cast("StatsData", {"TYPE": stats_type, "DATA": data})


def player_stats_stats(stats_type: str = "PLAYER_STATS", **data: Any) -> "PlayerStatsStats":
    return cast("PlayerStatsStats", {"TYPE": stats_type, "DATA": data})
