from ._stubbed import build

_classes = {}
build("_game", _classes)

NonexistentGameError = _classes["NonexistentGameError"]
Game = _classes["Game"]
