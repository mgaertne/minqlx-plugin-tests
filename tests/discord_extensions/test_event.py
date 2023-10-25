import threading
from unittest.mock import AsyncMock

import pytest

# noinspection PyPackageRequirements
from discord import (
    Intents,
    Guild,
    PrivacyLevel,
    EntityType,
    ScheduledEvent,
    EventStatus,
)
from hamcrest import assert_that, equal_to, has_entries

# noinspection PyProtectedMember
from mockito import mock, any_, when2, spy2, verify, unstub

from minqlx_plugin_test import setup_cvars, connected_players, fake_player
from minqlx import Plugin
from discord_extensions import event


class TestEvent:
    @pytest.fixture(name="mocked_guild")
    def _guild(self, bot):
        guild = mock(spec=Guild)
        guild.scheduled_events = []
        guild.create_scheduled_event = AsyncMock()
        bot.guilds = [guild]

        yield guild

        unstub(guild)

    @pytest.fixture(name="mocked_active_event")
    def _event(self):
        mocked_event = mock(spec=ScheduledEvent)
        mocked_event.end = AsyncMock()
        mocked_event.delete = AsyncMock()
        mocked_event.name = "event name"
        mocked_event.status = EventStatus.active

        yield mocked_event

        unstub(mocked_event)

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars(
            {
                "qlx_discord_ext_event_name": "event name",
                "qlx_discord_ext_event_location": "event location",
            }
        )

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    @pytest.mark.asyncio
    async def test_create_and_start_event_is_created_and_started(
        self, bot, mocked_guild
    ):
        await event.create_and_start_event(bot)

        mocked_guild.create_scheduled_event.assert_awaited_once()
        assert_that(
            mocked_guild.create_scheduled_event.await_args.kwargs,
            has_entries(
                {
                    "name": "event name",
                    "privacy_level": PrivacyLevel.guild_only,
                    "entity_type": EntityType.external,
                    "location": "event location",
                }
            ),
        )

    @pytest.mark.asyncio
    async def test_create_and_start_event_when_event_already_started(
        self, bot, mocked_guild, mocked_active_event
    ):
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.create_and_start_event(bot)

        mocked_guild.create_scheduled_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_and_start_event_deletes_existing_event_that_did_not_start_yet(
        self, bot, mocked_guild, mocked_active_event
    ):
        mocked_active_event.status = EventStatus.scheduled
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.create_and_start_event(bot)

        mocked_active_event.delete.assert_awaited_once()
        mocked_guild.create_scheduled_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_and_start_event_event_misconfigured_event_name_cvar(
        self, bot, mocked_guild
    ):
        when2(Plugin.get_cvar, "qlx_discord_ext_event_name").thenReturn(None)
        when2(Plugin.get_cvar, "qlx_discord_ext_event_location").thenReturn(
            "event location"
        )

        await event.create_and_start_event(bot)

        mocked_guild.create_scheduled_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_and_start_event_event_misconfigured_event_location_cvar(
        self, bot, mocked_guild
    ):
        when2(Plugin.get_cvar, "qlx_discord_ext_event_name").thenReturn("event name")
        when2(Plugin.get_cvar, "qlx_discord_ext_event_location").thenReturn(None)

        await event.create_and_start_event(bot)

        mocked_guild.create_scheduled_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_end_event_ends_active_event_that_matches(
        self, bot, mocked_guild, mocked_active_event
    ):
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.end_event(bot)

        mocked_active_event.end.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_end_event_does_not_end_active_event_that_does_not_match(
        self, bot, mocked_guild, mocked_active_event
    ):
        mocked_active_event.name = "event non-matching name"
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.end_event(bot)

        mocked_active_event.end.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_end_event_does_not_end_inactive_event(
        self, bot, mocked_guild, mocked_active_event
    ):
        mocked_active_event.status = EventStatus.scheduled
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.end_event(bot)

        mocked_active_event.end.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_end_event_with_non_configured_event_name(
        self, bot, mocked_guild, mocked_active_event
    ):
        when2(Plugin.get_cvar, "qlx_discord_ext_event_name").thenReturn(None)
        mocked_guild.scheduled_events.append(mocked_active_event)

        await event.end_event(bot)

        mocked_active_event.end.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_playing_activity_with_no_players_connected_ends_events(
        self, bot
    ):
        event.end_event = AsyncMock()
        connected_players()

        event.check_playing_activity(bot)

        event.end_event.assert_called_once_with(bot)

    @pytest.mark.asyncio
    async def test_check_playing_activity_creates_and_starts_event_when_player_connected(
        self, bot
    ):
        event.create_and_start_event = AsyncMock()
        connected_players(fake_player(1, "Dummy Player"))

        event.check_playing_activity(bot)

        event.create_and_start_event.assert_called_once_with(bot)

    @pytest.mark.asyncio
    async def test_bot_setup_called_with_wrong_intentions(self, bot):
        bot.intents = mock(spec=Intents)
        bot.intents.guild_scheduled_events = False
        with pytest.raises(ValueError) as exception:
            await event.setup(bot)
            assert_that(
                exception.value,
                equal_to("client needs guild_scheduled_events for this extension"),
            )

    @pytest.mark.asyncio
    async def test_bot_setup_called_with_right_intentions(self, bot):
        threading_mock = mock(spec=threading.Thread)
        threading_mock.start = mock()
        spy2(threading.Thread)
        when2(threading.Thread, target=any_).thenReturn(threading_mock)

        bot.intents = mock(spec=Intents)
        bot.intents.guild_scheduled_events = True

        await event.setup(bot)

        verify(threading).Thread(target=event.run_schedule)
        verify(threading_mock.start).__call__()
