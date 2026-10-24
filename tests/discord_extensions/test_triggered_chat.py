from types import SimpleNamespace

import pytest

# noinspection PyPackageRequirements
from discord import Message
from hamcrest import assert_that, equal_to
from minqlx_plugin_test import setup_cvars
from mockito import mock, verify

import minqlx
from discord_extensions import triggered_chat
from discord_extensions.triggered_chat import TriggeredChat, int_set


class TestTriggeredChat:
    @pytest.fixture(name="chat_context")
    def chat_context(self, context):
        context.invoked_with = "quakelive"
        yield context

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discordTriggeredChannelIds": "1234",
                "qlx_discordTriggerTriggeredChannelChat": "quakelive",
                "qlx_discordMessagePrefix": "[DISCORD]",
            }
        )

    def test_int_set_handles_none_empty_and_duplicate_values(self):
        assert int_set(None) == set()
        assert int_set(["", "123", "123", "456"]) == {123, 456}

    @pytest.mark.asyncio
    async def test_message_from_wrong_channel_is_not_forwarded(self, bot, chat_context, private_channel):
        chat_context.channel = private_channel

        extension = TriggeredChat(bot)

        await extension.triggered_chat(chat_context)

        chat_context.reply.assert_awaited_with(content="tried to send a message from the wrong channel", ephemeral=True)

    @pytest.mark.asyncio
    async def test_direct_message_is_not_forwarded(self, bot, chat_context, user, guild_channel):
        chat_context.channel = guild_channel
        chat_context.author = user

        extension = TriggeredChat(bot)

        await extension.triggered_chat(chat_context)

        chat_context.reply.assert_awaited_with(content="tried to send a message from a private message", ephemeral=True)

    @pytest.mark.asyncio
    async def test_text_triggered_chat_is_forwarded_to_ql(self, bot, chat_context, member, guild_channel, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        chat_context.channel = guild_channel
        chat_context.author = member
        chat_context.message.clean_content = "!quakelive message from discord to quake"

        extension = TriggeredChat(bot)

        await extension.triggered_chat(chat_context)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_forwarded_message_uses_nick(self, bot, chat_context, member, guild_channel, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        member.nick = "MemberNick"
        chat_context.channel = guild_channel
        chat_context.author = member
        chat_context.message.clean_content = "!quakelive message from discord to quake"

        extension = TriggeredChat(bot)

        await extension.triggered_chat(chat_context)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6MemberNick^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_slash_message_from_wrong_channel_is_not_forwarded(self, bot, interaction, private_channel):
        interaction.channel = private_channel

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(interaction, message="message")

        interaction.response.send_message.assert_awaited_with(
            content="tried to send a message from the wrong channel", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_direct_slash_message_is_not_forwarded(self, bot, interaction, user, guild_channel):
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

        await extension.slash_triggered_chat(interaction, message="message from discord to quake")

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_slash_forwarded_message_uses_nick(self, bot, interaction, member, guild_channel, mock_channel):
        minqlx.CHAT_CHANNEL = mock_channel
        member.nick = "MemberNick"
        interaction.channel = guild_channel
        interaction.user = member

        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(interaction, message="message from discord to quake")

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6MemberNick^7:^2 message from discord to quake"
        )

    @pytest.mark.asyncio
    async def test_slash_message_resolves_member_channel_and_role_mentions(
        self, bot, interaction, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        interaction.guild = SimpleNamespace(
            get_member=lambda _identifier: member,
            get_channel=lambda _identifier: guild_channel,
            get_role=lambda _identifier: SimpleNamespace(name="Moderator"),
        )
        interaction.channel = guild_channel
        interaction.user = member
        extension = TriggeredChat(bot)
        message = "Hi <@123456789012345>, <#123456789012345> and <@&123456789012345>"

        await extension.slash_triggered_chat(interaction, message=message)

        verify(minqlx.CHAT_CHANNEL).reply(
            "[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 Hi @DiscordMember, "
            "#DiscordGuildChannel and @&Moderator"
        )

    @pytest.mark.asyncio
    async def test_slash_message_replaces_deleted_member_and_returns_for_dm(
        self, bot, interaction, member, guild_channel, mock_channel
    ):
        minqlx.CHAT_CHANNEL = mock_channel
        interaction.guild = SimpleNamespace(get_member=lambda _identifier: None)
        interaction.channel = guild_channel
        interaction.user = member
        extension = TriggeredChat(bot)

        await extension.slash_triggered_chat(interaction, message="Hi <@!123456789012345>")

        verify(minqlx.CHAT_CHANNEL).reply("[DISCORD] ^5#DiscordGuildChannel ^6DiscordMember^7:^2 Hi @deleted-user")

        interaction.guild = None
        interaction.response.send_message.reset_mock()
        await extension.slash_triggered_chat(interaction, message="ignored")
        interaction.response.send_message.assert_not_awaited()

    @pytest.mark.parametrize("channel_id,expected", [(1234, True), (5678, False)])
    def test_is_message_inconfigured_triggered_channel(self, channel_id, expected, chat_context, bot, guild_channel):
        extension = TriggeredChat(bot)

        guild_channel.id = channel_id
        chat_context.message = mock(spec=Message)
        chat_context.message.channel = guild_channel

        assert_that(extension.is_message_in_triggered_channel(chat_context), equal_to(expected))

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await triggered_chat.setup(bot)

        bot.add_cog.assert_awaited_once()
        assert_that(isinstance(bot.add_cog.call_args.args[0], TriggeredChat), equal_to(True))
