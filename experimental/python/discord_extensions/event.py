import asyncio
import threading
import time
from datetime import timedelta

from discord import PrivacyLevel, EntityType, EventStatus
from discord.utils import utcnow
from discord.ext.commands import Bot

import minqlx
from minqlx import Plugin

import schedule


async def create_and_start_event(bot: Bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    for scheduled_event in bot.guilds[0].scheduled_events:
        if event_name in scheduled_event.name and scheduled_event.status == EventStatus.active:
            return

    event_location = Plugin.get_cvar("qlx_discord_ext_event_location")
    start_date = utcnow() + timedelta(seconds=1)
    end_date = utcnow() + timedelta(hours=6)
    await bot.guilds[0].create_scheduled_event(
        name=event_name, privacy_level=PrivacyLevel.guild_only, start_time=start_date, end_time=end_date,
        entity_type=EntityType.external,
        location=event_location)


async def end_event(bot: Bot):
    event_name = Plugin.get_cvar("qlx_discord_ext_event_name")
    end_date = utcnow() + timedelta(seconds=2)
    for scheduled_event in bot.guilds[0].scheduled_events:
        if event_name in scheduled_event.name and scheduled_event.status == EventStatus.active:
            await scheduled_event.edit(
                name=scheduled_event.name,
                description=scheduled_event.description,
                channel=scheduled_event.channel,
                start_time=scheduled_event.start_time,
                end_time=end_date,
                privacy_level=scheduled_event.privacy_level,
                entity_type=EntityType.external,
                status=EventStatus.ended,
                location=scheduled_event.location)


def check_playing_activity(bot: Bot) -> None:
    try:
        game = minqlx.Game()
    except minqlx.NonexistentGameError:
        return

    if game.state == "in_progress":
        asyncio.run_coroutine_threadsafe(create_and_start_event(bot), loop=bot.loop)

#    players = Plugin.players()
#    if len(players) == 0:
#        asyncio.run_coroutine_threadsafe(end_event(bot), loop=bot.loop)


async def setup(bot: Bot):
    schedule.every(1).minute.do(check_playing_activity, bot)
    threading.Thread(target=run_schedule).start()


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)
