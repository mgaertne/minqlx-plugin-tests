import asyncio
import threading
from typing import Union

import discord.utils
from discord import app_commands, Embed, Color, Member, TextChannel, DMChannel, ChannelType, Interaction
from discord.ext.commands import Cog, Bot, Command, Context

import minqlx
from minqlx import Plugin


class DiscordInteractionChannel(minqlx.AbstractChannel, minqlx.AbstractDummyPlayer):
    """
    a minqlx channel class to respond to from within minqlx for interactions with discord
    """
    def __init__(self, client: Bot, interaction: Interaction):
        super().__init__("discord")
        self.client: Bot = client
        self.interaction: Interaction = interaction
        self.embed = Embed(color=Color.red())

    def __repr__(self) -> str:
        return f"{str(self)} {self.interaction.user.display_name}"

    @property
    def steam_id(self) -> int:
        return minqlx.owner()

    @property
    def channel(self) -> minqlx.AbstractChannel:
        return self

    async def expand_original_reply(self, content: str):
        if self.embed.description is None:
            self.embed.description = content
        else:
            self.embed.description = f"{self.embed.description}\n{discord.utils.escape_markdown(content)}"

        await self.interaction.edit_original_message(embed=self.embed)

    def tell(self, msg: str) -> None:
        """
        overwrites the ```player.tell``` function to relay messages to discord

        :param: msg: the msg to send to this player
        """
        asyncio.run_coroutine_threadsafe(
            self.expand_original_reply(content=Plugin.clean_text(msg)),
            loop=self.client.loop)

    def reply(self, msg: str) -> None:
        """
        overwrites the ```channel.reply``` function to relay messages to discord

        :param: msg: the message to send to this channel
        """
        asyncio.run_coroutine_threadsafe(
            self.expand_original_reply(content=Plugin.clean_text(msg)),
            loop=self.client.loop)


class DiscordChannel(minqlx.AbstractChannel):
    """
    a minqlx channel class to respond to from within minqlx for interactions with discord
    """
    def __init__(self, client: Bot, author: Member, discord_channel: Union[TextChannel, DMChannel]):
        super().__init__("discord")
        self.client: Bot = client
        self.author: Member = author
        self.discord_channel: Union[TextChannel, DMChannel] = discord_channel

    def __repr__(self) -> str:
        return f"{str(self)} {self.author.display_name}"

    def reply(self, msg: str) -> None:
        """
        overwrites the ```channel.reply``` function to relay messages to discord

        :param: msg: the message to send to this channel
        """
        asyncio.run_coroutine_threadsafe(
            self.discord_channel.send(discord.utils.escape_markdown(Plugin.clean_text(msg))),
            loop=self.client.loop)


class DiscordDummyPlayer(minqlx.AbstractDummyPlayer):
    """
    a minqlx dummy player class to relay messages to discord
    """
    def __init__(self, client: Bot, author: Member, discord_channel: Union[TextChannel, DMChannel]):
        self.client: Bot = client
        self.author: Member = author
        self.discord_channel: Union[TextChannel, DMChannel] = discord_channel
        super().__init__(name=f"Discord-{author.display_name}")

    @property
    def steam_id(self) -> int:
        return minqlx.owner()

    @property
    def channel(self) -> minqlx.AbstractChannel:
        return DiscordChannel(self.client, self.author, self.discord_channel)

    def tell(self, msg: str) -> None:
        """
        overwrites the ```player.tell``` function to relay messages to discord

        :param: msg: the msg to send to this player
        """
        asyncio.run_coroutine_threadsafe(
            self.discord_channel.send(discord.utils.escape_markdown(Plugin.clean_text(msg))),
            loop=self.client.loop)


class AdminCog(Cog):
    """
    Uses:
    * qlx_discordAdminPassword (default "supersecret") passwort for remote admin of the server via discord private
    messages to the discord bot.
    * qlx_discordAuthCommand (default: "auth") command for authenticating a discord user to the plugin via private
    message
    * qlx_discordExecPrefix (default: "qlx") command for authenticated users to execute server commands from discord

    """
    def __init__(self, bot: Bot):
        Plugin.set_cvar_once("qlx_discordAdminPassword", "supersecret")
        Plugin.set_cvar_once("qlx_discordAuthCommand", "auth")
        Plugin.set_cvar_once("qlx_discordExecPrefix", "qlx")

        self.bot = bot

        self.authed_discord_ids: set[int] = set()
        self.auth_attempts: dict[int: int] = {}

        self.discord_admin_password: str = Plugin.get_cvar("qlx_discordAdminPassword")
        self.discord_auth_command: str = Plugin.get_cvar("qlx_discordAuthCommand")
        self.discord_exec_prefix: str = Plugin.get_cvar("qlx_discordExecPrefix")

        bot.add_command(Command(self.auth, name=self.discord_auth_command,
                                checks=[self.is_private_message, lambda ctx: not self.is_authed(ctx),
                                        lambda ctx: not self.is_barred_from_auth(ctx)],
                                hidden=True,
                                pass_context=True,
                                help="auth with the bot",
                                require_var_positional=True))
        bot.add_command(Command(self.qlx, name=self.discord_exec_prefix,
                                checks=[self.is_private_message, self.is_authed],
                                hidden=True,
                                pass_context=True,
                                help="execute minqlx commands on the server",
                                require_var_positional=True))

        super().__init__()

    @staticmethod
    def is_private_message(ctx: Context) -> bool:
        """
        Checks whether a message was sent on a private chat to the bot

        :param: ctx: the context the trigger happened in
        """
        return ctx.message.channel.type == ChannelType.private

    def is_authed(self, ctx: Context) -> bool:
        """
        Checks whether a user is authed to the bot

        :param: ctx: the context the trigger happened in
        """
        return ctx.message.author.id in self.authed_discord_ids

    def is_barred_from_auth(self, ctx: Context) -> bool:
        """
        Checks whether an author is currently barred from authentication to the bot

        :param: ctx: the context the trigger happened in
        """
        return ctx.message.author.id in self.auth_attempts and self.auth_attempts[ctx.message.author.id] <= 0

    async def auth(self, ctx: Context, *_args, **_kwargs) -> None:
        """
        Handles the authentication to the bot via private message

        :param: ctx: the context of the original message sent for authentication
        :param: password: the password to authenticate
        """
        command_length = self.command_length(ctx)
        password = ctx.message.content[command_length:]
        await ctx.send(self.auth_reply_for(ctx.message.author.id, password))

    def auth_reply_for(self, discord_id: int, password: str) -> str:
        if password == self.discord_admin_password:
            self.authed_discord_ids.add(discord_id)
            return f"You have been successfully authenticated. " \
                   f"You can now use {self.discord_exec_prefix} to execute commands."

        # Allow up to 3 attempts for the user's discord id to authenticate.
        if discord_id not in self.auth_attempts:
            self.auth_attempts[discord_id] = 3
        self.auth_attempts[discord_id] -= 1
        if self.auth_attempts[discord_id] > 0:
            return f"Wrong password. You have {self.auth_attempts[discord_id]} attempts left."

        # User has reached maximum auth attempts, we will bar her/him from authentication for 5 minutes (300 seconds)
        bar_delay = 300

        def f():
            del self.auth_attempts[discord_id]

        threading.Timer(bar_delay, f).start()
        return f"Maximum authentication attempts reached. " \
               f"You will be barred from authentication for {bar_delay} seconds."

    @staticmethod
    def command_length(ctx: Context) -> int:
        return len(f"{ctx.prefix}{ctx.invoked_with} ")

    async def qlx(self, ctx: Context, *_args, **_kwargs) -> None:
        """
        Handles exec messages from discord via private message to the bot

        :param: ctx: the context the trigger happened in
        :param: qlx_command: the command that was sent by the user
        """
        @minqlx.next_frame
        def f():
            command_length = self.command_length(ctx)
            qlx_command = ctx.message.content[command_length:].split(" ")
            try:
                minqlx.COMMANDS.handle_input(
                    DiscordDummyPlayer(ctx.bot, ctx.message.author, ctx.message.channel),
                    " ".join(qlx_command),
                    DiscordChannel(ctx.bot, ctx.message.author, ctx.message.channel))
            except Exception as e:  # pylint: disable=broad-except
                send_message = ctx.send(f"{e.__class__.__name__}: {e}")
                asyncio.run_coroutine_threadsafe(send_message, loop=ctx.bot.loop)
                minqlx.log_exception()

        f()

    @app_commands.command(name="qlx", description="execute minqlx commands on the server")
    @app_commands.describe(command="minqlx ommand to execute on the server")
    async def slash_qlx(self, interaction: Interaction, command: str):
        if interaction.user.id not in self.authed_discord_ids:
            await interaction.response.send_message(content="Sorry, you are not authed with the bot",
                                                    ephemeral=interaction.channel.guild is not None)
            return

        @minqlx.next_frame
        def f():
            discord_interaction = DiscordInteractionChannel(self.bot, interaction)
            try:
                minqlx.COMMANDS.handle_input(discord_interaction, command, discord_interaction)
            except Exception as e:  # pylint: disable=broad-except
                send_message = interaction.edit_original_message(content=f"{e.__class__.__name__}: {e}")
                asyncio.run_coroutine_threadsafe(send_message, loop=self.bot.loop)
                minqlx.log_exception()

        await interaction.response.send_message(content=f"executing command {command}",
                                                ephemeral=interaction.channel.guild is not None)
        f()


async def setup(bot: Bot):
    await bot.add_cog(AdminCog(bot))
