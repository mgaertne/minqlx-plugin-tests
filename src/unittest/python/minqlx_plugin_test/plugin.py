from minqlx import Plugin

from mockito import *
from mockito.matchers import *

"""Functions for setting up unit tests for a :class:`minqlx.Plugin` and checking interactions with class methods
provided by minqlx.
"""


def setup_plugin():
    """Setup a minqlx.Plugin for unit testing.

    This function will enable spying on certain functions like messages sent to the console through msg,
    and center_prints on the screen.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the
    next test.**
    """
    spy2(Plugin.msg)
    when2(Plugin.msg, any(str)).thenReturn(None)
    spy2(Plugin.center_print)
    when2(Plugin.center_print, any(str)).thenReturn(None)
    spy2(Plugin.play_sound)
    when2(Plugin.play_sound, any(str)).thenReturn(None)
    spy2(Plugin.players)
    when2(Plugin.players).thenReturn(None)
    spy2(Plugin.player)
    when2(Plugin.player, any()).thenReturn(None)


def setup_cvar(cvar_name, cvar_value, return_type=None):
    """Setup a minqlx.Plugin with the provided cvar and value.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the
    next test.**

    :param cvar_name: the name of the cvar
    :param cvar_value: the value the plugin should return for the cvar
    :param return_type: the type that the get_cvar call shall be casting to. (Default: None)
    """
    spy2(Plugin.get_cvar)
    if return_type is None:
        when2(Plugin.get_cvar, cvar_name).thenReturn(cvar_value)
        return

    when2(Plugin.get_cvar, cvar_name, return_type).thenReturn(cvar_value)


def assert_plugin_sent_to_console(matcher, times=1):
    """Verify that a certain text was sent to the console.

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param matcher: A :class:`mockito.matchers` that should match the text sent to the Quake Live console.
    :param times: The amount of times the plugin should have sent a matching message, set to 0 for no matching message
    having been sent. (default: 1).
    """
    verify(Plugin, times=times).msg(matcher)


def assert_plugin_center_printed(matcher, times=1):
    """Verify that a certain text was printed for each player to see.

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param matcher: A :class:`mockito.matchers` that should match the text printed centric for all players and
    spectators.
    :param times: The amount of times the plugin should have displayed the matching message, set to 0 for no matching
    message having been shown. (default: 1).
    """
    verify(Plugin, times=times).center_print(matcher)
