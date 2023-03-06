from typing import TYPE_CHECKING

# noinspection PyPackageRequirements
from discord.ext.commands import Bot, Cog, Context

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from discord import Interaction

def int_set(string_set: set[str] | None) -> set[int]: ...

class TriggeredChat(Cog):
    bot: Bot
    discord_trigger_triggered_channel_chat: str
    discord_message_prefix: str
    discord_triggered_channel_ids: set[str]
    def __init__(self, bot: Bot) -> None: ...
    def is_message_in_triggered_channel(self, ctx: Context) -> bool: ...
    @staticmethod
    def command_length(ctx: Context) -> int: ...
    async def triggered_chat(self, ctx: Context, *_args: list, **_kwargs: dict) -> None: ...
    async def slash_triggered_chat(self, interaction: Interaction, message: str) -> None: ...

async def setup(bot: Bot) -> None: ...
