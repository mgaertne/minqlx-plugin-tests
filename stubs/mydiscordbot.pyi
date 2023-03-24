from typing import TYPE_CHECKING
from threading import Thread

# noinspection PyPackageRequirements
from discord.ext.commands import Bot, DefaultHelpCommand

from minqlx import Plugin, Player, AbstractChannel

if TYPE_CHECKING:
    from logging import Logger

    # noinspection PyPackageRequirements
    from discord import (
        Message as Message,
        Member,
        VoiceChannel,
        StageChannel,
        ForumChannel,
        TextChannel,
        CategoryChannel,
        DMChannel,
        PartialMessageable,
        GroupChannel,
        User,
    )

    # noinspection PyPackageRequirements
    from discord.ext.commands import Context

    from minqlx import Game as minqlxGame, GameEndData

plugin_version: str

# noinspection PyPep8Naming
class mydiscordbot(Plugin):
    discord_message_filters: set[str]
    discord: SimpleAsyncDiscord
    def __init__(self, discord_client: SimpleAsyncDiscord | None = ...) -> None: ...
    def version_information(self) -> str: ...
    def handle_plugin_unload(self, plugin: Plugin | str) -> None: ...
    @staticmethod
    def game_status_information(game: minqlxGame) -> str: ...
    @staticmethod
    def get_game_info(game: minqlxGame) -> str: ...
    @staticmethod
    def player_data() -> str: ...
    @staticmethod
    def team_data(player_list: list[Player], limit: int | None = ...) -> str: ...
    def is_filtered_message(self, msg: str) -> bool: ...
    def handle_ql_chat(
        self, player: Player, msg: str, channel: AbstractChannel
    ) -> None: ...
    def handle_player_connect(self, player: Player) -> None: ...
    def handle_player_disconnect(self, player: Player, reason: str) -> None: ...
    def handle_map(self, mapname: str, _factory: str) -> None: ...
    def handle_vote_started(
        self, caller: Player | None, vote: str, args: str
    ) -> None: ...
    def handle_vote_ended(
        self, votes: tuple[int, int], _vote: str, _args: str, passed: bool
    ) -> None: ...
    def handle_game_countdown_or_end(
        self, *_args: GameEndData, **_kwargs: str
    ) -> None: ...
    def cmd_discord(
        self, player: Player, msg: list[str], _channel: AbstractChannel
    ) -> int: ...
    def cmd_discordbot(
        self, _player: Player, msg: list[str], channel: AbstractChannel
    ) -> int: ...
    def connect_discord(self) -> None: ...
    def disconnect_discord(self) -> None: ...

class MinqlxHelpCommand(DefaultHelpCommand):
    def __init__(self) -> None: ...
    def get_ending_note(self) -> str: ...
    async def send_error_message(self, error: str) -> None: ...

class SimpleAsyncDiscord(Thread):
    version_information: str
    logger: Logger
    discord: Bot | None
    discord_bot_token: str
    discord_application_id: str
    discord_relay_channel_ids: set[int]
    discord_relay_team_chat_channel_ids: set[int]
    discord_triggered_channel_ids: set[int]
    discord_triggered_channel_message_prefix: str
    discord_command_prefix: str
    discord_help_enabled: bool
    discord_version_enabled: bool
    discord_message_prefix: str
    discord_show_relay_channel_names: bool
    discord_replace_relayed_mentions: bool
    discord_replace_triggered_mentions: bool
    def __init__(self, version_information: str, logger: Logger) -> None: ...
    @staticmethod
    def setup_extended_logger() -> None: ...
    @staticmethod
    def int_set(string_set: set[str] | None) -> set[int]: ...
    def status(self) -> str: ...
    def run(self) -> None: ...
    def initialize_bot(self, discord_bot: Bot) -> None: ...
    async def version(
        self, ctx: Context[Bot], *_args: list, **_kwargs: dict
    ) -> None: ...
    def _format_message_to_quake(
        self,
        channel: (
            (TextChannel | VoiceChannel | Thread | DMChannel | PartialMessageable)
            | GroupChannel
        ),
        author: Member | User,
        content: str,
    ) -> str: ...
    async def on_ready(self) -> None: ...
    async def on_message(self, message: Message) -> None: ...
    async def on_command_error(
        self, exception: Exception, ctx: Context[Bot]
    ) -> None: ...
    def is_discord_logged_in(self) -> bool: ...
    def stop(self) -> None: ...
    def relay_message(self, msg: str) -> None: ...
    def send_to_discord_channels(
        self, channel_ids: set[str] | set[int], content: str
    ) -> None: ...
    def relay_chat_message(
        self, player: Player, channel: str, message: str
    ) -> None: ...
    def relay_team_chat_message(
        self, player: Player, channel: str, message: str
    ) -> None: ...
    def replace_user_mentions(
        self, message: str, player: Player | None = ...
    ) -> str: ...
    @staticmethod
    def find_user_that_matches(
        match: str, member_list: list[Member], player: Player | None = ...
    ) -> Member | None: ...
    def replace_channel_mentions(
        self, message: str, player: Player | None = ...
    ) -> str: ...
    @staticmethod
    def find_channel_that_matches(
        match: str,
        channel_list: list[
            VoiceChannel | StageChannel | ForumChannel | TextChannel | CategoryChannel
        ],
        player: Player | None = ...,
    ) -> (
        VoiceChannel
        | StageChannel
        | ForumChannel
        | TextChannel
        | CategoryChannel
        | None
    ): ...
    def triggered_message(self, player: Player, message: str) -> None: ...
