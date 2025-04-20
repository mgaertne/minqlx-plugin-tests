from typing import TYPE_CHECKING

# noinspection PyPackageRequirements
from discord.ext.commands import Cog

from minqlx import AbstractChannel, AbstractDummyPlayer

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    # noinspection PyPackageRequirements
    from discord import Interaction as Interaction, Message, User, Embed

    # noinspection PyPackageRequirements
    from discord.ext.commands import Bot, Context

    # noinspection PyPackageRequirements
    import discord.utils

class DiscordInteractionChannel(AbstractChannel):
    user: User
    message: Message
    loop: AbstractEventLoop
    embed: Embed
    def __init__(
        self, user: User, message: Message, *, loop: AbstractEventLoop
    ) -> None: ...
    async def expand_original_reply(self, content: str) -> None: ...
    def reply(self, msg: str, _limit: int = ..., _delimiter: str = ...) -> None: ...

class DiscordInteractionPlayer(AbstractDummyPlayer):
    user: User
    message: Message
    loop: AbstractEventLoop
    def __init__(
        self, user: User, message: Message, *, loop: AbstractEventLoop
    ) -> None: ...
    @property
    def steam_id(self) -> int | None: ...
    @property
    def channel(self) -> AbstractChannel: ...
    def tell(self, msg: str, **_kwargs: dict) -> None: ...

class AdminCog(Cog):
    bot: Bot
    authed_discord_ids: set[int]
    auth_attempts: dict[int, int]
    discord_admin_password: str
    discord_auth_command: str
    discord_exec_prefix: str
    discord_commands_whitelist: list[str]
    def __init__(self, bot: Bot) -> None: ...
    @staticmethod
    def is_private_message(ctx: Context) -> bool: ...
    def is_authed(self, ctx: Context) -> bool: ...
    def is_barred_from_auth(self, ctx: Context) -> bool: ...
    async def auth(self, ctx: Context, *_args: list, **_kwargs: dict) -> None: ...
    def auth_reply_for(self, discord_id: int, password: str) -> str: ...
    @staticmethod
    def command_length(ctx: Context) -> int: ...
    async def qlx(self, ctx: Context, *_args: list, **_kwargs: dict) -> None: ...
    def execute_qlx_command(
        self, user: discord.User, message: Message, qlx_command: str
    ) -> None: ...
    async def slash_qlx(self, interaction: Interaction, command: str) -> None: ...

async def setup(bot: Bot) -> None: ...
