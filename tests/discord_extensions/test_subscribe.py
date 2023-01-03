import threading

import pytest
import redis

# noinspection PyPackageRequirements
from discord import Intents, app_commands, Member, Activity, ActivityType
from hamcrest import (
    assert_that,
    equal_to,
    contains_string,
    has_entries,
    contains_inanyorder,
    not_,
    has_item,
)

# noinspection PyProtectedMember
from mockito import unstub, mock, patch, when, any_, verify

from minqlx_plugin_test import setup_cvars, connected_players
import minqlx
import minqlx.database
from minqlx import Plugin, Player

from discord_extensions import subscribe
from discord_extensions.subscribe import SubscriberCog


def assert_interaction_deferred_thinking(interaction):
    interaction.response.defer.assert_awaited_once_with(thinking=True, ephemeral=True)


def assert_interaction_response_description_matches(interaction, matcher, *, times=1):
    interaction.edit_original_response.assert_awaited()
    assert_that(interaction.edit_original_response.await_count, equal_to(times))
    assert_that(
        interaction.edit_original_response.await_args.kwargs["embed"].description,
        matcher,
    )


def setup_db_long_map_names(mocked_db, known_long_map_names):
    when(mocked_db).exists("minqlx:maps:longnames").thenReturn(True)
    when(mocked_db).hgetall("minqlx:maps:longnames").thenReturn(known_long_map_names)


def setup_db_players(mocked_db, known_users):
    for steam_id, name in known_users.items():
        when(mocked_db).exists(f"minqlx:players:{steam_id}:last_used_name").thenReturn(True)
        when(mocked_db).get(f"minqlx:players:{steam_id}:last_used_name").thenReturn(name)


class TestSubscribe:
    @pytest.fixture(name="no_presences_bot")
    def no_presences_bot(self, bot):
        bot.intents = mock(spec=Intents)
        bot.intents.presences = False
        yield bot

    @pytest.fixture(name="presences_aware_bot")
    def presences__aware_bot(self, bot):
        bot.intents = mock(spec=Intents)
        bot.intents.presences = True
        yield bot

    @pytest.fixture(name="mocked_db", autouse=True)
    def mocked_db(self):
        redis_mock = mock(spec=redis.StrictRedis)
        when(redis_mock).exists(any_).thenReturn(False)
        when(redis_mock).keys(any_).thenReturn([])
        when(redis_mock).sadd(any_, any_).thenReturn(True)
        when(redis_mock).srem(any_, any_).thenReturn(True)
        when(redis_mock).smembers(any_).thenReturn([])
        # noinspection PyPropertyAccess
        minqlx.database.Redis.r = redis_mock

        yield redis_mock

        unstub()

    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        setup_cvars({"qlx_redisAddress": "localhost", "qlx_redisDatabase": "minqlx"})

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_member_commands_are_removed_when_bot_intents_do_not_allow(self, no_presences_bot, mocked_db):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        subscribe_commands = [command.name for command in extension.subscribe_group.commands]
        # noinspection PyTypeChecker
        assert_that(subscribe_commands, not_(has_item("member")))  # type: ignore
        unsubscribe_commands = [command.name for command in extension.unsubscribe_group.commands]
        # noinspection PyTypeChecker
        assert_that(unsubscribe_commands, not_(has_item("member")))  # type: ignore
        verify(no_presences_bot).remove_listener(extension.on_presence_update)

    def test_member_commands_are_kept_when_bot_has_right_intents(self, presences_aware_bot, mocked_db):
        extension = SubscriberCog(presences_aware_bot, mocked_db)

        subscribe_commands = [command.name for command in extension.subscribe_group.commands]
        # noinspection PyTypeChecker
        assert_that(subscribe_commands, has_item("member"))
        unsubscribe_commands = [command.name for command in extension.unsubscribe_group.commands]
        # noinspection PyTypeChecker
        assert_that(unsubscribe_commands, has_item("member"))
        verify(presences_aware_bot, times=0).remove_listener(extension.on_presence_update)

    def test_long_map_names_gathered_from_db(self, no_presences_bot, mocked_db):
        setup_db_long_map_names(
            mocked_db,
            {"theatreofpain": "Theatre of Pain", "ra3azra1": "Industrial Rust"},
        )
        extension = SubscriberCog(no_presences_bot, mocked_db)

        assert_that(
            extension.long_map_names_lookup,
            has_entries(theatreofpain="Theatre of Pain", ra3azra1="Industrial Rust"),
        )

    def test_installed_maps_gathered_from_maps_manager_plugin(self, no_presences_bot, mocked_db):
        maps_plugin = mock(spec=Plugin)
        maps_plugin.installed_maps = ["ra3azra1", "campgrounds", "theatreofpain"]
        Plugin._loaded_plugins = {"maps_manager": maps_plugin}  # pylint: disable=W0212

        setup_db_long_map_names(
            mocked_db,
            {"theatreofpain": "Theatre of Pain", "ra3azra1": "Industrial Rust"},
        )
        extension = SubscriberCog(no_presences_bot, mocked_db)

        assert_that(
            extension.installed_maps,
            contains_inanyorder("ra3azra1", "campgrounds", "theatreofpain"),
        )
        # noinspection PyTypeChecker
        assert_that(
            extension.formatted_installed_maps,
            has_entries(
                ra3azra1="Industrial Rust (ra3azra1)",
                theatreofpain="Theatre of Pain (theatreofpain)",
                campgrounds="campgrounds",
            ),
        )

    def test_installed_maps_gathered_from_maps_plugin(self, no_presences_bot, mocked_db):
        maps_plugin = mock(spec=Plugin)
        maps_plugin.logged_maps = ["ra3azra1", "campgrounds", "theatreofpain"]
        Plugin._loaded_plugins = {"maps": maps_plugin}  # pylint: disable=W0212

        setup_db_long_map_names(
            mocked_db,
            {"theatreofpain": "Theatre of Pain", "ra3azra1": "Industrial Rust"},
        )
        extension = SubscriberCog(no_presences_bot, mocked_db)

        assert_that(
            extension.installed_maps,
            contains_inanyorder("ra3azra1", "campgrounds", "theatreofpain"),
        )
        # noinspection PyTypeChecker
        assert_that(
            extension.formatted_installed_maps,
            has_entries(
                ra3azra1="Industrial Rust (ra3azra1)",
                theatreofpain="Theatre of Pain (theatreofpain)",
                campgrounds="campgrounds",
            ),
        )

    def test_installed_maps_gathered_known_player_names_from_db(self, no_presences_bot, mocked_db):
        when(mocked_db).keys("minqlx:players:*:last_used_name").thenReturn(
            [
                "minqlx:players:123:last_used_name",
                "minqlx:players:456:last_used_name",
                "minqlx:players:misconfigured:last_used_name",
            ]
        )
        known_players = {123: "plainname", 456: "^1colored^5name^7"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)

        # noinspection PyTypeChecker
        assert_that(extension.known_players, has_entries({123: "plainname", 456: "coloredname"}))

    @pytest.mark.asyncio
    async def test_subscribe_map_with_no_provided_map(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._subscribe_map(interaction, "")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(interaction, equal_to("No mapname provided."))

    @pytest.mark.asyncio
    async def test_subscribe_map_with_a_not_installed_map(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._subscribe_map(interaction, "not_installed")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(interaction, equal_to("Map `not_installed` is not installed."))

    @pytest.mark.asyncio
    async def test_subscribe_map_user_is_subscribed_to_map_changes(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["thunderstruck"]
        extension.formatted_installed_maps["thunderstruck"] = "thunderstruck"

        await extension._subscribe_map(interaction, "thunderstruck")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been subscribed to map changes for map `thunderstruck`"),
            times=2,
        )
        verify(mocked_db).sadd("minqlx:discord:42:subscribed_maps", "thunderstruck")

    @pytest.mark.asyncio
    async def test_subscribe_map_with_long_mapname(self, no_presences_bot, mocked_db, interaction, user):
        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn(["theatreofpain", "ra3azra1", "ra3goetz1"])

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["theatreofpain"]
        extension.formatted_installed_maps = {"theatreofpain": "Theatre of Pain"}
        extension.long_map_names_lookup = {"ra3azra1": "Industrial Rust"}

        await extension._subscribe_map(interaction, "theatreofpain")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("`Theatre of Pain`, `Industrial Rust (ra3azra1)`, `ra3goetz1`"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_map_user_already_subscribed_to_map_changes(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        when(mocked_db).sadd(any_, "thunderstruck").thenReturn(False)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["thunderstruck"]
        extension.formatted_installed_maps["thunderstruck"] = "thunderstruck"

        await extension._subscribe_map(interaction, "thunderstruck")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You already were subscribed to map changes for map `thunderstruck`"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_map_autocomplete_shows_matching_installed_maps(
        self, no_presences_bot, user, interaction, mocked_db
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["campgrounds"]
        extension.formatted_installed_maps["campgrounds"] = "campgrounds"

        result = await extension.subscribe_map_autocomplete(interaction, "camp")

        assert_that(len(result), equal_to(1))
        assert_that(isinstance(result[0], app_commands.Choice), equal_to(True))
        assert_that(result[0].name, equal_to("campgrounds"))
        assert_that(result[0].value, equal_to("campgrounds"))

    @pytest.mark.asyncio
    async def test_subscribe_player_with_no_provided_player(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._subscribe_player(interaction, "")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(interaction, equal_to("No player name provided."))

    @pytest.mark.asyncio
    async def test_subscribe_player_with_no_matching_player_name(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._subscribe_player(interaction, "unknownplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            equal_to("No player matching player name `unknownplayer` found."),
        )

    @pytest.mark.asyncio
    async def test_subscribe_player_with_more_than_one_matching_player_name(
        self, no_presences_bot, mocked_db, interaction
    ):
        known_players = {123: "matchedplayer", 456: "anothermatchedplayer"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._subscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            equal_to(
                "More than one player matching your player name found. "
                "Players matching `matchedplayer` are:\n`matchedplayer`, `anothermatchedplayer`"
            ),
        )

    @pytest.mark.asyncio
    async def test_subscribe_player_user_is_subscribed_to_player_connecting_to_server(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        known_players = {123: "matchedplayer"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._subscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been subscribed to player `matchedplayer`"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_player_user_was_already_subscribed_to_player(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        known_players = {123: "matchedplayer", 456: "anotherplayer"}
        setup_db_players(mocked_db, known_players)
        when(mocked_db).sadd(any_, any_).thenReturn(False)
        when(mocked_db).smembers(any_).thenReturn([123, 456])

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._subscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string(
                "You already were subscribed to player `matchedplayer`.\n"
                "You are currently subscribed to the following players: `matchedplayer`, `anotherplayer`"
            ),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_player_user_is_subscribed_to_player_by_steam_id(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players[123] = "matchedplayer"

        await extension._subscribe_player(interaction, "123")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been subscribed to player `123`"),
            times=2,
        )
        verify(mocked_db).sadd("minqlx:discord:42:subscribed_players", 123)

    @pytest.mark.asyncio
    async def test_subscribe_player_autocomplete_with_no_subscribed_players(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)

        subscribed_players = await extension.subscribe_player_autocomplete(interaction, "matchedplayer")

        assert_that(subscribed_players, equal_to([]))

    @pytest.mark.asyncio
    async def test_subscribe_player_autocomplete_with_matching_subscribed_players(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn([])
        known_players = {123: "matchedplayer1", 456: "matchedplayer2"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        subscribed_players = await extension.subscribe_player_autocomplete(interaction, "matchedplayer")

        assert_that(len(subscribed_players), equal_to(2))
        assert_that(subscribed_players[0].value, equal_to("123"))
        assert_that(subscribed_players[0].name, equal_to("matchedplayer1"))
        assert_that(subscribed_players[1].value, equal_to("456"))
        assert_that(subscribed_players[1].name, equal_to("matchedplayer2"))

    @pytest.mark.asyncio
    async def test_subscribe_member_subscribes_to_discord_user_playing(
        self, presences_aware_bot, mocked_db, interaction, user
    ):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@SubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        interaction.user = user

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._subscribe_member(interaction, member)  # pylint: disable=W0212

        verify(mocked_db).sadd("minqlx:discord:42:subscribed_members", 21)
        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been subscribed to Quake Live activities of <@SubscribedMember>."),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_member_already_subscribed(self, presences_aware_bot, mocked_db, interaction, user):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@SubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        interaction.user = user

        when(mocked_db).sadd(any_, any_).thenReturn(False)

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._subscribe_member(interaction, member)  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You already were subscribed to Quake Live activities of <@SubscribedMember>."),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_subscribe_member_informs_user_of_other_member_subscriptions(
        self, presences_aware_bot, mocked_db, interaction, user
    ):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@SubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        other_member = mock(spec=Member)
        other_member.id = 11
        other_member.mention = "<@OtherSubscribedMember>"
        when(presences_aware_bot).get_user(11).thenReturn(other_member)

        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn([21, 11, 666])

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._subscribe_member(interaction, member)  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string(
                "You are currently subscribed to Quake Live activities of: "
                "<@SubscribedMember>, <@OtherSubscribedMember>"
            ),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_map_with_no_provided_map(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._unsubscribe_map(interaction, "")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(interaction, equal_to("No mapname provided."))

    @pytest.mark.asyncio
    async def test_unsubscribe_map_user_is_unsubscribed_from_map_changes(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["thunderstruck"]
        extension.formatted_installed_maps["thunderstruck"] = "thunderstruck"

        await extension._unsubscribe_map(interaction, "thunderstruck")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been unsubscribed from map changes for map `thunderstruck`"),
            times=2,
        )
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You are no longer subscribed to any map changes."),
            times=2,
        )
        verify(mocked_db).srem("minqlx:discord:42:subscribed_maps", "thunderstruck")

    @pytest.mark.asyncio
    async def test_unsubscribe_map_with_long_mapname(self, no_presences_bot, mocked_db, interaction, user):
        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn(["ra3azra1", "ra3goetz1"])

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["theatreofpain"]
        extension.formatted_installed_maps = {"theatreofpain": "Theatre of Pain"}
        extension.long_map_names_lookup = {"ra3azra1": "Industrial Rust"}

        await extension._unsubscribe_map(interaction, "theatreofpain")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You are still subscribed to `Industrial Rust (ra3azra1)`, `ra3goetz1`"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_map_user_already_unsubscribed_from_map_changes(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        when(mocked_db).srem(any_, "thunderstruck").thenReturn(False)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["thunderstruck"]
        extension.formatted_installed_maps["thunderstruck"] = "thunderstruck"

        await extension._unsubscribe_map(interaction, "thunderstruck")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You were not subscribed to map changes for map `thunderstruck`"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_map_autocomplete_shows_matching_subscribed_maps(
        self, no_presences_bot, user, interaction, mocked_db
    ):
        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn(["ra3azra1", "campgrounds", "ra3azra1a"])

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.installed_maps = ["ra3azra1", "ra3azra1a", "ra3azra1b", "campgrounds"]
        extension.formatted_installed_maps = {
            "ra3azra1": "Industrial Rust (ra3azra1)",
            "ra3azra1a": "Born Again (ra3azra1a)",
            "ra3azra1b": "Hand of Doom (ra3azra1b))",
            "campgrounds": "Camgrounds",
        }

        result = await extension.unsubscribe_map_autocomplete(interaction, "ra3az")

        assert_that(len(result), equal_to(2))
        assert_that(isinstance(result[0], app_commands.Choice), equal_to(True))
        assert_that(result[0].name, equal_to("Industrial Rust (ra3azra1)"))
        assert_that(result[0].value, equal_to("ra3azra1"))
        assert_that(isinstance(result[1], app_commands.Choice), equal_to(True))
        assert_that(result[1].name, equal_to("Born Again (ra3azra1a)"))
        assert_that(result[1].value, equal_to("ra3azra1a"))

    @pytest.mark.asyncio
    async def test_unsubscribe_player_with_no_provided_player(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._unsubscribe_player(interaction, "")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(interaction, equal_to("No player name provided."))

    @pytest.mark.asyncio
    async def test_unsubscribe_player_with_no_matching_player_name(self, no_presences_bot, mocked_db, interaction):
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension._unsubscribe_player(interaction, "unknownplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            equal_to("No player matching player name `unknownplayer` found."),
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_player_with_more_than_one_matching_player_name(
        self, no_presences_bot, mocked_db, interaction
    ):
        known_players = {123: "matchedplayer", 456: "anothermatchedplayer"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._unsubscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            equal_to(
                "More than one player matching your player name found. "
                "Players matching `matchedplayer` are:\n`matchedplayer`, `anothermatchedplayer`"
            ),
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_player_user_is_subscribed_to_player_connecting_to_server(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        known_players = {123: "matchedplayer"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._unsubscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been unsubscribed from player `matchedplayer`"),
            times=2,
        )
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You are no longer subscribed to any players."),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_player_user_was_already_subscribed_to_player(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        known_players = {123: "matchedplayer", 456: "anotherplayer"}
        setup_db_players(mocked_db, known_players)
        when(mocked_db).srem(any_, any_).thenReturn(False)
        when(mocked_db).smembers(any_).thenReturn([456])

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        await extension._unsubscribe_player(interaction, "matchedplayer")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string(
                "You were not subscribed to player `matchedplayer`.\n"
                "You are currently subscribed to the following players: `anotherplayer`"
            ),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_player_user_is_subscribed_to_player_by_steam_id(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players[123] = "matchedplayer"

        await extension._unsubscribe_player(interaction, "123")  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been unsubscribed from player `123`"),
            times=2,
        )
        verify(mocked_db).srem("minqlx:discord:42:subscribed_players", "123")

    @pytest.mark.asyncio
    async def test_unsubscribe_player_autocomplete_with_no_subscribed_players(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        extension = SubscriberCog(no_presences_bot, mocked_db)

        unsubscribed_players = await extension.unsubscribe_player_autocomplete(interaction, "matchedplayer")

        assert_that(unsubscribed_players, equal_to([]))

    @pytest.mark.asyncio
    async def test_unsubscribe_player_autocomplete_with_matching_subscribed_players(
        self, no_presences_bot, mocked_db, interaction, user
    ):
        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn([123, 456])
        known_players = {123: "matchedplayer1", 456: "matchedplayer2"}
        setup_db_players(mocked_db, known_players)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.known_players = known_players

        unsubscribed_players = await extension.unsubscribe_player_autocomplete(interaction, "matchedplayer")

        assert_that(len(unsubscribed_players), equal_to(2))
        assert_that(unsubscribed_players[0].value, equal_to("123"))
        assert_that(unsubscribed_players[0].name, equal_to("matchedplayer1"))
        assert_that(unsubscribed_players[1].value, equal_to("456"))
        assert_that(unsubscribed_players[1].name, equal_to("matchedplayer2"))

    @pytest.mark.asyncio
    async def test_unsubscribe_member_subscribes_to_discord_user_playing(
        self, presences_aware_bot, mocked_db, interaction, user
    ):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@UnsubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        interaction.user = user

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._unsubscribe_member(interaction, member)  # pylint: disable=W0212

        verify(mocked_db).srem("minqlx:discord:42:subscribed_members", 21)
        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You have been unsubscribed from Quake Live activities of <@UnsubscribedMember>."),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_member_already_unsubscribed(self, presences_aware_bot, mocked_db, interaction, user):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@UnsubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        interaction.user = user

        when(mocked_db).srem(any_, any_).thenReturn(False)

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._unsubscribe_member(interaction, member)  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You were not subscribed to Quake Live activities of <@UnsubscribedMember>."),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_member_informs_user_of_other_member_subscriptions(
        self, presences_aware_bot, mocked_db, interaction, user
    ):
        member = mock(spec=Member)
        member.id = 21
        member.mention = "<@UnsubscribedMember>"
        when(presences_aware_bot).get_user(21).thenReturn(member)

        other_member = mock(spec=Member)
        other_member.id = 11
        other_member.mention = "<@OtherSubscribedMember>"
        when(presences_aware_bot).get_user(11).thenReturn(other_member)

        interaction.user = user

        when(mocked_db).smembers(any_).thenReturn([11, 666])

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension._unsubscribe_member(interaction, member)  # pylint: disable=W0212

        assert_interaction_deferred_thinking(interaction)
        assert_interaction_response_description_matches(
            interaction,
            contains_string("You are still subscribed to Quake Live activities of <@OtherSubscribedMember>"),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_notify_map_change(self, no_presences_bot, mocked_db, user):
        when(no_presences_bot).get_user(user.id).thenReturn(user)

        other_member = mock(spec=Member)
        other_member.id = 21
        when(no_presences_bot).get_user(other_member.id).thenReturn(other_member)

        when(mocked_db).keys("minqlx:discord:*:subscribed_maps").thenReturn(
            [
                "minqlx:discord:21:subscribed_maps",
                "minqlx:discord:42:subscribed_maps",
                "minqlx:discord:666:subscribed_maps",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:666:subscribed_maps", "overkill").thenReturn(True)
        when(mocked_db).sismember("minqlx:discord:42:subscribed_maps", "overkill").thenReturn(True)
        when(mocked_db).sismember("minqlx:discord:21:subscribed_maps", "overkill").thenReturn(False)
        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension.notify_map_change("overkill")

        user.send.assert_awaited_once_with(content="`overkill`, one of your favourite maps has been loaded!")

    @pytest.mark.asyncio
    async def test_notify_player_connected(self, no_presences_bot, mocked_db, user):
        when(no_presences_bot).get_user(user.id).thenReturn(user)

        connected_player = mock(spec=Player)
        connected_player.steam_id = 123
        connected_player.clean_name = "ConnectedPlayer"

        when(mocked_db).keys("minqlx:discord:*:subscribed_players").thenReturn(
            [
                "minqlx:discord:42:subscribed_players",
                "minqlx:discord:21:subscribed_players",
                "minqlx:discord:666:subscribed_players",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:666:subscribed_players", 123).thenReturn(True)
        when(mocked_db).sismember("minqlx:discord:42:subscribed_players", 123).thenReturn(True)
        when(mocked_db).sismember("minqlx:discord:21:subscribed_players", 123).thenReturn(False)

        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension.notify_player_connected(connected_player)

        user.send.assert_awaited_once_with(
            content="`ConnectedPlayer`, one of your followed players, just connected to the server!"
        )

    @pytest.mark.asyncio
    async def test_check_subscriptions_no_game_running(self, no_presences_bot, mocked_db, no_minqlx_game, user):
        when(no_presences_bot).get_user(user.id).thenReturn(user)

        when(mocked_db).keys("minqlx:discord:*:subscribed_maps").thenReturn(
            [
                "minqlx:discord:42:subscribed_maps",
            ]
        )
        connected_players()

        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension.check_subscriptions()

        assert_that(user.send.await_count, equal_to(0))

    @pytest.mark.asyncio
    async def test_check_subscriptions_map_already_notified(self, no_presences_bot, mocked_db, game_in_warmup, user):
        when(no_presences_bot).get_user(user.id).thenReturn(user)

        when(mocked_db).keys("minqlx:discord:*:subscribed_maps").thenReturn(
            [
                "minqlx:discord:42:subscribed_maps",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:42:subscribed_maps", game_in_warmup.map).thenReturn(True)
        connected_players()

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.last_notified_map = game_in_warmup.map

        await extension.check_subscriptions()

        assert_that(user.send.await_count, equal_to(0))

    @pytest.mark.asyncio
    async def test_check_subscriptions_informs_about_favorite_map(
        self, no_presences_bot, mocked_db, game_in_warmup, user
    ):
        when(no_presences_bot).get_user(user.id).thenReturn(user)

        when(mocked_db).keys("minqlx:discord:*:subscribed_maps").thenReturn(
            [
                "minqlx:discord:42:subscribed_maps",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:42:subscribed_maps", game_in_warmup.map).thenReturn(True)
        connected_players()

        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension.check_subscriptions()

        user.send.assert_awaited_once_with(content="`campgrounds`, one of your favourite maps has been loaded!")

    @pytest.mark.asyncio
    async def test_check_subscriptions_informs_about_player_connected(
        self, no_presences_bot, mocked_db, game_in_warmup, user
    ):
        new_player = mock(spec=Player)
        new_player.steam_id = 123
        new_player.clean_name = "newplayer"

        when(no_presences_bot).get_user(user.id).thenReturn(user)

        when(mocked_db).keys("minqlx:discord:*:subscribed_players").thenReturn(
            [
                "minqlx:discord:42:subscribed_players",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:42:subscribed_players", new_player.steam_id).thenReturn(True)
        connected_players(new_player)

        extension = SubscriberCog(no_presences_bot, mocked_db)

        await extension.check_subscriptions()

        user.send.assert_awaited_once_with(
            content="`newplayer`, one of your followed players, just connected to the server!"
        )

    @pytest.mark.asyncio
    async def test_check_subscriptions_player_already_informed(self, no_presences_bot, mocked_db, game_in_warmup, user):
        new_player = mock(spec=Player)
        new_player.steam_id = 123
        new_player.clean_name = "newplayer"

        when(no_presences_bot).get_user(user.id).thenReturn(user)

        when(mocked_db).keys("minqlx:discord:*:subscribed_players").thenReturn(
            [
                "minqlx:discord:42:subscribed_players",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:42:subscribed_players", new_player.steam_id).thenReturn(True)
        connected_players(new_player)

        extension = SubscriberCog(no_presences_bot, mocked_db)
        extension.notified_steam_ids = [new_player.steam_id]

        await extension.check_subscriptions()

        assert_that(user.send.await_count, equal_to(0))

    def test_find_relevant_activitiy_with_no_activity(self, presences_aware_bot, mocked_db):
        member = mock(spec=Member)
        member.activities = []
        extension = SubscriberCog(presences_aware_bot, mocked_db)

        activities = extension.find_relevant_activity(member)

        assert_that(activities, equal_to(None))

    def test_find_relevant_activitiy_with_irrelevant_activity(self, presences_aware_bot, mocked_db):
        member = mock(spec=Member)
        member.activities = [
            Activity(type=ActivityType.listening),
            Activity(type=ActivityType.playing, name="Doom Eternal"),
            Activity(type=ActivityType.playing, name=None),
        ]
        extension = SubscriberCog(presences_aware_bot, mocked_db)

        activities = extension.find_relevant_activity(member)

        assert_that(activities, equal_to(None))

    def test_find_relevant_activitiy_finds_quakelive_activity(self, presences_aware_bot, mocked_db):
        member = mock(spec=Member)
        quakelive_activitiy = Activity(type=ActivityType.playing, name="Quake Live")
        member.activities = [
            Activity(type=ActivityType.listening),
            quakelive_activitiy,
            Activity(type=ActivityType.playing, name=None),
        ]
        extension = SubscriberCog(presences_aware_bot, mocked_db)

        activities = extension.find_relevant_activity(member)

        assert_that(activities, equal_to(quakelive_activitiy))

    @pytest.mark.asyncio
    async def test_on_presence_update_member_was_playing_before(self, presences_aware_bot, mocked_db, user):
        before_member = mock(spec=Member)
        before_member.id = 21
        before_member.activities = [Activity(type=ActivityType.playing, name="Quake Live")]

        when(mocked_db).keys("minqlx:discord:*:subscribed_members").thenReturn(["minqlx:discord:42:subscribed_members"])
        when(mocked_db).sismember("minqlx:discord:42:subscribed_members", 21).thenReturn(True)

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension.on_presence_update(before_member, before_member)

        assert_that(user.send.await_count, equal_to(0))

    @pytest.mark.asyncio
    async def test_on_presence_update_member_is_not_playing_after(self, presences_aware_bot, mocked_db, user):
        after_member = mock(spec=Member)
        after_member.id = 21
        after_member.activities = []

        when(mocked_db).keys("minqlx:discord:*:subscribed_members").thenReturn(["minqlx:discord:42:subscribed_members"])
        when(mocked_db).sismember("minqlx:discord:42:subscribed_members", 21).thenReturn(True)

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension.on_presence_update(after_member, after_member)

        assert_that(user.send.await_count, equal_to(0))

    @pytest.mark.asyncio
    async def test_on_presence_update_member_just_started_playing(self, presences_aware_bot, mocked_db, user):
        before_member = mock(spec=Member)
        before_member.id = 21
        before_member.activities = []

        after_member = mock(spec=Member)
        after_member.id = 21
        after_member.display_name = "PlayingMember"
        after_member.activities = [Activity(type=ActivityType.playing, name="Quake Live")]

        when(mocked_db).keys("minqlx:discord:*:subscribed_members").thenReturn(
            [
                "minqlx:discord:42:subscribed_members",
                "minqlx:discord:666:subscribed_members",
            ]
        )
        when(mocked_db).sismember("minqlx:discord:42:subscribed_members", "21").thenReturn(True)
        when(mocked_db).sismember("minqlx:discord:666:subscribed_members", "21").thenReturn(True)

        when(presences_aware_bot).get_user(user.id).thenReturn(user)

        extension = SubscriberCog(presences_aware_bot, mocked_db)

        await extension.on_presence_update(before_member, after_member)

        user.send.assert_awaited_once_with(
            content="PlayingMember, a discord user you are subscribed to, just started playing Quake Live."
        )

    @pytest.mark.asyncio
    async def test_bot_setup_called(self, no_presences_bot):
        thread_nock = mock(spec=threading.Thread)
        when(thread_nock).start().thenReturn()
        patch(threading.Thread, lambda target: thread_nock)

        await subscribe.setup(no_presences_bot)

        no_presences_bot.add_cog.assert_awaited_once()
        assert_that(
            isinstance(no_presences_bot.add_cog.call_args.args[0], SubscriberCog),
            equal_to(True),
        )
