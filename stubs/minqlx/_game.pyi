from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Mapping
    from minqlx import Player

class NonexistentGameError(Exception): ...

class Game:
    cached: bool
    _valid: bool

    def __init__(self, cached: bool = ...) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __contains__(self, key: str) -> bool: ...
    def __getitem__(self, key: str) -> str: ...
    @property
    def cvars(self) -> Mapping[str, str]: ...
    @property
    def type(self) -> str: ...
    @property
    def type_short(self) -> str: ...
    @property
    def map(self) -> str: ...
    @map.setter
    def map(self, value: str) -> None: ...
    @property
    def map_title(self) -> str | None: ...
    @property
    def map_subtitle1(self) -> str | None: ...
    @property
    def map_subtitle2(self) -> str | None: ...
    @property
    def red_score(self) -> int: ...
    @property
    def blue_score(self) -> int: ...
    @property
    def state(self) -> str: ...
    @property
    def factory(self) -> str: ...
    @factory.setter
    def factory(self, value: str) -> None: ...
    @property
    def factory_title(self) -> str: ...
    @property
    def hostname(self) -> str: ...
    @hostname.setter
    def hostname(self, value: str) -> None: ...
    @property
    def instagib(self) -> bool: ...
    @instagib.setter
    def instagib(self, value: bool | int) -> None: ...
    @property
    def loadout(self) -> bool: ...
    @loadout.setter
    def loadout(self, value: bool | int) -> None: ...
    @property
    def maxclients(self) -> int: ...
    @maxclients.setter
    def maxclients(self, new_limit: int) -> None: ...
    @property
    def timelimit(self) -> int: ...
    @timelimit.setter
    def timelimit(self, new_limit: int) -> None: ...
    @property
    def fraglimit(self) -> int: ...
    @fraglimit.setter
    def fraglimit(self, new_limit: int) -> None: ...
    @property
    def roundlimit(self) -> int: ...
    @roundlimit.setter
    def roundlimit(self, new_limit: int) -> None: ...
    @property
    def roundtimelimit(self) -> int: ...
    @roundtimelimit.setter
    def roundtimelimit(self, new_limit: int) -> None: ...
    @property
    def scorelimit(self) -> int: ...
    @scorelimit.setter
    def scorelimit(self, new_limit: int) -> None: ...
    @property
    def capturelimit(self) -> int: ...
    @capturelimit.setter
    def capturelimit(self, new_limit: int) -> None: ...
    @property
    def teamsize(self) -> int: ...
    @teamsize.setter
    def teamsize(self, new_size: int) -> None: ...
    @property
    def tags(self) -> Iterable[str]: ...
    @tags.setter
    def tags(self, new_tags: str | Iterable[str]) -> None: ...
    @property
    def workshop_items(self) -> Iterable[int]: ...
    @workshop_items.setter
    def workshop_items(self, new_items: Iterable[int]) -> None: ...
    @classmethod
    def shuffle(cls) -> None: ...
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
