from types import SimpleNamespace
from typing import Any, Type, TypeVar, cast

T = TypeVar("T")


def stand_in(kind: Type[T], /, **attributes: Any) -> T:
    """A bare object with just the given attributes, typed as ``kind`` for the type checker.

    :param kind: the type the object stands in for, e.g. :class:`minqlx.Player`
    :param attributes: the attributes the code under test reads from it
    :return: a :class:`types.SimpleNamespace` that type checkers see as ``kind``
    """
    return cast("T", SimpleNamespace(**attributes))
