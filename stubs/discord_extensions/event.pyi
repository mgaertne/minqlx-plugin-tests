from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import NoReturn

    # noinspection PyPackageRequirements
    from discord.ext.commands import Bot

async def create_and_start_event(bot: Bot) -> None: ...
async def end_event(bot: Bot) -> None: ...
def check_playing_activity(bot: Bot) -> None: ...
async def setup(bot: Bot) -> None: ...
def run_schedule() -> NoReturn: ...
