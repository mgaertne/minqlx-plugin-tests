from minqlx import Player, Plugin

from mockito import *
from mockito.matchers import *
from mockito.matchers import Matcher

"""Functions for setting up players in the game and verifying interactions with them.
"""

any_team = any(str)


def fake_player(steam_id, name, team="spectator", id=0, score=0, ping=0):
    """A builder for mocked players that assertion can be used to check for certain interactions.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the
    next test.**

    :param steam_id: the steam_id of this fake_player
    :param name: the name of the fake_player
    :param team: the team the player should be on (default "spectator")
    :param ping: the ping that player should have (default: 0)
    :return: a mocked player that might be used to set up the game and interactions can be checked with assertion
    functions afterwards.
    """
    player = mock(spec=Player, strict=False)
    player.id = id
    player.steam_id = steam_id
    player.name = name
    player.clean_name = name
    player.team = team
    player.ping = ping
    player.score = score
    return player


def connected_players(*players):
    """Sets up a plugin with the provided players being connected to the server.

    **Make sure to use :func:`mockito.unstub()` after calling this function to avoid side effects spilling into the
    next test.**

    :param players: the players that are currently on the server, in all possible teams: "red", "blue", "spectator",
    and "free"
    """
    when2(Plugin.players).thenReturn(players)
    for player in players:
        when2(Plugin.player, player.steam_id).thenReturn(player)
        when2(Plugin.player, player).thenReturn(player)


def assert_player_was_put_on(player, matcher, times=1):
    """Assert that the given player was put on the matching team given.

    **The player needs to be set up via :func:`.fake_player(steam_id, name, team, ping)` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param player: the player that should have been put on the matching team
    :param matcher: matches the team the player should have been put on. This might be  :class:`mockito.matchers` to
    check that the player was not put on a different team.
    :param times: The amount of times the player should have been put on the matching team, set to 0 for team switch
    for that player to have happened. (default: 1).
    """
    verify(player, times=times).put(matcher)


def assert_player_was_told(player, matcher, times=1):
    """Verify that a certain text was sent to the console by the player.

    **The player needs to be set up via :func:`.fake_player(steam_id, name, team, ping)` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param player: the player that should have been told the matching message
    :param matcher: matches the text the player should have told. This might be  :class:`mockito.matchers` to check for
    certain types of messages.
    :param times: The amount of times the player should have been told the matching message, set to 0 for no message
    told to the player. (default: 1).
    :return:
    """
    verify(player, times=times).tell(matcher)


def assert_player_received_center_print(player, matcher, times=1):
    """Verify that a certain text was center printed for the player.

    **The player needs to be set up via :func:`.fake_player(steam_id, name, team, ping)` before using this assertion.**

    **Make sure to use :func:`mockito.unstub()` after calling this assertion to avoid side effects spilling into the
    next test.**

    :param player: the player that should have received the matching center print
    :param matcher: matches the text the player should have received. This might be :class:`mockito.matchers` to check
    for certain types of messages.
    :param times: The amount of times the player should have been received the matching message, set to 0 for no message
    center printed to the player. (default: 1).
    :return:
    """
    verify(player, times=times).center_print(matcher)


class PlayerMatcher(Matcher):
    """
    A custom mockito matcher that matches minqlx.Players by their name and steam_id.
    """
    def __init__(self, wanted_player):
        self.wanted_player = wanted_player

    def matches(self, matching_player):
        return self.wanted_player.steam_id == matching_player.steam_id \
            and self.wanted_player.name == matching_player.name

    def __repr__(self):
        return "<Player: id=%s, name=%s>" % (self.wanted_player.steam_id, self.wanted_player.name)


def player_that_matches(player):
    """
    Matches against a given player by their name and steam_id.
    """
    return PlayerMatcher(player)
