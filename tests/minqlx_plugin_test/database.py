from typing import TYPE_CHECKING, Optional, Protocol, cast

if TYPE_CHECKING:
    from minqlx import Plugin


class _FakeDatabaseHolder(Protocol):
    database: object
    _db_instance: object


def use_database(plugin: "Plugin", instance: object, database_class: Optional[object] = None) -> None:
    """Make the plugin use the given object as its database instead of a Redis connection.

    :param plugin: the plugin under test
    :param instance: the object the plugin gets as ``self.db``
    :param database_class: the class to set as the plugin's ``database`` (default: leave it as it is)
    """
    holder = cast("_FakeDatabaseHolder", plugin)
    holder._db_instance = instance
    if database_class is not None:
        holder.database = database_class
