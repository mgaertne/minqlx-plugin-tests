from types import SimpleNamespace
from typing import List
from unittest.mock import Mock

import pytest

import minqlx
from experimental.admin_votes import admin_votes
from experimental.cmdlist import cmdlist


@pytest.mark.parametrize("vote_yes_no,configstring", [(True, 10), (False, 11)])
def test_admin_vote_counts_a_privileged_vote_once(monkeypatch, vote_yes_no, configstring):
    plugin = admin_votes()
    plugin.is_vote_active = lambda: True
    plugin.get_cvar = lambda _name, _kind: True
    player = SimpleNamespace(privileges="admin", steam_id=123, team="red", tell=Mock())
    writes = []
    monkeypatch.setattr(minqlx, "get_configstring", lambda index: "2" if index == configstring else "0")
    monkeypatch.setattr(minqlx, "set_configstring", lambda index, value: writes.append((index, value)))

    result = plugin.process_vote(player, vote_yes_no)

    assert result == minqlx.RET_STOP_ALL
    assert writes == [(configstring, "3")]
    assert plugin.mods_admins_voted == [123]


def test_admin_vote_ignores_inactive_votes_and_non_admins():
    plugin = admin_votes()
    player = SimpleNamespace(privileges="player", steam_id=123, team="red", tell=Mock())
    plugin.is_vote_active = lambda: False

    assert plugin.process_vote(player, True) == minqlx.RET_NONE

    plugin.is_vote_active = lambda: True
    assert plugin.process_vote(player, True) == minqlx.RET_NONE


def test_admin_vote_rejects_duplicate_and_disallowed_spectator_votes():
    plugin = admin_votes()
    plugin.is_vote_active = lambda: True
    player = SimpleNamespace(privileges="mod", steam_id=123, team="spectator", tell=Mock())
    plugin.mods_admins_voted = [123]

    assert plugin.process_vote(player, True) == minqlx.RET_STOP_ALL
    player.tell.assert_called_once_with("Vote already cast.")

    player.tell.reset_mock()
    plugin.mods_admins_voted = []
    plugin.get_cvar = lambda _name, _kind: False
    assert plugin.process_vote(player, True) == minqlx.RET_STOP_ALL
    player.tell.assert_not_called()
    assert plugin.mods_admins_voted == []


def test_admin_vote_started_clears_previous_voters():
    plugin = admin_votes()
    plugin.mods_admins_voted = [123]

    plugin.handle_vote_started(None, "map", "campgrounds")

    assert plugin.mods_admins_voted == []


def test_cmdlist_formats_commands_by_permission_and_splits_long_output(monkeypatch):
    plugin = cmdlist()
    sent: List[str] = []
    player = SimpleNamespace(tell=sent.append)
    commands = [
        SimpleNamespace(is_eligible_player=lambda _player, _check: True, name="help", usage=None, permission=0),
        SimpleNamespace(
            is_eligible_player=lambda _player, _check: True,
            name=("map", "m"),
            usage="<name>",
            permission=1,
        ),
        SimpleNamespace(is_eligible_player=lambda _player, _check: False, name="hidden", usage=None, permission=2),
    ]
    monkeypatch.setattr(minqlx, "COMMANDS", SimpleNamespace(commands=commands), raising=False)
    monkeypatch.setattr(minqlx, "CHAT_CHANNEL", SimpleNamespace(split_long_lines=lambda text, delimiter: [text]))
    monkeypatch.setattr("experimental.cmdlist.time.sleep", lambda _duration: None)

    plugin.thread_reply(player)

    assert sent == [
        "^1Permission level 0^7 commands:",
        "^1  help",
        "^2Permission level 1^7 commands:",
        "^2  map <name>^7, ^2m <name>",
    ]


def test_cmdlist_formats_scalar_usage_and_aliases_without_usage(monkeypatch):
    plugin = cmdlist()
    sent: List[str] = []
    player = SimpleNamespace(tell=sent.append)
    commands = [
        SimpleNamespace(is_eligible_player=lambda _player, _check: True, name="players", usage="[TEAM]", permission=3),
        SimpleNamespace(is_eligible_player=lambda _player, _check: True, name=("ready", "r"), usage=None, permission=3),
    ]
    monkeypatch.setattr(minqlx, "COMMANDS", SimpleNamespace(commands=commands), raising=False)
    monkeypatch.setattr(minqlx, "CHAT_CHANNEL", SimpleNamespace(split_long_lines=lambda text, delimiter: [text]))
    monkeypatch.setattr("experimental.cmdlist.time.sleep", lambda _duration: None)

    plugin.thread_reply(player)

    assert sent == [
        "^4Permission level 3^7 commands:",
        "^4  players [TEAM]^7, ^4ready^7, ^4r",
    ]


def test_cmdlist_command_starts_reply_thread():
    plugin = cmdlist()
    player = SimpleNamespace()
    plugin.thread_reply = Mock()

    plugin.cmd_cmdlist(player, ["!cmdlist"], None)

    plugin.thread_reply.assert_called_once_with(player)
