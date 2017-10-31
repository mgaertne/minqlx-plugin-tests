import minqlx

from mockito import *
from mockito.matchers import *

"""Functions for setting up unit tests for a :class:`minqlx.Plugin` and checking interactions with class methods provided by minqlx.  
"""
def setup_plugin(plugin: minqlx.Plugin):
    """Setup a minqlx.Plugin passed in for unit testing.

    This function will enable spying on certain functions like messages sent to the console through msg,
    and center_prints on the screen.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the next test.**

    :param plugin: The plugin to prepare for unit testing
    :type plugin: minqlx.Plugin

    """
    spy2(plugin.msg)
    when2(plugin.msg, ANY(str)).thenReturn(None)
    spy2(plugin.center_print)
    when2(plugin.center_print, ANY(str)).thenReturn(None)
    spy2(plugin.play_sound)
    when2(plugin.play_sound, ANY(str)).thenReturn(None)
    spy2(plugin.player)

def setup_cvar(plugin, cvar_name, cvar_value, return_type=None):
    """Setup a minqlx.Plugin passed in with the provided cvar and value.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the next test.**

    :param plugin: the plugin to prepare with the cvar
    :param cvar_name: the name of the cvar
    :param cvar_value: the value the plugin should return for the cvar
    :param return_type: the type that the get_cvar call shall be casting to. (Default: None)
    """
    plugin.get_cvar = mock()
    if return_type == None:
        when2(plugin.get_cvar, cvar_name).thenReturn(cvar_value)
        return

    when2(plugin.get_cvar, cvar_name, return_type).thenReturn(cvar_value)


def assert_plugin_sent_to_console(plugin, matcher, times=1):
    """Verify that a certain text was sent to the console by the plugin.

    **The plugin needs to be set up via :func:`.setUp_plugin(plugin)` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the next test.**

    :param plugin: The plugin -- previously set up with :func:`.setUp_plugin(plugin)`-- that should have sent the text to the console.
    :param matcher: A :class:`mockito.matchers` that should match the text sent to the Quake Live console.
    :param times: The amount of times the plugin should have sent a matching message, set to 0 for no matching message having been sent. (default: 1).
    """
    verify(plugin, times=times).msg(matcher)

def assert_plugin_center_printed(plugin, matcher, times=1):
    """Verify that a certain text was printed for each player to see.

    **The plugin needs to be set up via :func:`.setUp_plugin(plugin)` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the next test.**

    :param plugin: The plugin -- previously set up with :func:`.setUp_plugin(plugin)`-- that should have been displayed for all players and spectators.
    :param matcher: A :class:`mockito.matchers` that should match the text printed centric for all players and spectators.
    :param times: The amount of times the plugin should have displayed the matching message, set to 0 for no matching message having been shown. (default: 1).
    """
    verify(plugin, times=times).center_print(matcher)
