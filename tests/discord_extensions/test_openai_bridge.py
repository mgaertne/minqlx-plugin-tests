from threading import Lock
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from minqlx_plugin_test import setup_cvars

from discord_extensions.openai_bridge import OpenAIBridge, int_set
from minqlx import Plugin


def test_int_set_handles_missing_empty_and_duplicate_values():
    assert int_set(None) == set()
    assert int_set(["", "12", "12", "34"]) == {12, 34}


def test_init_uses_configured_values_and_removes_empty_triggers():
    setup_cvars(
        {
            "qlx_openai_botname": "Helper",
            "qlx_openai_clanprefix": "[TAG]",
            "qlx_openai_bot_triggers": "hello,,help",
            "qlx_openai_bot_role_chat": "\u0048i",
        }
    )

    bridge = OpenAIBridge(Mock())

    assert bridge.bot_name == "Helper"
    assert bridge.bot_clanprefix == "[TAG]"
    assert bridge.bot_triggers == ["hello", "help"]
    assert bridge.bot_role_chat == "Hi"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id,bot_user_id", [(99, 1), (12, None)])
async def test_on_message_ignores_unconfigured_channel_or_missing_bot_user(channel_id, bot_user_id):
    setup_cvars({"qlx_discordRelayChannelIds": "12"})
    bot = Mock(user=None if bot_user_id is None else SimpleNamespace(id=bot_user_id))
    bridge = OpenAIBridge(bot)
    message = SimpleNamespace(channel=SimpleNamespace(id=channel_id), author=SimpleNamespace(id=2))

    with patch.object(Plugin, "_loaded_plugins", {}):
        await bridge.on_message(message)


@pytest.mark.asyncio
async def test_on_message_ignores_own_messages_and_missing_plugin():
    setup_cvars({"qlx_discordRelayChannelIds": "12"})
    bot = Mock(user=SimpleNamespace(id=1))
    bridge = OpenAIBridge(bot)
    message = SimpleNamespace(channel=SimpleNamespace(id=12), author=SimpleNamespace(id=1))

    with patch.object(Plugin, "_loaded_plugins", {}):
        await bridge.on_message(message)

    message.author.id = 2
    with patch.object(Plugin, "_loaded_plugins", {}):
        await bridge.on_message(message)


@pytest.mark.asyncio
async def test_on_message_records_untriggered_relay_chat():
    setup_cvars({"qlx_discordRelayChannelIds": "12"})
    bot = Mock(user=SimpleNamespace(id=1))
    bridge = OpenAIBridge(bot)
    message = SimpleNamespace(
        channel=SimpleNamespace(id=12, send=AsyncMock()),
        author=SimpleNamespace(id=2, display_name="Player", name="Fallback"),
        content="ordinary chat",
    )
    plugin = SimpleNamespace(
        queue_lock=Lock(),
        is_triggered_message=Mock(return_value=False),
        _record_chat_line=Mock(),
    )

    with patch.object(Plugin, "_loaded_plugins", {"openai_bot": plugin}):
        await bridge.on_message(message)

    plugin._record_chat_line.assert_called_once_with("Player: ordinary chat", lock=plugin.queue_lock)


@pytest.mark.asyncio
async def test_on_message_completes_trigger_and_sends_response():
    setup_cvars({"qlx_discordRelayChannelIds": "12"})
    bot = Mock(user=SimpleNamespace(id=1))
    bridge = OpenAIBridge(bot)
    message = SimpleNamespace(
        channel=SimpleNamespace(id=12, send=AsyncMock()),
        author=SimpleNamespace(id=2, display_name="", name="Player"),
        content="!hello",
    )
    plugin = SimpleNamespace(
        queue_lock=Lock(),
        is_triggered_message=Mock(return_value=True),
        contextualized_chat_history=Mock(return_value=["history"]),
        _record_chat_line=Mock(),
        _completion=AsyncMock(return_value="completion"),
        _pick_choice=Mock(return_value="choice"),
        _cleanup_choice=Mock(return_value="response"),
        _ql_cleaned_up=Mock(return_value="clean response"),
    )

    with patch.object(Plugin, "_loaded_plugins", {"openai_bot": plugin}), patch.object(
        Plugin, "clean_text", side_effect=lambda text: text
    ), patch.object(Plugin, "msg") as send_game_message:
        await bridge.on_message(message)

    plugin.contextualized_chat_history.assert_called_once_with("Player: !hello", trigger_template="")
    plugin._completion.assert_awaited_once_with(["history"])
    assert plugin._record_chat_line.call_count == 2
    send_game_message.assert_called_once_with("^7Bob^7: ^2clean response")
    message.channel.send.assert_awaited_once_with(content="Bob: response")


@pytest.mark.asyncio
async def test_on_message_stops_when_completion_has_no_response():
    setup_cvars({"qlx_discordRelayChannelIds": "12"})
    bridge = OpenAIBridge(Mock(user=SimpleNamespace(id=1)))
    message = SimpleNamespace(
        channel=SimpleNamespace(id=12, send=AsyncMock()),
        author=SimpleNamespace(id=2, display_name="Player", name="Player"),
        content="!hello",
    )
    plugin = SimpleNamespace(
        queue_lock=Lock(),
        is_triggered_message=Mock(return_value=True),
        contextualized_chat_history=Mock(return_value=[]),
        _record_chat_line=Mock(),
        _completion=AsyncMock(return_value=None),
        _pick_choice=Mock(return_value=None),
        _cleanup_choice=Mock(return_value=None),
    )

    with patch.object(Plugin, "_loaded_plugins", {"openai_bot": plugin}):
        await bridge.on_message(message)

    plugin._record_chat_line.assert_called_once()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_adds_cog_to_bot():
    from discord_extensions.openai_bridge import setup

    bot = Mock(add_cog=AsyncMock())

    await setup(bot)

    bot.add_cog.assert_awaited_once()
    assert isinstance(bot.add_cog.await_args.args[0], OpenAIBridge)
