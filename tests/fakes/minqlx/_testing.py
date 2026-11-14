import minqlx


def reset_registrations():
    """Forgets every command and event hook that plugins registered, so scenarios start without leftovers."""
    for priority_level in minqlx.COMMANDS._commands:
        priority_level.clear()
    for dispatcher in minqlx.EVENT_DISPATCHERS._dispatchers.values():
        dispatcher.plugins.clear()
