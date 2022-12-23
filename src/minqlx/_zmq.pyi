import zmq

import minqlx


class StatsListener:
    done: bool
    address: str
    password: str | None

    context: zmq.Context
    socket: zmq.Socket
    _in_progress: bool

    def __init__(self): ...

    @minqlx.delay(0.25)
    def keep_receiving(self) -> None: ...
    def stop(self) -> None: ...
