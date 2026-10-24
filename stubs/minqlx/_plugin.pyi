from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    from logging import Logger
    from typing import (
        Callable,
        ClassVar,
        Iterable,
        Literal,
        Mapping,
        Type,
        TypedDict,
    )

    from minqlx import (
        AbstractChannel,
        CancellableEventReturn,
        Command,
        Game,
        Player,
        UncancellableEventReturn,
        UserInfo,
    )
    from minqlx.database import Redis

class PlayerSummaryData(TypedDict):
    NAME: str
    STEAM_ID: str
    TEAM: int

class GameStartData(TypedDict):
    CAPTURE_LIMIT: int
    FACTORY: str
    FACTORY_TITLE: str
    FRAG_LIMIT: int
    GAME_TYPE: str
    INFECTED: int
    INSTAGIB: int
    MAP: str
    MATCH_GUID: str
    MERCY_LIMIT: int
    PLAYERS: list[PlayerSummaryData]
    QUADHOG: int
    ROUND_LIMIT: int
    SCORE_LIMIT: int
    SERVER_TITLE: str
    TIME_LIMIT: int
    TRAINING: int

class GameEndData(TypedDict):
    ABORTED: bool
    CAPTURE_LIMIT: int
    EXIT_MSG: str
    FACTORY: str
    FACTORY_TITLE: str
    FIRST_SCORER: str
    FRAG_LIMIT: int
    GAME_LENGTH: int
    GAME_TYPE: str
    INFECTED: int
    INSTAGIB: int
    LAST_LEAD_CHANGE_TIME: int
    LAST_SCORER: str
    LAST_TEAMSCORER: str
    MAP: str
    MATCH_GUID: str
    MERCY_LIMIT: int
    QUADHOG: int
    RESTARTED: int
    ROUND_LIMIT: int
    SCORE_LIMIT: int
    SERVER_TITLE: str
    TIME_LIMIT: int
    TRAINING: int
    TSCORE0: int
    TSCORE1: int

class RoundEndData(TypedDict):
    MATCH_GUID: str
    ROUND: int
    TEAM_WON: Literal["RED", "BLUE", "DRAW"]
    TIME: int
    WARMUP: bool

class Vector(TypedDict):
    x: float
    y: float
    z: float

PowerUps = Literal["QUAD", "BATTLESUIT", "HASTE", "INVISIBILITY", "REGENERATION", "INVULNERABILITY"]
Holdable = Literal["TELEPORTER", "MEDKIT", "FLIGHT", "KAMIKAZE", "PORTAL", "INVULNERABILITY"]
Weapon = Literal[
    "GAUNTLET",
    "MACHINEGUN",
    "SHOTGUN",
    "GRENADE",
    "ROCKET",
    "LIGHTNING",
    "RAILGUN",
    "PLASMA",
    "BFG",
    "GRAPPLE",
    "NAIL",
    "PROXIMITY",
    "CHAINGUN",
    "HMG",
    "HANDS",
]

class PlayerData(TypedDict):
    AIRBORNE: bool
    AMMO: int
    ARMOR: int
    BOT: bool
    BOT_SKILL: int | None
    HEALTH: int
    HOLDABLE: Holdable | None
    NAME: str
    POSITION: Vector
    POWERUPS: list[PowerUps] | None
    SPEED: float
    STEAM_ID: str
    SUBMERGED: bool
    TEAM: int
    VIEW: Vector
    WEAPON: Weapon

MeansOfDeath = Literal[
    "UNKNOWN",
    "SHOTGUN",
    "GAUNTLET",
    "MACHINEGUN",
    "GRENADE",
    "GRENADE_SPLASH",
    "ROCKET",
    "ROCKET_SPLASH",
    "PLASMA",
    "PLASMA_SPLASH",
    "RAILGUN",
    "LIGHTNING",
    "BFG",
    "BFG_SPLASH",
    "WATER",
    "SLIME",
    "LAVA",
    "CRUSH",
    "TELEFRAG",
    "FALLING",
    "SUICIDE",
    "TARGET_LASER",
    "HURT",
    "NAIL",
    "CHAINGUN",
    "PROXIMITY_MINE",
    "KAMIKAZE",
    "JUICED",
    "GRAPPLE",
    "SWITCHTEAM",
    "THAW",
    "LIGHTNING_DISCHARGE",
    "HMG",
    "RAILGUN_HEADSHOT",
]

class KillData(TypedDict):
    KILLER: PlayerData
    VICTIM: PlayerData
    MATCH_GUID: str
    MOD: MeansOfDeath
    OTHER_TEAM_ALIVE: int
    OTHER_TEAM_DEAD: int
    ROUND: int
    SUICIDE: bool
    TEAMKILL: bool
    TEAM_ALIVE: int
    TEAM_DEAD: int
    TIME: int
    WARMUP: bool

class DeathData(TypedDict):
    KILLER: PlayerData | None
    VICTIM: PlayerData
    MATCH_GUID: str
    MOD: MeansOfDeath
    OTHER_TEAM_ALIVE: int
    OTHER_TEAM_DEAD: int
    ROUND: int
    SUICIDE: bool
    TEAMKILL: bool
    TEAM_ALIVE: int
    TEAM_DEAD: int
    TIME: int
    WARMUP: bool

UserInfoEventInput = TypedDict(
    "UserInfoEventInput",
    {
        "ip": str,
        "ui_singlePlayerActive": str,
        "cg_autoAction": str,
        "cg_autoHop": str,
        "cg_predictItems": str,
        "model": str,
        "headmodel": str,
        "cl_anonymous": str,
        "countr<": str,
        "color1": str,
        "rate": str,
        "color2": str,
        "sex": str,
        "teamtask": str,
        "name": str,
        "handicap": str,
        "password": str,
    },
    total=False,
)

class PlayerKillStats(TypedDict):
    DATA: KillData
    TYPE: Literal["PLAYER_KILL"]

class PlayerDeathStats(TypedDict):
    DATA: DeathData
    TYPE: Literal["PLAYER_DEATH"]

class MedalData(TypedDict):
    MATCH_GUID: str
    MEDAL: Literal[
        "ACCURACY",
        "ASSISTS",
        "CAPTURES",
        "COMBOKILL",
        "DEFENDS",
        "EXCELLENT",
        "FIRSTFRAG",
        "HEADSHOT",
        "HUMILIATION",
        "IMPRESSIVE",
        "MIDAIR",
        "PERFECT",
        "PERFORATED",
        "QUADGOD",
        "RAMPAGE",
        "REVENGE",
    ]
    NAME: str
    STEAM_ID: str
    TIME: int
    TOTAL: int
    WARMUP: bool

class PlayerMedalStats(TypedDict):
    DATA: MedalData
    TYPE: Literal["PLAYER_MEDAL"]

class RoundOverStats(TypedDict):
    DATA: RoundEndData
    TYPE: Literal["ROUND_OVER"]

class PlayerGameData(TypedDict):
    MATCH_GUID: str
    NAME: str
    STEAM_ID: str
    TIME: int
    WARMUP: bool

class PlayerConnectStats(TypedDict):
    DATA: PlayerGameData
    TYPE: Literal["PLAYER_CONNECT"]

class PlayerDisconnectStats(TypedDict):
    DATA: PlayerGameData
    TYPE: Literal["PLAYER_DICCONNECT"]

class TeamSwitchEvent(TypedDict):
    NAME: str
    OLD_TEAM: str
    STEAM_ID: str
    TEAM: str

class TeamSwitchGameData(TypedDict):
    KILLER: TeamSwitchEvent
    MATCH_GUID: str
    TIME: int
    WARMUP: bool

class PlayerSwitchTeamStats(TypedDict):
    DATA: TeamSwitchGameData
    TYPE: Literal["PLAYER_SWITCHTEAM"]

class MatchStartedStats(TypedDict):
    DATA: GameStartData
    TYPE: Literal["MATCH_STARTED"]

class MatchReportStats(TypedDict):
    DATA: GameEndData
    TYPE: Literal["MATCH_REPORT"]

class DamageEntry(TypedDict):
    DEALT: int
    TAKEN: int

class MedalsEntry(TypedDict):
    ACCURACY: int
    ASSISTS: int
    CAPTURES: int
    COMBOKILL: int
    DEFENDS: int
    EXCELLENT: int
    FIRSTFRAG: int
    HEADSHOT: int
    HUMILIATION: int
    IMPRESSIVE: int
    MIDAIR: int
    PERFECT: int
    PERFORATED: int
    QUADGOD: int
    RAMPAGE: int
    REVENGE: int

class PickupsEntry(TypedDict):
    AMMO: int
    ARMOR: int
    ARMOR_REGEN: int
    BATTLESUIT: int
    DOUBLER: int
    FLIGHT: int
    GREEN_ARMOR: int
    GUARD: int
    HASTE: int
    HEALTH: int
    INVIS: int
    INVULNERABILITY: int
    KAMIKAZE: int
    MEDKIT: int
    MEGA_HEALTH: int
    OTHER_HOLDABLE: int
    OTHER_POWERUP: int
    PORTAL: int
    QUAD: int
    RED_ARMOR: int
    REGEN: int
    SCOUT: int
    TELEPORTER: int
    YELLOW_ARMOR: int

class SingleWeaponStatsEntry(TypedDict):
    D: int
    DG: int
    DR: int
    H: int
    K: int
    P: int
    S: int
    T: int

class WeaponsStatsEntry(TypedDict):
    BFG: SingleWeaponStatsEntry
    CHAINGUN: SingleWeaponStatsEntry
    GAUNTLET: SingleWeaponStatsEntry
    GRENADE: SingleWeaponStatsEntry
    HMG: SingleWeaponStatsEntry
    LIGHTNING: SingleWeaponStatsEntry
    MACHINEGUN: SingleWeaponStatsEntry
    NAILGUN: SingleWeaponStatsEntry
    OTHER_WEAPON: SingleWeaponStatsEntry
    PLASMA: SingleWeaponStatsEntry
    PROXMINE: SingleWeaponStatsEntry
    RAILGUN: SingleWeaponStatsEntry
    ROCKET: SingleWeaponStatsEntry
    SHOTGUN: SingleWeaponStatsEntry

class PlayerStatsEntry(TypedDict):
    ABORTED: bool
    BLUE_FLAG_PICKUPS: int
    DAMAGE: DamageEntry
    DEATHS: int
    HOLY_SHITS: int
    KILLS: int
    LOSE: int
    MATCH_GUID: str
    MAX_STREAK: int
    MEDALS: MedalsEntry
    MODEL: str
    NAME: str
    NEUTRAL_FLAG_PICKUPS: int
    PICKUPS: PickupsEntry
    PLAY_TIME: int
    QUIT: int
    RANK: int
    RED_FLAG_PICKUPS: int
    SCORE: int
    STEAM_ID: str
    TEAM: int
    TEAM_JOIN_TIME: int
    TEAM_RANK: int
    TIED_RANK: int
    TIED_TEAM_RANK: int
    WARMUP: bool
    WEAPONS: WeaponsStatsEntry
    WIN: int

class PlayerStatsStats(TypedDict):
    DATA: PlayerStatsEntry
    TYPE: Literal["PLAYER_STATS"]

StatsData = (
    PlayerKillStats
    | PlayerDeathStats
    | PlayerMedalStats
    | RoundOverStats
    | PlayerConnectStats
    | PlayerDisconnectStats
    | PlayerSwitchTeamStats
    | MatchStartedStats
    | MatchReportStats
    | PlayerStatsStats
)

class Plugin:
    _loaded_plugins: ClassVar[dict[str, Any]] = ...
    database: Type[Redis] | None = ...
    _hooks: list[tuple[str, Callable, int]]
    _commands: list[Command]
    _db_instance: Redis | None = ...

    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[str] = ...) -> str | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[bool]) -> bool | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[int]) -> int | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[float]) -> float | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[list]) -> list[str] | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[set]) -> set[str] | None: ...
    @classmethod
    @overload
    def get_cvar(cls, name: str, return_type: Type[tuple]) -> tuple[str, ...] | None: ...
    @classmethod
    def set_cvar(
        cls,
        name: str,
        value: str | bool | int | float | list | set | tuple,
        flags: int = ...,
    ) -> bool: ...
    @classmethod
    def set_cvar_limit(
        cls,
        name: str,
        value: int | float,
        minimum: int | float,
        maximum: int | float,
        flags: int = ...,
    ) -> bool: ...
    @classmethod
    def set_cvar_once(
        cls,
        name: str,
        value: str | bool | int | float | list | set | tuple,
        flags: int = ...,
    ) -> bool: ...
    @classmethod
    def set_cvar_limit_once(
        cls,
        name: str,
        value: int | float,
        minimum: int | float,
        maximum: int | float,
        flags: int = ...,
    ) -> bool: ...
    @classmethod
    def players(cls) -> list[Player]: ...
    @classmethod
    def player(cls, name: str | int | Player, player_list: Iterable[Player] | None = ...) -> Player | None: ...
    @classmethod
    def msg(cls, msg: str, chat_channel: str = ..., **kwargs: str) -> None: ...
    @classmethod
    def console(cls, text: str) -> None: ...
    @classmethod
    def clean_text(cls, text: str) -> str: ...
    @classmethod
    def colored_name(cls, name: str | Player, player_list: Iterable[Player] | None = ...) -> str | None: ...
    @classmethod
    def client_id(cls, name: str | int | Player, player_list: Iterable[Player] | None = ...) -> int | None: ...
    @classmethod
    def find_player(cls, name: str, player_list: Iterable[Player] | None = ...) -> list[Player]: ...
    @classmethod
    def teams(cls, player_list: Iterable[Player] | None = ...) -> Mapping[str, list[Player]]: ...
    @classmethod
    def center_print(cls, msg: str, recipient: str | int | Player | None = ...) -> None: ...
    @classmethod
    def tell(cls, msg: str, recipient: str | int | Player, **kwargs: str) -> None: ...
    @classmethod
    def is_vote_active(cls) -> bool: ...
    @classmethod
    def current_vote_count(cls) -> tuple[int, int] | None: ...
    @classmethod
    def callvote(cls, vote: str, display: str, time: int = ...) -> bool: ...
    @classmethod
    def force_vote(cls, pass_it: bool) -> bool: ...
    @classmethod
    def teamsize(cls, size: int) -> None: ...
    @classmethod
    def kick(cls, player: str | int | Player, reason: str = ...) -> None: ...
    @classmethod
    def shuffle(cls) -> None: ...
    @classmethod
    def cointoss(cls) -> None: ...
    @classmethod
    def change_map(cls, new_map: str, factory: str | None = ...) -> None: ...
    @classmethod
    def switch(cls, player: Player, other_player: Player) -> None: ...
    @classmethod
    def play_sound(cls, sound_path: str, player: Player | None = ...) -> bool: ...
    @classmethod
    def play_music(cls, music_path: str, player: Player | None = ...) -> bool: ...
    @classmethod
    def stop_sound(cls, player: Player | None = ...) -> None: ...
    @classmethod
    def stop_music(cls, player: Player | None = ...) -> None: ...
    @classmethod
    def slap(cls, player: str | int | Player, damage: int = ...) -> None: ...
    @classmethod
    def slay(cls, player: str | int | Player) -> None: ...
    @classmethod
    def timeout(cls) -> None: ...
    @classmethod
    def timein(cls) -> None: ...
    @classmethod
    def allready(cls) -> None: ...
    @classmethod
    def pause(cls) -> None: ...
    @classmethod
    def unpause(cls) -> None: ...
    @classmethod
    def lock(cls, team: str | None = ...) -> None: ...
    @classmethod
    def unlock(cls, team: str | None = ...) -> None: ...
    @classmethod
    def put(cls, player: Player, team: str) -> None: ...
    @classmethod
    def mute(cls, player: Player) -> None: ...
    @classmethod
    def unmute(cls, player: Player) -> None: ...
    @classmethod
    def tempban(cls, player: Player) -> None: ...
    @classmethod
    def ban(cls, player: Player) -> None: ...
    @classmethod
    def unban(cls, player: Player) -> None: ...
    @classmethod
    def opsay(cls, msg: str) -> None: ...
    @classmethod
    def addadmin(cls, player: Player) -> None: ...
    @classmethod
    def addmod(cls, player: Player) -> None: ...
    @classmethod
    def demote(cls, player: Player) -> None: ...
    @classmethod
    def abort(cls) -> None: ...
    @classmethod
    def addscore(cls, player: Player, score: int) -> None: ...
    @classmethod
    def addteamscore(cls, team: str, score: int) -> None: ...
    @classmethod
    def setmatchtime(cls, time: int) -> None: ...
    def __init__(self) -> None: ...
    def __str__(self) -> str: ...
    @property
    def db(self) -> Redis: ...
    @property
    def name(self) -> str: ...
    @property
    def plugins(self) -> Mapping[str, Any]: ...
    @property
    def hooks(self) -> Iterable[tuple[str, Callable, int]]: ...
    @property
    def commands(self) -> Iterable[Command]: ...
    @property
    def game(self) -> Game | None: ...
    @property
    def logger(self) -> Logger: ...
    @overload
    def add_hook(
        self,
        event: Literal["console_print"],
        handler: Callable[
            [str],
            str | CancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["command"],
        handler: Callable[
            [Player, Command, str],
            CancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["client_command"],
        handler: Callable[[Player | None, str], str | bool | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["server_command"],
        handler: Callable[[Player | None, str], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["frame"],
        handler: Callable[[], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["set_configstring"],
        handler: Callable[[int, str], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["chat"],
        handler: Callable[[Player, str, AbstractChannel], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["unload"],
        handler: Callable[[Plugin], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["player_connect"],
        handler: Callable[[Player], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["player_loaded"],
        handler: Callable[[Player], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["player_disconnect"],
        handler: Callable[[Player, str | None], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["player_spawn"],
        handler: Callable[[Player], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["stats"],
        handler: Callable[[StatsData], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["vote_called"],
        handler: Callable[[Player, str, str | None], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["vote_started"],
        handler: Callable[[Player, str, str | None], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["vote_ended"],
        handler: Callable[[tuple[int, int], str, str | None, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["vote"],
        handler: Callable[[Player, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["game_countdown"],
        handler: Callable[[], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["game_start"],
        handler: Callable[[GameStartData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["game_end"],
        handler: Callable[[GameEndData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["round_countdown"],
        handler: Callable[[int], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["round_start"],
        handler: Callable[[int], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["round_end"],
        handler: Callable[[RoundEndData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["team_switch"],
        handler: Callable[[Player, str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["team_switch_attempt"],
        handler: Callable[[Player, str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["map"],
        handler: Callable[[str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["new_game"],
        handler: Callable[[], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["kill"],
        handler: Callable[[Player, Player, KillData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["death"],
        handler: Callable[[Player, Player | None, DeathData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["userinfo"],
        handler: Callable[[Player, UserInfoEventInput], UserInfo | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["kamikaze_use"],
        handler: Callable[[Player], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["kamikaze_explde"],
        handler: Callable[[Player, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["player_items_toss"],
        handler: Callable[[Player], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def add_hook(
        self,
        event: Literal["damage"],
        handler: Callable[
            [Player | int | None, Player | int | None, int, int, int],
            UncancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["console_print"],
        handler: Callable[
            [str],
            str | CancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["command"],
        handler: Callable[
            [Player, Command, str],
            CancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["client_command"],
        handler: Callable[[Player | None, str], str | bool | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["server_command"],
        handler: Callable[[Player | None, str], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["frame"],
        handler: Callable[[], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["set_configstring"],
        handler: Callable[[int, str], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["chat"],
        handler: Callable[[Player, str, AbstractChannel], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["unload"],
        handler: Callable[[Plugin], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["player_connect"],
        handler: Callable[[Player], str | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["player_loaded"],
        handler: Callable[[Player], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["player_disconnect"],
        handler: Callable[[Player, str | None], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["player_spawn"],
        handler: Callable[[Player], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["stats"],
        handler: Callable[[StatsData], UncancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["vote_called"],
        handler: Callable[[Player, str, str | None], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["vote_started"],
        handler: Callable[[Player, str, str | None], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["vote_ended"],
        handler: Callable[[tuple[int, int], str, str | None, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["vote"],
        handler: Callable[[Player, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["game_countdown"],
        handler: Callable[[], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["game_start"],
        handler: Callable[[GameStartData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["game_end"],
        handler: Callable[[GameEndData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["round_countdown"],
        handler: Callable[[int], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["round_start"],
        handler: Callable[[int], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["round_end"],
        handler: Callable[[RoundEndData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["team_switch"],
        handler: Callable[[Player, str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["team_switch_attempt"],
        handler: Callable[[Player, str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["map"],
        handler: Callable[[str, str], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["new_game"],
        handler: Callable[[], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["kill"],
        handler: Callable[[Player, Player, KillData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["death"],
        handler: Callable[[Player, Player | None, DeathData], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["userinfo"],
        handler: Callable[[Player, UserInfoEventInput], UserInfo | CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["kamikaze_use"],
        handler: Callable[[Player], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["kamikaze_explde"],
        handler: Callable[[Player, bool], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["player_items_toss"],
        handler: Callable[[Player], CancellableEventReturn],
        priority: int = ...,
    ) -> None: ...
    @overload
    def remove_hook(
        self,
        event: Literal["damage"],
        handler: Callable[
            [Player | int | None, Player | int | None, int, int, int],
            UncancellableEventReturn,
        ],
        priority: int = ...,
    ) -> None: ...
    def add_command(
        self,
        name: str | Iterable[str],
        handler: Callable[[Player, str | list[str], AbstractChannel], CancellableEventReturn],
        permission: int = ...,
        channels: Iterable[AbstractChannel] | None = ...,
        exclude_channels: Iterable[AbstractChannel] = ...,
        priority: int = ...,
        client_cmd_pass: bool = ...,
        client_cmd_perm: int = ...,
        prefix: bool = ...,
        usage: str = ...,
    ) -> None: ...
    def remove_command(
        self,
        name: Iterable[str],
        handler: Callable[[Player, str, AbstractChannel], CancellableEventReturn],
    ) -> None: ...
