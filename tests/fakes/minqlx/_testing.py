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
