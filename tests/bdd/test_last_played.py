from datetime import datetime, timedelta, timezone

import pytest
import redis
from minqlx_plugin_test import setup_cvars
from mockito import any_, mock, when
from pytest_bdd import given, parsers, scenarios

from last_played import TIMESTAMP_FORMAT, last_played

scenarios("features/last_played.feature")


def _ago(amount, unit):
    return (datetime.now(timezone.utc) - timedelta(**{unit: amount})).strftime(TIMESTAMP_FORMAT)


@pytest.fixture(name="db")
def _db():
    db = mock(spec=redis.StrictRedis)
    when(db).exists(any_).thenReturn(False)
    return db


@given("the last_played plugin is loaded", target_fixture="plugin")
def _plugin_loaded(db):
    setup_cvars({"qlx_commandPrefix": "!"})
    plugin = last_played()
    plugin._db_instance = db
    return plugin


@given(parsers.parse('the map "{mapname}" was last played {amount:d} {unit} ago'))
def _map_was_played(db, mapname, amount, unit):
    key = f"minqlx:maps:{mapname}:last_played"
    when(db).exists(key).thenReturn(True)
    when(db).get(key).thenReturn(_ago(amount, unit))


@given(parsers.parse('Alice played "{mapname}" {amount:d} {unit} ago'))
def _alice_played(db, players, mapname, amount, unit):
    key = f"minqlx:players:{players['Alice'].steam_id}:last_played"
    when(db).exists(key).thenReturn(True)
    when(db).hget(key, mapname).thenReturn(_ago(amount, unit))
