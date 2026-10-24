from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from minqlx_plugin_test import fake_player
from mockito import unstub, when

import minqlx
from experimental.custom_votes import custom_votes


class TestCustomVotes:
    def teardown_method(self):
        unstub()

    @pytest.mark.usefixtures("game_in_progress")
    def test_thrufloors_on_calls_vote_and_accepts_it(self, monkeypatch):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        when(minqlx.Plugin).is_vote_active().thenReturn(False)
        callvote = Mock()
        client_command = Mock()
        monkeypatch.setattr(minqlx, "callvote", callvote)
        monkeypatch.setattr(minqlx, "client_command", client_command)

        result = plugin.handle_vote_called(caller, "THRUFLOORS", "on")

        assert result == minqlx.RET_STOP_ALL
        callvote.assert_called_once_with("g_forceDmgThroughSurface 1", "Turn on damage through floors?")
        client_command.assert_called_once_with(caller.id, "vote yes")

    @pytest.mark.usefixtures("game_in_progress")
    def test_thrufloors_invalid_args_explain_usage(self):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        when(minqlx.Plugin).is_vote_active().thenReturn(False)

        result = plugin.handle_vote_called(caller, "thrufloors", "maybe")

        assert result == minqlx.RET_STOP_ALL

    @pytest.mark.usefixtures("game_in_warmup")
    def test_allready_starts_vote_during_warmup(self, monkeypatch):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        when(minqlx.Plugin).is_vote_active().thenReturn(False)
        callvote = Mock()
        monkeypatch.setattr(minqlx, "callvote", callvote)
        monkeypatch.setattr(minqlx, "client_command", Mock())

        result = plugin.handle_vote_called(caller, "allready", "")

        assert result == minqlx.RET_STOP_ALL
        callvote.assert_called_once_with("qlx !allready", "Ready all players?")

    def test_unknown_vote_is_ignored(self):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        when(minqlx.Plugin).is_vote_active().thenReturn(False)

        assert plugin.handle_vote_called(caller, "unknown", "") == minqlx.RET_NONE

    @pytest.mark.usefixtures("game_in_progress")
    def test_spec_vote_puts_target_in_spectators(self, monkeypatch):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        target = SimpleNamespace(id=456, name="Target", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        plugin.find_target_player_or_list_alternatives = lambda _caller, _target: target
        when(minqlx.Plugin).is_vote_active().thenReturn(False)
        callvote = Mock()
        monkeypatch.setattr(minqlx, "callvote", callvote)
        monkeypatch.setattr(minqlx, "client_command", Mock())

        assert plugin.handle_vote_called(caller, "spec", "Target") == minqlx.RET_STOP_ALL
        callvote.assert_called_once_with("put 456 spec", "spec Target^7?")

    @pytest.mark.usefixtures("game_in_progress")
    def test_mute_vote_calls_silence_command(self, monkeypatch):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        target = SimpleNamespace(id=456, name="Target", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        plugin.find_target_player_or_list_alternatives = lambda _caller, _target: target
        when(minqlx.Plugin).is_vote_active().thenReturn(False)
        callvote = Mock()
        monkeypatch.setattr(minqlx, "callvote", callvote)
        monkeypatch.setattr(minqlx, "client_command", Mock())

        assert plugin.handle_vote_called(caller, "mute", "Target") == minqlx.RET_STOP_ALL
        assert callvote.call_count == 1

    @pytest.mark.usefixtures("game_in_progress")
    def test_allready_rejects_active_match(self):
        plugin = custom_votes()
        caller = fake_player(123, "Caller", team="red")
        plugin.get_cvar = lambda _name, _kind: True
        when(minqlx.Plugin).is_vote_active().thenReturn(False)

        assert plugin.handle_vote_called(caller, "allready", "") == minqlx.RET_STOP_ALL
