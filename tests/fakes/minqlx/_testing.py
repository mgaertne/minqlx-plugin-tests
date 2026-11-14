import threading

import minqlx


def reset_registrations():
    """Forgets commands, event hooks and pending delayed tasks, so scenarios start without leftovers."""
    for priority_level in minqlx.COMMANDS._commands:
        priority_level.clear()
    for dispatcher in minqlx.EVENT_DISPATCHERS._dispatchers.values():
        dispatcher.plugins.clear()
    for event in list(minqlx.frame_tasks.queue):
        minqlx.frame_tasks.cancel(event)
    while not minqlx.next_frame_tasks.empty():
        minqlx.next_frame_tasks.get(block=False)


def run_delayed_tasks():
    """Runs every task queued by ``@minqlx.delay`` right away, whatever its delay is."""
    for event in sorted(minqlx.frame_tasks.queue):
        minqlx.frame_tasks.cancel(event)
        event.action(*event.argument, **event.kwargs)


def run_next_frame_tasks():
    """Runs every task queued by ``@minqlx.next_frame``, as the next game frame would."""
    while not minqlx.next_frame_tasks.empty():
        func, args, kwargs = minqlx.next_frame_tasks.get(block=False)
        func(*args, **kwargs)


def join_minqlx_threads():
    """Waits for the threads started by ``@minqlx.thread``."""
    for thread in threading.enumerate():
        if thread.name.endswith("minqlxthread"):
            thread.join(timeout=2)
