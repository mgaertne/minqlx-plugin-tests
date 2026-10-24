from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import discord_extensions.uptime as uptime_extension
from minqlx import Plugin


@pytest.mark.asyncio
async def test_uptime_sends_embed_with_system_and_server_uptimes(monkeypatch):
    now = datetime(2025, 1, 1, 12, 0, 0)

    class FixedDateTime:
        @staticmethod
        def now():
            return now

        @staticmethod
        def fromtimestamp(timestamp):
            return now - timedelta(seconds=timestamp)

    process = Mock(create_time=Mock(return_value=1800))
    monkeypatch.setattr(uptime_extension.datetime, "datetime", FixedDateTime)
    monkeypatch.setattr(uptime_extension.distro, "lsb_release_info", lambda: {"description": "Test OS"})
    monkeypatch.setattr(uptime_extension.psutil, "boot_time", lambda: 3600)
    monkeypatch.setattr(uptime_extension.psutil, "Process", lambda _pid: process)
    monkeypatch.setattr(uptime_extension.os, "getpid", lambda: 42)
    monkeypatch.setattr(uptime_extension.platform, "python_version", lambda: "3.test")
    monkeypatch.setattr(uptime_extension.humanize, "precisedelta", lambda delta, **_kwargs: str(delta))
    monkeypatch.setattr(Plugin, "get_cvar", lambda _name: "Test Server")
    interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))

    await uptime_extension._uptime(interaction)

    interaction.response.send_message.assert_awaited_once()
    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "Test Server"
    assert "Test OS" in embed.description
    assert "Python 3.test" in embed.description
    assert interaction.response.send_message.await_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_context_menu_calls_uptime(monkeypatch):
    send_uptime = AsyncMock()
    monkeypatch.setattr(uptime_extension, "_uptime", send_uptime)
    interaction = Mock()

    await uptime_extension.uptime.callback(interaction, Mock())

    send_uptime.assert_awaited_once_with(interaction)


@pytest.mark.asyncio
async def test_setup_registers_context_menu():
    bot = SimpleNamespace(tree=SimpleNamespace(add_command=Mock()))

    await uptime_extension.setup(bot)

    bot.tree.add_command.assert_called_once_with(uptime_extension.uptime)
