class StatsListener:
    done: bool
    address: str
    password: str | None
    _in_progress: bool

    def __init__(self) -> None: ...
    def keep_receiving(self) -> None: ...
    def stop(self) -> None: ...
