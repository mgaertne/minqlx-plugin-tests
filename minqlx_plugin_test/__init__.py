from .plugin import *
from .game import *
from .player import *

"""minqlx_plugin_test provides functions for unit testing plugin behavior for :class:`minqlx.Plugin`s.

This module provides serveral functions for setting up a currently game, preparing a plugin for tests with mocked objects, and interactions with players being simulated to be connected to the server.
"""
__all__ = ['setUp_plugin', 'setup_no_game', 'setup_game_in_warmup', 'setup_game_in_progress',
           'assert_plugin_sent_to_console', 'assert_plugin_center_printed',
           'fake_player', 'connected_players', 'assert_player_was_put_on', 'any_team', 'assert_player_was_told']

__version__ = "0.0.1"
__author__ = "Markus Gärtner"
__copyright__ = "Copyright 2017"
__license__ = "BSD, see License.txt"
