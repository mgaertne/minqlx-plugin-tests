from .database import use_database
from .event_data import (
    death_data,
    game_end_data,
    game_start_data,
    kill_data,
    player_stats_stats,
    round_end_data,
    stats_data,
)
from .fake_runtime import fake_runtime
from .game import (
    assert_game_addteamscore,
    editable_game,
    setup_game_in_progress,
    setup_game_in_warmup,
    setup_no_game,
)
from .matchers import negated
from .player import (
    any_team,
    assert_player_received_center_print,
    assert_player_was_put_on,
    assert_player_was_told,
    connected_players,
    fake_player,
    player_that_matches,
)
from .plugin import (
    assert_channel_was_replied,
    assert_cvar_was_set_to,
    assert_players_switched,
    assert_plugin_center_printed,
    assert_plugin_played_sound,
    assert_plugin_sent_to_console,
    mocked_channel,
    register_decorated_handlers,
    setup_cvar,
    setup_cvars,
    setup_plugin,
)
from .stand_in import stand_in

# minqlx_plugin_test provides functions for unit testing plugin behavior for :class:`minqlx.Plugin`s.
#
# This module provides several functions for setting up a currently game, preparing a plugin for tests with mocked
# objects, and interactions with players being simulated to be connected to the server.
__all__ = [
    "any_team",
    "assert_channel_was_replied",
    "assert_cvar_was_set_to",
    "assert_game_addteamscore",
    "assert_player_received_center_print",
    "assert_player_was_put_on",
    "assert_player_was_told",
    "assert_players_switched",
    "assert_plugin_center_printed",
    "assert_plugin_played_sound",
    "assert_plugin_sent_to_console",
    "connected_players",
    "death_data",
    "editable_game",
    "fake_player",
    "fake_runtime",
    "game_end_data",
    "game_start_data",
    "kill_data",
    "mocked_channel",
    "negated",
    "player_stats_stats",
    "player_that_matches",
    "register_decorated_handlers",
    "round_end_data",
    "setup_cvar",
    "setup_cvars",
    "setup_game_in_progress",
    "setup_game_in_warmup",
    "setup_no_game",
    "setup_plugin",
    "stand_in",
    "stats_data",
    "use_database",
]

__file__ = "__init__"

__version__ = "0.0.1"
__author__ = "Markus Gaertner"
__copyright__ = "Copyright 2017"
__license__ = "BSD, see License"
