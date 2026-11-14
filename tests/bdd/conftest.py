import pytest

import minqlx


@pytest.fixture(autouse=True)
def _forget_plugin_registrations():
    yield
    minqlx.reset_registrations()
