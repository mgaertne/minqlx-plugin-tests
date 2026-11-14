from ._stubbed import build

_classes = {}
build("_player", _classes)

NonexistentPlayerError = _classes["NonexistentPlayerError"]
Player = _classes["Player"]
AbstractDummyPlayer = _classes["AbstractDummyPlayer"]
RconDummyPlayer = _classes["RconDummyPlayer"]


def _player_init(self, client_id, info=None):
    self._id = client_id
    self._info = info
    self._valid = True
    self._name = "" if info is None else info.name


def _dummy_init(self, name="DummyPlayer"):
    Player.__init__(self, -1)
    self._name = name


Player.__init__ = _player_init
Player.__str__ = lambda self: self._name
Player.id = property(lambda self: self._id)
Player.name = property(lambda self: self._name)
AbstractDummyPlayer.__init__ = _dummy_init
