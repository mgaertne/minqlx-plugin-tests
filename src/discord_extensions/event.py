import asyncio
import threading
import time
from datetime import timedelta, datetime, timezone
from contextlib import suppress

# noinspection PyPackageRequirements
from discord import PrivacyLevel, EntityType, EventStatus
from discord.errors import NotFound, Forbidden

# noinspection PyPackageRequirements
from discord.utils import utcnow

import schedule  # type: ignore

from minqlx import Plugin


async def create_and_start_event(bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    if event_name is None:
        return

    active_event_found = False

    now = datetime.now(timezone.utc)

    end_events = []
    for scheduled_event in bot.guilds[0].scheduled_events:
        if (
            event_name in scheduled_event.name
            and scheduled_event.status not in [EventStatus.scheduled, EventStatus.completed, EventStatus.cancelled]
            and scheduled_event.end_time is not None
            and scheduled_event.end_time >= now
        ):
            if not active_event_found:
                active_event_found = True
            else:
                end_events.append(scheduled_event.delete())

    with suppress(NotFound):
        await asyncio.gather(*end_events)
    if active_event_found:
        return

    event_location = Plugin.get_cvar("qlx_discord_ext_event_location")
    if event_location is None:
        return

    start_date = utcnow() + timedelta(seconds=1)
    end_date = utcnow() + timedelta(hours=8)
    event = await bot.guilds[0].create_scheduled_event(
        name=event_name,
        privacy_level=PrivacyLevel.guild_only,
        start_time=start_date,
        end_time=end_date,
        entity_type=EntityType.external,
        location=event_location,
    )
    await event.start()


async def end_event(bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    if event_name is None:
        return

    now = datetime.now(timezone.utc)

    end_events = []
    for scheduled_event in bot.guilds[0].scheduled_events:
        if (
            event_name in scheduled_event.name
            and scheduled_event.status not in [EventStatus.scheduled, EventStatus.completed, EventStatus.cancelled]
            and scheduled_event.end_time is not None
            and scheduled_event.end_time >= now
        ):
            end_events.append(scheduled_event.end())

    with suppress(Forbidden):
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
