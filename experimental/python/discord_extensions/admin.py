import asyncio
from asyncio import AbstractEventLoop
import threading

# noinspection PyPackageRequirements
import discord.utils
# noinspection PyPackageRequirements
from discord import app_commands, Embed, Color, ChannelType, Interaction, Message, User
# noinspection PyPackageRequirements
from discord.ext.commands import Cog, Bot, Command, Context

import minqlx
from minqlx import Plugin


class DiscordInteractionChannel(minqlx.AbstractChannel, minqlx.AbstractDummyPlayer):
    """
    a minqlx channel class to respond to from within minqlx for interactions with discord
    """
    def __init__(self, user: User, message: Message, *, loop: AbstractEventLoop):
        self.user: User = user
        self.message: Message = message
        self.loop: AbstractEventLoop = loop
        self.embed = Embed(color=Color.red())

        super().__init__(name=f"Discord-{self.user.display_name}")

    def __repr__(self) -> str:
        return f"{str(self)} {self.user.display_name}"

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

        await self.message.edit(embed=self.embed)

    def tell(self, msg: str) -> None:
        """
        overwrites the ```player.tell``` function to relay messages to discord

        :param: msg: the msg to send to this player
        """
        asyncio.run_coroutine_threadsafe(
            self.expand_original_reply(content=Plugin.clean_text(msg)),
            loop=self.loop)

    def reply(self, msg: str) -> None:
        """
        overwrites the ```channel.reply``` function to relay messages to discord

        :param: msg: the message to send to this channel
        """
        asyncio.run_coroutine_threadsafe(
            self.expand_original_reply(content=Plugin.clean_text(msg)),
            loop=self.loop)


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

        self.bot.add_command(Command(self.auth, name=self.discord_auth_command,
                                     checks=[self.is_private_message, lambda ctx: not self.is_authed(ctx),
                                             lambda ctx: not self.is_barred_from_auth(ctx)],
                                     hidden=True,
                                     pass_context=True,
                                     help="auth with the bot",
                                     require_var_positional=True))
        self.bot.add_command(Command(self.qlx, name=self.discord_exec_prefix,
                                     checks=[self.is_private_message, self.is_authed],
                                     hidden=True,
                                     pass_context=True,
                                     help="execute minqlx commands on the server",
                                     require_var_positional=True))
        self.bot.tree.add_command(
            app_commands.Command(name=self.discord_exec_prefix,
                                 description="execute minqlx commands on the server",
                                 callback=self.slash_qlx,
                                 parent=None,
                                 nsfw=False))

        super().__init__()

    async def cog_load(self):
        await self.bot.tree.sync()

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
        command_length = self.command_length(ctx)
        qlx_command = ctx.message.content[command_length:]
        message = await ctx.reply(content=f"executing command `{qlx_command}`", ephemeral=False)
        self.execute_qlx_command(ctx.author, message, qlx_command)

    @minqlx.next_frame
    def execute_qlx_command(self, user: discord.User, message: Message, qlx_command: str):
        discord_interaction = DiscordInteractionChannel(user, message, loop=self.bot.loop)
        try:
            minqlx.COMMANDS.handle_input(discord_interaction, qlx_command, discord_interaction)
        except Exception as e:  # pylint: disable=broad-except
            send_message = message.edit(content=f"{e.__class__.__name__}: {e}")
            asyncio.run_coroutine_threadsafe(send_message, loop=self.bot.loop)
            minqlx.log_exception()

    @app_commands.describe(command="minqlx ommand to execute on the server")
    async def slash_qlx(self, interaction: Interaction, command: str):
        if interaction.user.id not in self.authed_discord_ids:
            await interaction.response.send_message(content="Sorry, you are not authed with the bot",
                                                    ephemeral=interaction.channel.guild is not None)
            return

        await interaction.response.send_message(content=f"executing command `{command}`",
                                                ephemeral=interaction.channel.guild is not None)
        message = await interaction.original_message()
        self.execute_qlx_command(interaction.user, message, command)


async def setup(bot: Bot):
    await bot.add_cog(AdminCog(bot))
