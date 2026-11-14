from typing import Protocol, cast

import minqlx


class FakeRuntime(Protocol):
    """The functions only the test fake of ``minqlx`` provides to drive its tasks and threads."""

    def reset_registrations(self) -> None: ...
    def run_delayed_tasks(self) -> None: ...
    def run_next_frame_tasks(self) -> None: ...
    def join_minqlx_threads(self) -> None: ...


fake_runtime = cast("FakeRuntime", minqlx)
