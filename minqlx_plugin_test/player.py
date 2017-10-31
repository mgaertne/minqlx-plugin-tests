import minqlx

from mockito import *
from mockito.matchers import *

def fake_player(steam_id, name, team="spectator", ping=0):
    player = mock(spec=minqlx.Player, strict=False)
    player.steam_id = steam_id
    player.name = name
    player.team = team
    player.ping = ping
    return player

def connected_players(plugin, *players):
    patch(plugin.players, lambda: players)
    for player in players:
        when2(plugin.player, player.steam_id).thenReturn(player)

def assert_player_was_put_on(player, matcher, times=1):
    verify(player, times=times).put(matcher)

any_team = any(str)

def assert_player_was_told(player, matcher, times=1):
    verify(player, times=times).tell(matcher)