from typing import TYPE_CHECKING

# noinspection PyPackageRequirements
from discord.ext.commands import Cog

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from discord import Message

    # noinspection PyPackageRequirements
    from discord.ext.commands import Bot

def int_set(string_set: set[str]) -> set[int]: ...

class OpenAIBridge(Cog):
    bot: Bot
    bot_name: str
    bot_clanprefix: str
    bot_triggers: list[str]
    bot_role_chat: str
    def __init__(self, bot: Bot) -> None: ...
    async def on_message(self, message: Message) -> None: ...

async def setup(bot: Bot) -> None: ...
