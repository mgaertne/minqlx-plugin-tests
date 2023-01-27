import asyncio
import threading
import time
from datetime import timedelta

# noinspection PyPackageRequirements
from discord import PrivacyLevel, EntityType, EventStatus

# noinspection PyPackageRequirements
from discord.utils import utcnow

# noinspection PyPackageRequirements
import schedule  # type: ignore

from minqlx import Plugin


async def create_and_start_event(bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    if event_name is None:
        return

    for scheduled_event in bot.guilds[0].scheduled_events:
        if event_name in scheduled_event.name and scheduled_event.status == EventStatus.active:
            return

    event_location = Plugin.get_cvar("qlx_discord_ext_event_location")
    if event_location is None:
        return

    start_date = utcnow() + timedelta(seconds=1)
    end_date = utcnow() + timedelta(hours=8)
    await bot.guilds[0].create_scheduled_event(
        name=event_name,
        privacy_level=PrivacyLevel.guild_only,
        start_time=start_date,
        end_time=end_date,
        entity_type=EntityType.external,
        location=event_location,
    )


async def end_event(bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    if event_name is None:
        return

    end_events = []
    for scheduled_event in bot.guilds[0].scheduled_events:
        if event_name in scheduled_event.name and scheduled_event.status == EventStatus.active:
            end_events.append(scheduled_event.end())

    await asyncio.gather(*end_events)


def check_playing_activity(bot):
    players = Plugin.players()
    if len(players) == 0:
        bot.loop.create_task(end_event(bot))
    else:
        bot.loop.create_task(create_and_start_event(bot))


async def setup(bot):
    if not bot.intents.guild_scheduled_events:
        raise ValueError("client needs guild_scheduled_events for this extension")

    schedule.every(1).minute.do(check_playing_activity, bot)
    threading.Thread(target=run_schedule).start()


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)
