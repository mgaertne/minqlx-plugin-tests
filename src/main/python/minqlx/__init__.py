import minqlx._minqlx
__version__ = _minqlx.__version__

# Put everything into a single module.
from minqlx._minqlx import *
from ._core import *
from ._plugin import *
from ._game import *
from ._events import *
from ._commands import *
from ._handlers import *
from ._player import *
from ._zmq import *
