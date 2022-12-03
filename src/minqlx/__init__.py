from typing import Tuple

import re as _re
import importlib

try:
    _minqlx = importlib.import_module(name="_minqlx")
    from _minqlx import *  # type: ignore
except ModuleNotFoundError:
    _minqlx = importlib.import_module(name="._minqlx", package="minqlx")
    from ._minqlx import *  # pylint: disable=unused-wildcard-import, wrong-import-position

__version__ = _minqlx.__version__
__plugins_version__ = "NOT_SET"

_map_title = ""
_map_subtitle1 = ""
_map_subtitle2 = ""

temp = _re.search(r"(\d+)\.(\d+)\.(\d+)", __version__)
__version_info__: Tuple[int, int, int]
if temp is None:
    __version_info__ = (999, 999, 999)
else:
    # noinspection PyBroadException
    try:
        __version_info__ = int(temp.group(1)), int(temp.group(2)), int(temp.group(3))
    except:  # pylint: disable=bare-except
        __version_info__ = (999, 999, 999)
del temp

# Put everything into a single module.
from ._core import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._plugin import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._game import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._events import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._commands import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._handlers import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._player import *  # pylint: disable=unused-wildcard-import, wrong-import-position
from ._zmq import *  # pylint: disable=unused-wildcard-import, wrong-import-position
