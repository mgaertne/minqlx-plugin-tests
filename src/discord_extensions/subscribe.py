import asyncio
import threading
import time

# noinspection PyPackageRequirements
import schedule

# noinspection PyPackageRequirements
from discord import (
    ActivityType,
    app_commands,
    Color,
    Embed,
    Member,
)

# noinspection PyPackageRequirements
from discord.ext.commands import Cog, GroupCog

import minqlx
from minqlx import Plugin, NonexistentGameError
from minqlx.database import Redis

DISCORD_MAP_SUBSCRIPTION_KEY = "minqlx:discord:{}:subscribed_maps"
DISCORD_PLAYER_SUBSCRIPTION_KEY = "minqlx:discord:{}:subscribed_players"
DISCORD_MEMBER_SUBSCRIPTION_KEY = "minqlx:discord:{}:subscribed_members"
LONG_MAP_NAMES_KEY = "minqlx:maps:longnames"
LAST_USED_NAME_KEY = "minqlx:players:{}:last_used_name"


class SubscriberCog(Cog):
    subscribe_group = app_commands.Group(
        name="subscribe",
        guild_only=True,
        description="subscribe to maps, players, or members playing",
    )
    unsubscribe_group = app_commands.Group(
        name="unsubscribe",
        guild_only=True,
        description="unsubscribe from maps, players, or members",
    )

    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

        self.long_map_names_lookup = {}
        if self.db.exists(LONG_MAP_NAMES_KEY):
            self.long_map_names_lookup = self.db.hgetall(LONG_MAP_NAMES_KEY)

        self.installed_maps = []
        # noinspection PyProtectedMember
        if "maps_manager" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember,PyUnresolvedReferences
            self.installed_maps = Plugin._loaded_plugins["maps_manager"].installed_maps  # type: ignore
        # noinspection PyProtectedMember
        elif "maps" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember,PyUnresolvedReferences
            self.installed_maps = Plugin._loaded_plugins["maps"].logged_maps  # type: ignore

        self.formatted_installed_maps = {
            mapname: mapname for mapname in self.installed_maps
        }
        for mapname, long_map_name in self.long_map_names_lookup.items():
            if (
                mapname in self.installed_maps
                and long_map_name.lower() != mapname.lower()
            ):
                self.formatted_installed_maps[mapname] = f"{long_map_name} ({mapname})"

        self.known_players = self.gather_known_players()

        self.last_notified_map = None
        self.notified_steam_ids = []

        if not self.bot.intents.presences:
            self.subscribe_group.remove_command("member")
            self.unsubscribe_group.remove_command("member")
            self.bot.remove_listener(self.on_presence_update)

        super().__init__()

    def gather_known_players(self):
        returned = {}
        prefix = LAST_USED_NAME_KEY.rsplit("{", maxsplit=1)[0]
        suffix = LAST_USED_NAME_KEY.rsplit("}", maxsplit=1)[-1]
        for key in self.db.keys(LAST_USED_NAME_KEY.format("*")):
            steam_id_candidate = key.replace(prefix, "").replace(suffix, "")
            if not steam_id_candidate.isdigit():
                continue

            steam_id = int(steam_id_candidate)
            last_used_name = self.db.get(key)
            returned[steam_id] = Plugin.clean_text(last_used_name)

        return returned

    @subscribe_group.command(name="map", description="Get notified when your favorite maps are played")  # type: ignore
    @app_commands.describe(mapname="the name of the map to subscribe to")
    @app_commands.guild_only()
    async def subscribe_map(self, interaction, mapname: str):
        await self._subscribe_map(interaction, mapname)

    async def _subscribe_map(self, interaction, mapname):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        stripped_mapname = mapname.strip(" ")
        if stripped_mapname == "":
            reply_embed.description = "No mapname provided."
            await interaction.edit_original_response(embed=reply_embed)
            return

        if stripped_mapname not in self.installed_maps:
            reply_embed.description = f"Map `{stripped_mapname}` is not installed."
            await interaction.edit_original_response(embed=reply_embed)
            return

        db_return_value = self.db.sadd(
            DISCORD_MAP_SUBSCRIPTION_KEY.format(interaction.user.id), stripped_mapname
        )

        if not db_return_value:
            immediate_reply_message = (
                f"You already were subscribed to map changes for map "
                f"`{self.formatted_installed_maps[stripped_mapname]}`."
            )
        else:
            immediate_reply_message = (
                f"You have been subscribed to map changes for map "
                f"`{self.formatted_installed_maps[stripped_mapname]}`."
            )
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_maps = self.subscribed_maps_of(interaction.user.id)
        formatted_maps = "`, `".join(
            [self.format_mapname(mapname) for mapname in subscribed_maps]
        )
        reply_embed.description = (
            f"{immediate_reply_message}\n"
            f"You are currently subscribed to map changes for: `{formatted_maps}`"
        )
        await interaction.edit_original_response(embed=reply_embed)

    def subscribed_maps_of(self, user_id):
        return self.db.smembers(DISCORD_MAP_SUBSCRIPTION_KEY.format(user_id))

    def format_mapname(self, mapname):
        if mapname in self.formatted_installed_maps:
            return self.formatted_installed_maps[mapname]

        if mapname in self.long_map_names_lookup:
            return f"{self.long_map_names_lookup[mapname]} ({mapname})"

        return mapname

    @subscribe_map.autocomplete(name="mapname")
    async def subscribe_map_autocomplete(self, interaction, current):
        subscribed_maps = self.subscribed_maps_of(interaction.user.id)
        filtered_candidates = [
            mapname
            for mapname, formatted_long_name in self.formatted_installed_maps.items()
            if current.lower() in formatted_long_name.lower()
            and mapname not in subscribed_maps
        ]
        filtered_candidates.sort()

        return [
            app_commands.Choice(
                name=self.formatted_installed_maps[mapname], value=mapname
            )
            for mapname in filtered_candidates[:25]
        ]

    @subscribe_group.command(  # type: ignore
        name="player",
        description="Get notified when your favorite players joins the server",
    )
    @app_commands.describe(player="Name of the player you want to subscribe to")
    @app_commands.guild_only()
    async def subscribe_player(self, interaction, player: str):
        await self._subscribe_player(interaction, player)

    async def _subscribe_player(self, interaction, player):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        stripped_player_name = player.strip(" ")
        if stripped_player_name == "":
            reply_embed.description = "No player name provided."
            await interaction.edit_original_response(embed=reply_embed)
            return

        matching_players = self.find_matching_players(stripped_player_name)
        if len(matching_players) == 0:
            reply_embed.description = (
                f"No player matching player name `{stripped_player_name}` found."
            )
            await interaction.edit_original_response(embed=reply_embed)
            return

        if len(matching_players) > 1:
            matching_player_names = [
                self.formatted_last_used_name(steam_id) for steam_id in matching_players
            ]
            formatted_player_names = "`, `".join(matching_player_names)
            reply_embed.description = (
                f"More than one player matching your player name found. "
                f"Players matching `{stripped_player_name}` are:\n"
                f"`{formatted_player_names}`"
            )
            await interaction.edit_original_response(embed=reply_embed)
            return

        matching_steam_id = int(matching_players[0])
        db_return_value = self.db.sadd(
            DISCORD_PLAYER_SUBSCRIPTION_KEY.format(interaction.user.id),
            matching_steam_id,
        )

        last_used_name = self.formatted_last_used_name(matching_steam_id)
        if not db_return_value:
            immediate_reply_message = (
                f"You already were subscribed to player `{last_used_name}`."
            )
        else:
            immediate_reply_message = (
                f"You have been subscribed to player `{last_used_name}`."
            )
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_players = self.subscribed_players_of(interaction.user.id)
        formatted_players = "`, `".join(
            [
                self.formatted_last_used_name(subscribed_steam_id)
                for subscribed_steam_id in subscribed_players
            ]
        )
        reply_embed.description = (
            f"{immediate_reply_message}\n"
            f"You are currently subscribed to the following players: `{formatted_players}`"
        )
        await interaction.edit_original_response(embed=reply_embed)

    def find_matching_players(self, player):
        if player.isdigit() and int(player) in self.known_players:
            return [int(player)]

        matching_steam_ids = []
        for steam_id, player_name in self.known_players.items():
            if player.lower() in player_name.lower() or player in str(steam_id):
                matching_steam_ids.append(steam_id)

        return matching_steam_ids

    def formatted_last_used_name(self, steam_id):
        if not self.db.exists(LAST_USED_NAME_KEY.format(steam_id)):
            return str(steam_id)
        return Plugin.clean_text(
            self.db.get(LAST_USED_NAME_KEY.format(steam_id))
        ).replace("`", r"\`")

    def subscribed_players_of(self, user_id):
        player_subscriptions = self.db.smembers(
            DISCORD_PLAYER_SUBSCRIPTION_KEY.format(user_id)
        )
        return [int(player_steam_id) for player_steam_id in player_subscriptions]

    @subscribe_player.autocomplete(name="player")
    async def subscribe_player_autocomplete(self, interaction, current):
        subscribed_players = self.subscribed_players_of(interaction.user.id)
        filtered_candidates = [
            candidate_steam_id
            for candidate_steam_id in self.find_matching_players(current)
            if candidate_steam_id not in subscribed_players
        ]
        filtered_candidates.sort()

        return [
            app_commands.Choice(
                name=self.formatted_last_used_name(steam_id), value=str(steam_id)
            )
            for steam_id in filtered_candidates[:25]
        ]

    @subscribe_group.command(  # type: ignore
        name="member",
        description="Get notified when your favorite discord user starts playing",
    )
    @app_commands.describe(member="Discord user you want to subscribe to")
    @app_commands.guild_only()
    async def subscribe_member(self, interaction, member: Member):
        await self._subscribe_member(interaction, member)

    async def _subscribe_member(self, interaction, member):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        db_return_value = self.db.sadd(
            DISCORD_MEMBER_SUBSCRIPTION_KEY.format(interaction.user.id), member.id
        )

        if not db_return_value:
            immediate_reply_message = f"You already were subscribed to Quake Live activities of {member.mention}."
        else:
            immediate_reply_message = f"You have been subscribed to Quake Live activities of {member.mention}."
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_users = self.subscribed_users_of(interaction.user.id)
        formatted_users = ", ".join([user.mention for user in subscribed_users])
        reply_embed.description = (
            f"{immediate_reply_message}\n"
            f"You are currently subscribed to Quake Live activities of: {formatted_users}"
        )
        await interaction.edit_original_response(embed=reply_embed)

    def subscribed_users_of(self, user_id):
        subscribed_users = []
        for discord_str_id in self.db.smembers(
            DISCORD_MEMBER_SUBSCRIPTION_KEY.format(user_id)
        ):
            discord_id = int(discord_str_id)
            subscribed_user = self.bot.get_user(discord_id)
            if subscribed_user is None:
                continue
            subscribed_users.append(subscribed_user)

        return subscribed_users

    @unsubscribe_group.command(name="map", description="Stop getting notified about a map")  # type: ignore
    @app_commands.describe(mapname="the name of the map to subscribe from")
    @app_commands.guild_only()
    async def unsubscribe_map(self, interaction, mapname: str):
        await self._unsubscribe_map(interaction, mapname)

    async def _unsubscribe_map(self, interaction, mapname):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        stripped_mapname = mapname.strip(" ")
        if stripped_mapname == "":
            reply_embed.description = "No mapname provided."
            await interaction.edit_original_response(embed=reply_embed)
            return

        db_return_value = self.db.srem(
            DISCORD_MAP_SUBSCRIPTION_KEY.format(interaction.user.id), stripped_mapname
        )

        if not db_return_value:
            immediate_reply_message = (
                f"You were not subscribed to map changes for map "
                f"`{self.format_mapname(stripped_mapname)}`. "
            )
        else:
            immediate_reply_message = (
                f"You have been unsubscribed from map changes for map "
                f"`{self.format_mapname(stripped_mapname)}`. "
            )
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_maps = self.subscribed_maps_of(interaction.user.id)

        if len(subscribed_maps) == 0:
            reply_embed.description = f"{immediate_reply_message}\nYou are no longer subscribed to any map changes."
            await interaction.edit_original_response(embed=reply_embed)
            return

        formatted_maps = "`, `".join(
            [self.format_mapname(mapname) for mapname in subscribed_maps]
        )
        reply_embed.description = (
            f"{immediate_reply_message}\nYou are still subscribed to `{formatted_maps}`"
        )
        await interaction.edit_original_response(embed=reply_embed)

    @unsubscribe_map.autocomplete("mapname")
    async def unsubscribe_map_autocomplete(self, interaction, current):
        subscribed_maps = self.subscribed_maps_of(interaction.user.id)
        candidates = [
            mapname
            for mapname in subscribed_maps
            if current.lower() in self.format_mapname(mapname).lower()
        ]
        candidates.sort()

        return [
            app_commands.Choice(name=self.format_mapname(mapname), value=mapname)
            for mapname in candidates[:25]
        ]

    @unsubscribe_group.command(name="player", description="Stop getting notified about a player")  # type: ignore
    @app_commands.describe(player="Name of the player you want to unsubscribe from")
    @app_commands.guild_only()
    async def unsubscribe_player(self, interaction, player: str):
        await self._unsubscribe_player(interaction, player)

    async def _unsubscribe_player(self, interaction, player):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        stripped_player_name = player.strip(" ")
        if stripped_player_name == "":
            reply_embed.description = "No player name provided."
            await interaction.edit_original_response(embed=reply_embed)
            return

        matching_players = self.find_matching_players(stripped_player_name)
        if len(matching_players) == 0:
            reply_embed.description = (
                f"No player matching player name `{stripped_player_name}` found."
            )
            await interaction.edit_original_response(embed=reply_embed)
            return

        if len(matching_players) > 1:
            matching_player_names = [
                self.formatted_last_used_name(steam_id) for steam_id in matching_players
            ]
            formatted_player_names = "`, `".join(matching_player_names)
            reply_embed.description = (
                f"More than one player matching your player name found. "
                f"Players matching `{stripped_player_name}` are:\n"
                f"`{formatted_player_names}`"
            )
            await interaction.edit_original_response(embed=reply_embed)
            return

        matching_steam_id = int(matching_players[0])
        db_return_value = self.db.srem(
            DISCORD_PLAYER_SUBSCRIPTION_KEY.format(interaction.user.id),
            stripped_player_name,
        )

        last_used_name = self.formatted_last_used_name(matching_steam_id)
        if not db_return_value:
            immediate_reply_message = (
                f"You were not subscribed to player `{last_used_name}`."
            )
        else:
            immediate_reply_message = (
                f"You have been unsubscribed from player `{last_used_name}`."
            )
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_players = self.subscribed_players_of(interaction.user.id)
        formatted_players = "`, `".join(
            [
                self.formatted_last_used_name(subscribed_steam_id)
                for subscribed_steam_id in subscribed_players
            ]
        )

        if len(subscribed_players) == 0:
            reply_embed.description = f"{immediate_reply_message}\nYou are no longer subscribed to any players."
            await interaction.edit_original_response(embed=reply_embed)
            return

        reply_embed.description = (
            f"{immediate_reply_message}\n"
            f"You are currently subscribed to the following players: `{formatted_players}`"
        )
        await interaction.edit_original_response(embed=reply_embed)

    @unsubscribe_player.autocomplete("player")
    async def unsubscribe_player_autocomplete(self, interaction, current):
        subscribed_players = self.subscribed_players_of(interaction.user.id)

        candidates = [
            steam_id
            for steam_id in subscribed_players
            if current.lower() in self.formatted_last_used_name(steam_id).lower()
        ]
        candidates.sort()

        return [
            app_commands.Choice(
                name=self.formatted_last_used_name(steam_id), value=str(steam_id)
            )
            for steam_id in candidates[:25]
        ]

    @unsubscribe_group.command(name="member", description="Stop getting notified about a discord user")  # type: ignore
    @app_commands.describe(member="Discord user you want to unsubscribe from")
    @app_commands.guild_only()
    async def unsubscribe_member(self, interaction, member: Member):
        await self._unsubscribe_member(interaction, member)

    async def _unsubscribe_member(self, interaction, member):
        reply_embed = Embed(color=Color.blurple())
        await interaction.response.defer(thinking=True, ephemeral=True)
        db_return_value = self.db.srem(
            DISCORD_MEMBER_SUBSCRIPTION_KEY.format(interaction.user.id), member.id
        )

        if not db_return_value:
            immediate_reply_message = (
                f"You were not subscribed to Quake Live activities of {member.mention}."
            )
        else:
            immediate_reply_message = f"You have been unsubscribed from Quake Live activities of {member.mention}."
        reply_embed.description = immediate_reply_message
        await interaction.edit_original_response(embed=reply_embed)

        subscribed_users = self.subscribed_users_of(interaction.user.id)

        if len(subscribed_users) == 0:
            reply_embed.description = (
                f"{immediate_reply_message}\n"
                f"You are no longer subscribed to Quake Live activities of anyone."
            )
            await interaction.edit_original_response(embed=reply_embed)
            return

        formatted_users = ", ".join([user.mention for user in subscribed_users])
        reply_embed.description = (
            f"{immediate_reply_message}\n"
            f"You are still subscribed to Quake Live activities of {formatted_users}"
        )
        await interaction.edit_original_response(embed=reply_embed)

    async def notify_map_change(self, mapname):
        prefix = DISCORD_MAP_SUBSCRIPTION_KEY.split("{", maxsplit=1)[0]
        suffix = DISCORD_MAP_SUBSCRIPTION_KEY.rsplit("}", maxsplit=1)[-1]

        notifications = []
        for key in self.db.keys(DISCORD_MAP_SUBSCRIPTION_KEY.format("*")):
            if self.db.sismember(key, mapname):
                discord_id = int(key.replace(prefix, "").replace(suffix, ""))
                subscribed_discord_user = self.bot.get_user(discord_id)
                if subscribed_discord_user is None:
                    continue

                notifications.append(
                    subscribed_discord_user.send(
                        content=f"`{self.format_mapname(mapname)}`, one of your favourite maps has been loaded!"
                    )
                )

        await asyncio.gather(*notifications)

    async def notify_player_connected(self, player):
        prefix = DISCORD_PLAYER_SUBSCRIPTION_KEY.split("{", maxsplit=1)[0]
        suffix = DISCORD_PLAYER_SUBSCRIPTION_KEY.rsplit("}", maxsplit=1)[-1]

        notifications = []
        for key in self.db.keys(DISCORD_PLAYER_SUBSCRIPTION_KEY.format("*")):
            if self.db.sismember(key, player.steam_id):
                discord_id = int(key.replace(prefix, "").replace(suffix, ""))
                subscribed_discord_user = self.bot.get_user(discord_id)

                if subscribed_discord_user is None:
                    continue

                notifications.append(
                    subscribed_discord_user.send(
                        content=f"`{player.clean_name}`, one of your followed players, "
                        f"just connected to the server!"
                    )
                )

        await asyncio.gather(*notifications)

    async def check_subscriptions(self):
        notification_actions = []
        game = None
        try:  # noqa: SIM105
            game = minqlx.Game()
        except NonexistentGameError:
            pass

        if game is not None and game.map != self.last_notified_map:
            self.last_notified_map = game.map
            if self.last_notified_map is not None:
                notification_actions.append(
                    self.notify_map_change(self.last_notified_map)
                )

        players = Plugin.players()
        new_players = [
            player
            for player in players
            if player.steam_id not in self.notified_steam_ids
        ]
        for player in new_players:
            notification_actions.append(self.notify_player_connected(player))
        self.notified_steam_ids = [player.steam_id for player in players]
        await asyncio.gather(*notification_actions)

    # noinspection PyMethodMayBeStatic
    def find_relevant_activity(self, member):
        for activity in member.activities:
            if activity.type != ActivityType.playing:
                continue
            if activity.name is None or "Quake Live" not in activity.name:
                continue
            return activity

        return None

    @GroupCog.listener()
    async def on_presence_update(self, before, after):
        relevant_activity = self.find_relevant_activity(before)
        if relevant_activity is not None:
            return

        relevant_activity = self.find_relevant_activity(after)
        if relevant_activity is None:
            return

        prefix = DISCORD_MEMBER_SUBSCRIPTION_KEY.split("{", maxsplit=1)[0]
        suffix = DISCORD_MEMBER_SUBSCRIPTION_KEY.rsplit("}", maxsplit=1)[-1]

        notifications = []
        for key in self.db.keys(DISCORD_MEMBER_SUBSCRIPTION_KEY.format("*")):
            if self.db.sismember(key, str(after.id)):
                discord_id = int(key.replace(prefix, "").replace(suffix, ""))
                informed_user = self.bot.get_user(discord_id)
                if informed_user is None:
                    continue

                notifications.append(
                    informed_user.send(
                        content=f"{after.display_name}, a discord user you are subscribed to, "
                        f"just started playing Quake Live."
                    )
                )

        await asyncio.gather(*notifications)


def check_subscriptions(cog):
    cog.bot.loop.create_task(cog.check_subscriptions())


async def setup(bot):
    # noinspection PyTypeChecker
    subscriber_cog = SubscriberCog(bot, Redis("mydiscordbot"))
    await bot.add_cog(subscriber_cog)
    schedule.every(1).minute.do(check_subscriptions, subscriber_cog)
    threading.Thread(target=run_schedule).start()


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)
