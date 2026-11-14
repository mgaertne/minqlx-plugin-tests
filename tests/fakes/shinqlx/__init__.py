"""shinqlx view of the fake: everything of the minqlx fake plus the shinqlx-only decorators."""

# ruff: noqa: F401, F403
from minqlx import *

from ._decorators import command, game, hook, register_decorated_handlers
