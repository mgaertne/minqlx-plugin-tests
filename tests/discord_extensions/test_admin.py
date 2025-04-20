import asyncio
import functools
import threading
import time
from unittest.mock import AsyncMock

import pytest

# noinspection PyPackageRequirements
from discord import ChannelType, InteractionResponse
from hamcrest import assert_that, equal_to, matches_regexp, has_key, not_
from mockito import unstub, patch, spy2, when2, mock, verify
from undecorated import undecorated

from minqlx_plugin_test import setup_cvars
import minqlx

from discord_extensions import admin
from discord_extensions.admin import AdminCog, DiscordInteractionChannel, DiscordInteractionPlayer


class ThreadContextManager:
    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        time.sleep(0.1)
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                thread.join()


class TestAdmin:
    @pytest.fixture(name="auth_context")
    def auth_context(self, context):
        context.invoked_with = "auth"
        yield context

    @pytest.fixture(name="exec_context")
    def exec_context(self, context):
        context.invoked_with = "exec"
        yield context

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discordAdminPassword": "adminpassword",
                "qlx_discordAuthCommand": "auth",
                "qlx_discordExecPrefix": "exec",
            }
        )

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_is_private_message_for_guild_channel(self, bot, context, guild_channel):
        context.message.channel = guild_channel

        extension = AdminCog(bot)
        is_private = extension.is_private_message(context)

        assert_that(is_private, equal_to(False))

    def test_is_private_message_for_private_channel(self, bot, context, guild_channel):
        guild_channel.type = ChannelType.private
        context.message.channel = guild_channel

        extension = AdminCog(bot)
        is_private = extension.is_private_message(context)

        assert_that(is_private, equal_to(True))

    def test_user_not_authed(self, bot, context, user):
        context.message.author = user
        extension = AdminCog(bot)
        is_authed = extension.is_authed(context)

        assert_that(is_authed, equal_to(False))

    def test_user_has_authed(self, bot, context, user):
        context.message.author = user
        extension = AdminCog(bot)
        extension.authed_discord_ids.add(user.id)

        is_authed = extension.is_authed(context)

        assert_that(is_authed, equal_to(True))

    def test_user_with_no_auth_attempts_is_not_barred(self, bot, context, user):
        context.message.author = user
        extension = AdminCog(bot)

        is_barred = extension.is_barred_from_auth(context)

        assert_that(is_barred, equal_to(False))

    def test_user_with_two_auth_attempts_is_not_barred(self, bot, context, user):
        context.message.author = user

        extension = AdminCog(bot)
        extension.auth_attempts[user.id] = 1

        is_barred = extension.is_barred_from_auth(context)

        assert_that(is_barred, equal_to(False))

    def test_user_has_no_auth_attempts_left(self, bot, context, user):
        context.message.author = user

        extension = AdminCog(bot)
        extension.auth_attempts[user.id] = 0

        is_barred = extension.is_barred_from_auth(context)

        assert_that(is_barred, equal_to(True))

    @pytest.mark.asyncio
    async def test_successful_auth(self, bot, auth_context, user):
        auth_context.message.content = "!auth adminpassword"
        auth_context.message.author = user

        extension = AdminCog(bot)

        await extension.auth(auth_context)

        assert_that(extension.authed_discord_ids, equal_to({user.id}))
        auth_context.send.assert_awaited_once()
        assert_that(
            auth_context.send.await_args.args[0],
            matches_regexp(".*successfully authenticated.*"),
        )

    @pytest.mark.asyncio
    async def test_first_failed_auth_attempt(self, bot, auth_context, user):
        auth_context.message.content = "!auth wrong password"
        auth_context.message.author = user

        extension = AdminCog(bot)

        await extension.auth(auth_context)

        # noinspection PyTypeChecker
        assert_that(extension.auth_attempts, has_key(user.id))
        assert_that(
            auth_context.send.await_args.args[0], matches_regexp(".*Wrong password.*")
        )

    @pytest.mark.asyncio
    async def test_third_failed_auth_attempt_bars_user_from_auth(
        self, bot, auth_context, user
    ):
        auth_context.message.content = "!auth wrong password"
        auth_context.message.author = user

        extension = AdminCog(bot)

        extension.auth_attempts[user.id] = 1

        patch(threading.Timer, "start", lambda: None)

        await extension.auth(auth_context)

        assert_that(extension.auth_attempts[user.id], equal_to(0))
        assert_that(
            auth_context.send.await_args.args[0],
            matches_regexp(".*Maximum authentication attempts reached.*"),
        )

    @pytest.mark.asyncio
    async def test_third_failed_auth_attempt_bars_user_from_auth_and_resets_attempts(
        self, bot, auth_context, user
    ):
        auth_context.message.content = "!auth wrong password"
        auth_context.message.author = user

        extension = AdminCog(bot)

        extension.auth_attempts[user.id] = 1

        patch(threading.Event, "wait", lambda *args: None)

        with ThreadContextManager():
            await extension.auth(auth_context)

        # noinspection PyTypeChecker
        assert_that(extension.auth_attempts, not_(has_key(user.id)))  # type: ignore

    @pytest.mark.asyncio
    async def test_qlx_executes_command(self, bot, exec_context, user):
        exec_context.message.content = "!exec exec to minqlx"
        exec_context.message.author = user
        exec_context.author = user

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.qlx(exec_context)

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)

    @pytest.mark.asyncio
    async def test_qlx_fails_to_execute_command(self, bot, exec_context, user):
        exec_context.message.content = "!exec exec to minqlx"
        exec_context.message.author = user
        exec_context.author = user

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenRaise(Exception())

        patch(minqlx.log_exception, lambda: None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.qlx(exec_context)

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)
        exec_context.reply.return_value.edit.assert_called_once()
        assert_that(
            exec_context.reply.return_value.edit.call_args.kwargs["content"],
            matches_regexp(".*Exception.*"),
        )

    @pytest.mark.asyncio
    async def test_qlx_notifies_discord_user_about_execution(
        self, bot, exec_context, user
    ):
        exec_context.message.content = "!exec exec to minqlx"
        exec_context.message.author = user
        exec_context.author = user

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.qlx(exec_context)

        exec_context.reply.assert_awaited_once()
        assert_that(
            exec_context.reply.await_args.kwargs["content"],
            equal_to("executing command `exec to minqlx`"),
        )

    @pytest.mark.asyncio
    async def test_qlx_execute_for_command_not_in_whitelist(
        self, bot, exec_context, user
    ):
        setup_cvars(
            {"qlx_discordCommandsWhitelist": "allowed_command, another_allowed_command"}
        )

        exec_context.message.content = "!exec !blocked_commmand exec to minqlx"
        exec_context.message.author = user
        exec_context.author = user

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.qlx(exec_context)

        exec_context.reply.assert_awaited_once()
        assert_that(
            exec_context.reply.await_args.kwargs["content"],
            matches_regexp(".*`blocked_commmand` cannot be used.*"),
        )

    @pytest.mark.asyncio
    async def test_qlx_execute_for_command_allowed_in_whitelist(
        self, bot, exec_context, user
    ):
        setup_cvars(
            {"qlx_discordCommandsWhitelist": "allowed_command, another_allowed_command"}
        )

        exec_context.message.content = "!exec !allowed_command exec to minqlx"
        exec_context.message.author = user
        exec_context.author = user

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.qlx(exec_context)

        verify(minqlx.COMMANDS).handle_input(
            any, "!allowed_command exec to minqlx", any
        )

    @pytest.mark.asyncio
    async def test_slash_qlx_executes_command_when_user_is_not_authed(
        self, bot, interaction, user, guild_channel
    ):
        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )

        await extension.slash_qlx(interaction, "exec to minqlx")

        interaction.response.send_message.assert_awaited_once()
        assert_that(
            interaction.response.send_message.await_args.kwargs["content"],
            equal_to("Sorry, you are not authed with the bot"),
        )

    @pytest.mark.asyncio
    async def test_slash_qlx_executes_command(
        self, bot, interaction, user, guild_channel
    ):
        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )
        extension.authed_discord_ids.add(user.id)

        await extension.slash_qlx(interaction, "exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)

    @pytest.mark.asyncio
    async def test_slash_qlx_fails_to_execute_command(
        self, bot, interaction, user, guild_channel
    ):
        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenRaise(Exception())

        patch(minqlx.log_exception, lambda: None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )
        extension.authed_discord_ids.add(user.id)

        await extension.slash_qlx(interaction, "exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "exec to minqlx", any)
        original_response = await interaction.original_response()
        original_response.edit.assert_called_once()
        assert_that(
            original_response.edit.call_args.kwargs["content"],
            matches_regexp(".*Exception.*"),
        )

    @pytest.mark.asyncio
    async def test_slash_qlx_notifies_discord_user_about_execution(
        self, bot, interaction, user, guild_channel
    ):
        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )
        extension.authed_discord_ids.add(user.id)

        await extension.slash_qlx(interaction, "exec to minqlx")

        interaction.response.send_message.assert_awaited_once()
        assert_that(
            interaction.response.send_message.await_args.kwargs["content"],
            equal_to("executing command `exec to minqlx`"),
        )

    @pytest.mark.asyncio
    async def test_slash_qlx_execute_for_command_not_in_whitelist(
        self, bot, interaction, user, guild_channel
    ):
        setup_cvars(
            {"qlx_discordCommandsWhitelist": "allowed_command, another_allowed_command"}
        )

        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )
        extension.authed_discord_ids.add(user.id)

        await extension.slash_qlx(interaction, "!blocked_command")

        interaction.response.send_message.assert_awaited_once()
        assert_that(
            interaction.response.send_message.await_args.kwargs["content"],
            matches_regexp(".*`blocked_command` cannot be used.*"),
        )

    @pytest.mark.asyncio
    async def test_slash_qlx_execute_for_command_allowed_in_whitelist(
        self, bot, interaction, user, guild_channel
    ):
        setup_cvars(
            {"qlx_discordCommandsWhitelist": "allowed_command, another_allowed_command"}
        )

        interaction.user = user
        guild_channel.guild = 123
        interaction.channel = guild_channel

        spy2(minqlx.COMMANDS.handle_input)
        when2(minqlx.COMMANDS.handle_input, any, any, any).thenReturn(None)

        extension = AdminCog(bot)
        extension.execute_qlx_command = functools.partial(
            undecorated(extension.execute_qlx_command), extension
        )
        extension.authed_discord_ids.add(user.id)

        await extension.slash_qlx(interaction, "!allowed_command exec to minqlx")

        verify(minqlx.COMMANDS).handle_input(any, "!allowed_command exec to minqlx", any)

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, bot):
        await admin.setup(bot)

        bot.add_cog.assert_awaited_once()
        assert_that(isinstance(bot.add_cog.call_args.args[0], AdminCog), equal_to(True))


@pytest.fixture(name="message")
def _message():
    message = mock(spec=InteractionResponse)
    message.edit = AsyncMock()

    yield message

    unstub(message)


class TestDiscordInteractionChannel:
    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    @pytest.mark.asyncio
    async def test_expand_original_reply_fills_initial_description(self, user, message):
        channel = DiscordInteractionChannel(
            user, message, loop=asyncio.get_running_loop()
        )

        await channel.expand_original_reply(content="Hi there")

        message.edit.assert_awaited_once()
        assert_that(
            message.edit.await_args.kwargs["embed"].description,  # type: ignore
            equal_to("Hi there"),
        )

    @pytest.mark.asyncio
    async def test_expand_original_reply_extends_original_reply(self, user, message):
        channel = DiscordInteractionChannel(
            user, message, loop=asyncio.get_running_loop()
        )
        channel.embed.description = "initial text"

        await channel.expand_original_reply(content="Hi there")

        message.edit.assert_awaited_once()
        assert_that(
            message.edit.await_args.kwargs["embed"].description,  # type: ignore
            equal_to("initial text\nHi there"),
        )

    @pytest.mark.asyncio
    async def test_reply(self, user, message):
        channel = DiscordInteractionChannel(
            user, message, loop=asyncio.get_running_loop()
        )
        spy2(channel.expand_original_reply)

        channel.reply("Hi there")

        verify(channel).expand_original_reply(content="Hi there")


class TestDiscordInteractionPlayer:
    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_steam_id(self, user, event_loop, message):
        setup_cvars({"qlx_owner": "42"})

        player = DiscordInteractionPlayer(user, message, loop=event_loop)

        assert_that(player.steam_id, equal_to(42))

    def test_channel(self, user, event_loop, message):
        player = DiscordInteractionPlayer(user, message, loop=event_loop)

        assert_that(isinstance(player.channel, minqlx.AbstractChannel))

    @pytest.mark.asyncio
    async def test_tell(self, user, message, event_loop):
        player = DiscordInteractionPlayer(
            user, message, loop=event_loop
        )

        player.tell("Hi there")

        while len(asyncio.all_tasks(loop=event_loop)) > 1:
            await asyncio.sleep(0.1)
        message.edit.assert_awaited_once()
        assert_that(message.edit.await_args.kwargs["embed"].description, equal_to("Hi there"))
