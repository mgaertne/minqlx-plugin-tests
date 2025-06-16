import sys
import asyncio

import pytest
import pytest_asyncio
from mockito import mock, unstub

if sys.version_info < (3, 8):
    __test__ = False
else:
    from unittest.mock import AsyncMock

    # noinspection PyPackageRequirements
    from discord import User, Member, Client, ChannelType

    # noinspection PyPackageRequirements
    from discord.abc import GuildChannel, PrivateChannel


@pytest_asyncio.fixture(name="bot")
async def _bot():
    bot = mock(
        {
            "add_command": mock(),
            "tree": mock(),
            "add_cog": AsyncMock(),
            "loop": asyncio.get_running_loop(),
            "client": mock(spec=Client),
        }
    )
    bot.client.user = mock(spec=User)
    bot.client.user.id = 666
    bot.client.user.mention = "@DiscordBotUser"
    bot.tree.add_command = mock()

    yield bot
    unstub(bot)


@pytest.fixture(name="context")
def _context():
    context = mock({"message": mock(), "reply": AsyncMock(), "send": AsyncMock()})
    replied_message = AsyncMock()
    replied_message.edit = AsyncMock()
    context.reply.return_value = replied_message
    context.prefix = "!"

    yield context
    unstub(context)


@pytest.fixture(name="interaction")
def _interaction():
    interaction = mock({"original_response": AsyncMock(), "edit_original_response": AsyncMock()})
    interaction.original_response.reply = AsyncMock()
    interaction.response = mock({"send_message": AsyncMock(), "defer": AsyncMock()})

    yield interaction
    unstub(interaction)


@pytest.fixture(name="user")
def _user():
    user = mock(spec=User)
    user.id = 42
    user.name = "DisordUser"
    user.display_name = user.name
    user.nick = None
    user.send = AsyncMock()

    yield user
    unstub(user)


@pytest.fixture(name="member")
def _member():
    member = mock(spec=Member)
    member.id = 42
    member.name = "DiscordMember"
    member.display_name = "DiscordMember"
    member.nick = None
    member.mention = "@DiscordMember"

    yield member
    unstub(member)


@pytest.fixture(name="guild_channel")
def _guild_channel():
    channel = mock(spec=GuildChannel)
    channel.name = "DiscordGuildChannel"
    channel.type = ChannelType.text

    yield channel
    unstub(channel)


@pytest.fixture(name="private_channel")
def _private_channel():
    channel = mock(spec=PrivateChannel)
    channel.name = "DiscordDMChannel"

    yield channel
    unstub(channel)
