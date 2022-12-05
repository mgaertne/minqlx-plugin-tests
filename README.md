# minqlx-plugin-tests
![python](https://img.shields.io/badge/python-3.8%7C3.9%7C3.10%7C3.11-blue.svg)
![Tests](https://github.com/mgaertne/minqlx-plugin-tests/actions/workflows/test.yml/badge.svg)
[![codecov](https://codecov.io/gh/mgaertne/minqlx-plugin-tests/branch/master/graph/badge.svg?token=4Lfg3k3LJ0)](https://codecov.io/gh/mgaertne/minqlx-plugin-tests)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Test support functions for unit testing [minqlx-plugins](https://github.com/MinoMino/minqlx-plugins).

[minqlx](https://github.com/MinoMino/minqlx) functions will be mocked out, so you should know the interface that minqlx provides for Quake Live plugins, and you should test the final plugin on the server to avoid integration problems with a real server running.

Use [tox](https://tox.wiki/) to build and run all unit tests.
