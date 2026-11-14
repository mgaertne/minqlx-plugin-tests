from typing import TYPE_CHECKING, TypeVar

from hamcrest import not_

if TYPE_CHECKING:
    from hamcrest.core.matcher import Matcher

T = TypeVar("T")


def negated(matcher: "Matcher[T]") -> "Matcher[T]":
    """:func:`hamcrest.not_` with a type signature that type checkers accept for any matcher."""
    return not_(matcher)
