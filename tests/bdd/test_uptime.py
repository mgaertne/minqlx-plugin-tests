import datetime

from minqlx_plugin_test import setup_cvars
from pytest_bdd import given, parsers, scenarios

import minqlx
from uptime import uptime

scenarios("features/uptime.feature")

NOON = datetime.datetime(2025, 6, 15, 12, 0)
UNITS = {"minute": "minutes", "hour": "hours", "day": "days"}


class NoonDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOON


@given("it is noon on the 15th of June 2025")
def _it_is_noon(monkeypatch):
    monkeypatch.setattr("uptime.datetime.datetime", NoonDatetime)


@given("the uptime plugin is loaded", target_fixture="plugin")
def _plugin_loaded():
    setup_cvars({"qlx_commandPrefix": "!"})
    return uptime()


@given(parsers.parse('the machine runs "{description}" with Python {python_version}'))
def _machine_runs(monkeypatch, description, python_version):
    monkeypatch.setattr("uptime.distro.lsb_release_info", lambda: {"description": description})
    monkeypatch.setattr("uptime.platform.python_version", lambda: python_version)


def _ago(amounts):
    parts = amounts.replace(" and ", " ").split()
    pairs = zip(parts[::2], parts[1::2])
    return datetime.timedelta(**{UNITS[unit.rstrip("s")]: int(number) for number, unit in pairs})


@given(parsers.parse("the machine booted {amounts} ago"))
def _machine_booted(monkeypatch, amounts):
    boot_time = (NOON - _ago(amounts)).timestamp()
    monkeypatch.setattr("uptime.psutil.boot_time", lambda: boot_time)


@given(parsers.parse("the Quake Live server started {amounts} ago"))
def _server_started(monkeypatch, amounts):
    create_time = (NOON - _ago(amounts)).timestamp()
    monkeypatch.setattr(
        "uptime.psutil.Process", lambda _pid: type("Process", (), {"create_time": lambda _self: create_time})()
    )


@given(parsers.parse('the server runs minqlx "{version}"'))
def _server_runs_minqlx(monkeypatch, version):
    monkeypatch.setattr(minqlx, "__version__", version)
