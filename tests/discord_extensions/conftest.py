import sys

import pytest
from mockito import mock, unstub

if sys.version_info < (3, 8):
    __test__ = False
else:
    from unittest.mock import AsyncMock

    # noinspection PyPackageRequirements
    from discord import User, Member, Client

    # noinspection PyPackageRequirements
    from discord.abc import GuildChannel, PrivateChannel


@pytest.fixture(name="bot")
def _bot(event_loop):
    bot = mock(
        {
            "add_command": mock(),
            "tree": mock(),
            "add_cog": AsyncMock(),
            "loop": event_loop,
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
    context = mock({"message": mock(), "reply": AsyncMock()})
    context.prefix = "!"
    context.invoked_with = "quakelive"

    yield context
    unstub(context)


@pytest.fixture(name="interaction")
def _interaction():
    interaction = mock()
    interaction.response = mock({"send_message": AsyncMock()})

    yield interaction
    unstub(interaction)


@pytest.fixture(name="user")
def _user():
    user = mock(spec=User)
    user.name = "DisordUser"
    user.nick = None

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

    yield channel
    unstub(channel)


@pytest.fixture(name="private_channel")
def _private_channel():
    channel = mock(spec=PrivateChannel)
    channel.name = "DiscordDMChannel"

    yield channel
    unstub(channel)
