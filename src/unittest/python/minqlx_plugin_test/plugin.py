from mockito import mock, when, any, verify

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
    spy2(Plugin.switch)
    when2(Plugin.switch, any, any).thenReturn(None)
    spy2(Plugin.set_cvar)
    when2(Plugin.set_cvar, any, any).thenReturn(None)
    spy2(Plugin.kick)
    when2(Plugin.kick, any, any(str)).thenReturn(None)


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


def setup_cvars(cvars):
    """Setup a minqlx.Plugin with the provided cvars and values.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the
    next test.**

    :param cvars: a dictionary containing the cvar names as keys, and a tuple of values and types
    """
    spy2(Plugin.get_cvar)
    for name, (value, value_type) in cvars.items():
        if value_type is None:
            when2(Plugin.get_cvar, name).thenReturn(value)
        else:
            when2(Plugin.get_cvar, name, value_type).thenReturn(value)


def assert_plugin_sent_to_console(matcher, times=1, atleast=None):
    """Verify that a certain text was sent to the console.

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param matcher: A :class:`mockito.matchers` that should match the text sent to the Quake Live console.
    :param times: The amount of times the plugin should have sent a matching message, set to 0 for no matching message
    having been sent. (default: 1).
    :param atleast: The minimum amount of times the plugin should have sent a matching message (default: None)
    """
    verify(Plugin, times=times, atleast=atleast).msg(matcher)


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


def assert_plugin_played_sound(matcher, times=1):
    """Verify that a certain sound was played for all players.

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param matcher: A :class:`mockito.matchers` that should match the sound file player for all players and
    spectators.
    :param times: The amount of times the plugin should have played the matching sound, set to 0 for no matching
    sound to have been played. (default: 1).
    """
    verify(Plugin, times=times).play_sound(matcher)


def assert_players_switched(player1, player2, times=1):
    """Verify that two players were switched with each other.

    This function differs from :func:`.assert_player_was_put_on` in that the two players were switched with each other
    directly via the according minqlx.Plugin function rather than minqlx.Player.put().

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param player1: A :class:`mockito.matchers` that should match one player that was switched
    :param player2: A :class:`mockito.matchers` that should match the other player that was switched
    :param times: The amount of times the plugin should have played the matching sound, set to 0 for no matching
    sound to have been played. (default: 1).
    """
    verify(Plugin, times=times).switch(player1, player2)


def assert_cvar_was_set_to(cvar_name, cvar_value, times=1):
    """Verify that the plugin set a cvar to certain value

    **The test needs to be set up via :func:`.setUp_plugin()` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param cvar_name: the name of the cvar
    :param cvar_value: the value the plugin should have set the cvar to
    :param times: The amount of times the plugin should have set the cvar. (default: 1).
    """
    verify(Plugin, times=times).set_cvar(cvar_name, cvar_value)


def mocked_channel():
    channel = mock()
    when(channel).reply(any).thenReturn(None)
    return channel


def assert_channel_was_replied(channel, matcher, times=1):
    verify(channel, times=times).reply(matcher)