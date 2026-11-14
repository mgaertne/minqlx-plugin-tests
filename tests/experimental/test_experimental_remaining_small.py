from types import SimpleNamespace
from unittest.mock import Mock

import minqlx
from experimental import uptime as experimental_uptime


def test_experimental_uptime_sends_two_messages(monkeypatch):
    plugin = experimental_uptime.uptime()
    now = experimental_uptime.datetime.datetime(2025, 1, 1, 12, 0)
    monkeypatch.setattr(
        experimental_uptime.datetime,
        "datetime",
        SimpleNamespace(
            now=lambda: now,
            fromtimestamp=lambda _value: now,
        ),
    )
    monkeypatch.setattr(experimental_uptime.distro, "lsb_release_info", lambda: {"description": "Test OS"})
    monkeypatch.setattr(experimental_uptime.psutil, "boot_time", lambda: 0)
    monkeypatch.setattr(experimental_uptime.psutil, "Process", lambda _pid: SimpleNamespace(create_time=lambda: 0))
    monkeypatch.setattr(experimental_uptime.humanize, "precisedelta", lambda *_args, **_kwargs: "one minute")
    monkeypatch.setattr(experimental_uptime.platform, "python_version", lambda: "3.test")
    plugin.msg = Mock()

    plugin.cmd_uptime(None, [], minqlx.CHAT_CHANNEL)

    assert plugin.msg.call_count == 2
