#!/usr/bin/env python
#

#   -*- coding: utf-8 -*-

from pybuilder.core import init, use_plugin, Author

use_plugin("python.core")
use_plugin("python.install_dependencies")

use_plugin("python.unittest")
use_plugin("python.coverage")

use_plugin("python.pylint")
use_plugin("python.flake8")

use_plugin("python.pycharm")

default_task = ["install_dependencies", "analyze", "run_unit_tests", "coverage"]

version = "0.0.1"
authors = (Author("Markus 'ShiN0' Gaertner"),)
url = "https://github.com/mgaertne/minqlx-plugin-tests"

requires_python = ">2.7,>3.8"


@init
def initialize(project):
    project.build_depends_on_requirements('requirements.txt')

    project.set_property("coverage_break_build", False)
    project.set_property("coverage_exceptions",
                         ["minqlx._commands", "minqlx._core", "minqlx._events", "minqlx._game", "minqlx._handlers",
                          "minqlx._minqlx", "minqlx._player", "minqlx._plugin", "minqlx._zmq", "minqlx.database"])

    project.set_property("pylint_options", ["--rcfile=./.pylintrc"])

    project.set_property("flake8_include_test_sources", True)
    project.set_property("flake8_ignore", "E226,E402,E722,F401,F403,F405,W504")
    project.set_property("flake8_max_line_length", "120")
