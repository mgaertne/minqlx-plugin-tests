from ._stubbed import build

_classes = {}
build("database", _classes)

AbstractDatabase = _classes["AbstractDatabase"]
Redis = _classes["Redis"]

Redis.__getattr__ = lambda self, attr: getattr(self.r, attr)
