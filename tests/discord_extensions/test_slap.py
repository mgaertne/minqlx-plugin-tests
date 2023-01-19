import random
from unittest.mock import AsyncMock

import pytest

# noinspection PyPackageRequirements
from discord import Member, InteractionMessage

# noinspection PyProtectedMember
from mockito import mock, unstub, spy2, when, any_, verify

from minqlx_plugin_test import setup_cvars
from minqlx import Plugin

from discord_extensions import slap


class TestSlap:

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discordRelayChannelIds": "1234",
                "qlx_displayChannelForDiscordRelayChannels": "0",
                "qlx_discordMessagePrefix": "[DISCORD]",
            }
        )

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    @pytest.mark.asyncio
    async def test_hidden_slap(self, bot, interaction, member):
        interaction.client = mock(spec=Member)
        interaction.client.user = None

        await slap._slap(interaction, member)  # pylint: disable=W0212

        interaction.response.send_message.assert_awaited_once_with("_@DiscordMember is slapped from the hidden._")

    @pytest.mark.asyncio
    async def test_revenge_slap(self, bot, interaction, member):
        interaction.user = member
        interaction.client = mock(spec=Member)
        interaction.client.user = bot.client.user

        await slap._slap(interaction, bot.client.user)  # pylint: disable=W0212

        interaction.response.send_message.assert_awaited_once_with("_slaps @DiscordMember with a large revenge trout._")

    @pytest.mark.asyncio
    async def test_self_slap(self, bot, interaction, member):
        interaction.user = member
        interaction.client = mock(spec=Member)
        interaction.client.user = bot.client.user

        await slap._slap(interaction, member)  # pylint: disable=W0212

        interaction.response.send_message.assert_awaited_once_with("_@DiscordMember slaps himself for his stupidity._")

    @pytest.mark.asyncio
    async def test_slap_of_other_user(self, bot, interaction, member):
        interaction.user = member
        interaction.client = mock(spec=Member)
        interaction.client.user = bot.client.user

        other_user = mock(spec=Member)
        other_user.id = 21
        other_user.mention = "@SlappedDiscordMember"
        other_user.display_name = "SlappedDiscordMember"

        spy2(random.choice)
        when(random).choice(any_).thenReturn(
            f"_{interaction.user.mention} slaps {other_user.mention} with a large trout._"
        )

        await slap._slap(interaction, other_user)  # pylint: disable=W0212

        interaction.response.send_message.assert_awaited_once_with(
            "_@DiscordMember slaps @SlappedDiscordMember with a large trout._"
        )

    @pytest.mark.asyncio
    async def test_slap_is_forwarded_to_relay_channel(self, bot, interaction, member):
        other_user = mock(spec=Member)
        other_user.id = 21
        other_user.mention = "@SlappedDiscordMember"
        other_user.display_name = "SlappedDiscordMember"

        interaction.channel_id = 1234
        mocked_original_message = AsyncMock()
        mocked_response = mock(spec=InteractionMessage)
        mocked_response.clean_content = \
            f"{member.mention} slaps {other_user.mention} with a large trout."
        mocked_original_message.return_value = mocked_response
        mocked_response.mentions = [member, other_user]
        interaction.original_response = mocked_original_message
        interaction.user = member
        interaction.client = mock(spec=Member)
        interaction.client.user = bot.client.user

        spy2(random.choice)
        when(random).choice(any_).thenReturn(
            f"_{interaction.user.mention} slaps {other_user.mention} with a large trout._"
        )

        await slap._slap(interaction, other_user)  # pylint: disable=W0212

        verify(Plugin).msg("[DISCORD]^2 @DiscordMember slaps @SlappedDiscordMember with a large trout.")

    @pytest.mark.asyncio
    async def test_slap_is_forwarded_to_relay_channel_with_channel_name(self, bot, interaction, member, guild_channel):
        setup_cvars({"qlx_displayChannelForDiscordRelayChannels": "1"})
        other_user = mock(spec=Member)
        other_user.id = 21
        other_user.mention = "@SlappedDiscordMember"
        other_user.display_name = "SlappedDiscordMember"

        interaction.channel_id = 1234
        interaction.channel = guild_channel
        mocked_original_message = AsyncMock()
        mocked_response = mock(spec=InteractionMessage)
        mocked_response.clean_content = \
            f"{member.mention} slaps {other_user.mention} with a large trout."
        mocked_original_message.return_value = mocked_response
        mocked_response.mentions = [member, other_user]
        interaction.original_response = mocked_original_message
        interaction.user = member
        interaction.client = mock(spec=Member)
        interaction.client.user = bot.client.user

        spy2(random.choice)
        when(random).choice(any_).thenReturn(
            f"_{interaction.user.mention} slaps {other_user.mention} with a large trout._"
        )

        await slap._slap(interaction, other_user)  # pylint: disable=W0212

        verify(Plugin).msg(
            "[DISCORD] ^5#DiscordGuildChannel^7:^2 @DiscordMember slaps @SlappedDiscordMember with a large trout."
        )

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await slap.setup(bot)

        bot.tree.add_command.assert_called_once_with(slap.slap)
