# minqlx-plugin-tests
![Tests](https://github.com/mgaertne/minqlx-plugin-tests/actions/workflows/tests.yml/badge.svg)

Test support functions for unit testing [minqlx-plugins](https://github.com/MinoMino/minqlx-plugins).

[minqlx](https://github.com/MinoMino/minqlx) functions will be mocked out, so you should know the interface that minqlx provides for Quake Live plugins, and you should test the final plugin on the server to avoid integration problems with a real server running.

Use [pyb](http://pybuilder.github.io/) to build and run all unit tests.
