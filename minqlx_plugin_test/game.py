import minqlx
from minqlx import NonexistentGameError

from mockito import *

def setup_no_game():
    when2(minqlx.Game).thenRaise(NonexistentGameError("Tried to instantiate a game while no game is active."))

def setup_game_in_warmup():
    mock_game = mock(spec=minqlx.Game, strict=False)
    when2(minqlx.Game).thenReturn(mock_game)
    mock_game.state = "warmup"

def setup_game_in_progress(game_type="ca", roundlimit=8, red_score=0, blue_score=0):
    mock_game = mock(spec=minqlx.Game, strict=False)
    when2(minqlx.Game).thenReturn(mock_game)
    mock_game.state = "in_progress"
    mock_game.type_short = game_type
    mock_game.roundlimit = roundlimit
    mock_game.red_score = red_score
    mock_game.blue_score = blue_score

