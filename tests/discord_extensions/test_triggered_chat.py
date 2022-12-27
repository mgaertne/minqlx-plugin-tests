from unittest.mock import AsyncMock

import pytest
from hamcrest import assert_that, is_
from mockito import verify, mock

# noinspection PyPackageRequirements
from discord import Message

from minqlx_plugin_test import setup_cvars
import minqlx
from discord_extensions import triggered_chat
from discord_extensions.triggered_chat import TriggeredChat


class TestTriggeredChat:
    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discordTriggeredChannelIds": "1234",
                "qlx_discordTriggerTriggeredChannelChat": "quakelive",
                "qlx_discordMessagePrefix": "[DISCORD]",
            }
        )

    @pytest.mark.asyncio
    async def test_message_from_wrong_channel_is_not_forwarded(
        self, bot, context, private_channel
    ):
        context.channel = private_channel

        extension = TriggeredChat(bot)

        await extension.triggered_chat(context)

        context.reply.assert_awaited_with(
            content="tried to send a message from the wrong channel", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_direct_message_is_not_forwarded(
        self, bot, context, user, guild_channel
    ):
        context.channel = guild_channel
        context.author = user

        extension = TriggeredChat(bot)

        await extension.triggered_chat(context)

        context.reply.assert_awaited_with(
            content="tried to send a message from a private message", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_text_triggered_chat_is_forwarded_to_ql(
        self, bot, context, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        context.channel = guild_channel
        context.author = member
        context.message.clean_content = "!quakelive message from discord to quake"

        extension = TriggeredChat(bot)

        await extension.triggered_chat(context)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_forwarded_message_uses_nick(
        self, bot, context, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        member.nick = "MemberNick"
        context.channel = guild_channel
        context.author = member
        context.message.clean_content = "!quakelive message from discord to quake"

        extension = TriggeredChat(bot)

        await extension.triggered_chat(context)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6MemberNick^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_slash_message_from_wrong_channel_is_not_forwarded(
        self, bot, interaction, private_channel
    ):
        interaction.channel = private_channel

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(interaction, message="message")

        interaction.response.send_message.assert_awaited_with(
            content="tried to send a message from the wrong channel", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_direct_slash_message_is_not_forwarded(
        self, bot, interaction, user, guild_channel
    ):
        interaction.channel = guild_channel
        interaction.user = user

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(interaction, message="message")

        interaction.response.send_message.assert_awaited_with(
            content="tried to send a message from a private message", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_slash_text_triggered_chat_is_forwarded_to_ql(
        self, bot, interaction, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        interaction.channel = guild_channel
        interaction.user = member

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(
            interaction, message="message from discord to quake"
        )

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_slash_forwarded_message_uses_nick(
        self, bot, interaction, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        member.nick = "MemberNick"
        interaction.channel = guild_channel
        interaction.user = member

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(
            interaction, message="message from discord to quake"
        )

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6MemberNick^7:^2 message from discord to quake"
        )

    @pytest.mark.parametrize("channel_id,expected", [(1234, True), (5678, False)])
    def test_is_message_inconfigured_triggered_channel(
        self, channel_id, expected, context, bot, guild_channel
    ):
        extension = TriggeredChat(bot)

        guild_channel.id = channel_id
        context.message = mock(spec=Message)
        context.message.channel = guild_channel

        assert_that(extension.is_message_in_triggered_channel(context), is_(expected))

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await triggered_chat.setup(bot)

        bot.add_cog.assert_awaited_once()
        assert_that(isinstance(bot.add_cog.call_args.args[0], TriggeredChat), is_(True))
