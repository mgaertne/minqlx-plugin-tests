from minqlx import Plugin


# noinspection PyPep8Naming
class thirtysecwarn(Plugin):
    announcerMap: dict[str, str]
    warner_thread_name: str | None

    def __init__(self) -> None: ...
    def handle_game_start(self, _game: dict) -> None: ...
    def handle_round_end(self, _data: dict) -> None: ...
    def handle_round_start(self, _round_number: int) -> None: ...
    def warntimer(self) -> None: ...
    def play_thirty_second_warning(self, warner_thread_name: str) -> None: ...
    def get_announcer_sound(self) -> str: ...
    def random_announcer(self) -> str: ...
