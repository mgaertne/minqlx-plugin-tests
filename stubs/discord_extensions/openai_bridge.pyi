# noinspection PyPackageRequirements
from discord import Message

# noinspection PyPackageRequirements
from discord.ext.commands import Cog, Bot

def int_set(string_set: set[str]) -> set[int]: ...

class OpenAIBridge(Cog):
    bot: Bot
    bot_name: str
    bot_clanprefix: str
    def __init__(self, bot: Bot) -> None: ...
    async def on_message(self, message: Message) -> None: ...

async def setup(bot: Bot) -> None: ...