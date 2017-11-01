from pybuilder.core import init, use_plugin

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.install_dependencies")

use_plugin("python.pycharm")

default_task = "publish"

@init
def initialize(project):
    project.build_depends_on('mockito')
    project.build_depends_on('PyHamcrest')

    project.set_property("coverage_threshold_warn", 0)
    project.set_property("coverage_exceptions",
                         ["minqlx.__init__", "minqlx._commands", "minqlx._core", "minqlx._events", "minqlx._game",
                          "minqlx._handlers", "minqlx._minqlx", "minqlx._player", "minqlx._plugin", "minqlx._zmq",
                          "minqlx.database"])
