"""Fake of the shinqlx decorators ``hook``, ``command`` and ``game``.

``game`` wraps the method when decorating, so it also guards manually registered and directly called methods.
``hook`` and ``command`` only mark the method; ``register_decorated_handlers`` registers the marked methods of a plugin
instance, like the shinqlx plugin loader after instantiating a plugin. Semantics follow docs/plugin.rst of shinqlx.
"""

import functools
import inspect
import math
import re

import minqlx

GAME_STATES = ("warmup", "countdown", "in_progress")
ARGUMENT_TYPES = (int, float, str)
_INT64 = re.compile(r"[+-]?[0-9]+")
_FLOAT64 = re.compile(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?")
_HOOK = "_shinqlx_hook"
_COMMAND = "_shinqlx_command"
_GAME = "_shinqlx_game"
_FIXED_PARAMETERS = 4
_COMMAND_ARGUMENTS = 3


def hook(event, priority=None):
    def decorator(func):
        setattr(func, _HOOK, (event, minqlx.PRI_NORMAL if priority is None else priority))
        return func

    return decorator


def command(name, *, args=None, min_args=None, usage=None, **options):
    if args is not None:
        args = _validated_arguments(args, min_args)
        min_args = len(args) if min_args is None else min_args
    elif min_args is not None:
        raise TypeError("min_args needs args")

    def decorator(func):
        if args is not None:
            _check_accepts(func, len(args), min_args)
        setattr(func, _COMMAND, (name, args, min_args, usage, options))
        return func

    return decorator


def game(state=None, message=None):
    states = None if state is None else _validated_states(state)

    def decorator(func):
        if hasattr(func, _GAME):
            raise TypeError("@game is applied twice to the same method")

        @functools.wraps(func)
        def guarded(self, *call_args, **call_kwargs):
            if _blocked(states):
                if len(call_args) >= _COMMAND_ARGUMENTS and isinstance(call_args[1], list) and message is not None:
                    call_args[2].reply(message)
                return None
            return func(self, *call_args, **call_kwargs)

        setattr(guarded, _GAME, (states, message))
        return guarded

    return decorator


def register_decorated_handlers(plugin):
    """Register every method of ``plugin`` marked with ``hook`` or ``command``, as the shinqlx plugin loader does."""
    for name in _marked_method_names(type(plugin)):
        function = getattr(type(plugin), name)
        hooked = getattr(function, _HOOK, None)
        commanded = getattr(function, _COMMAND, None)
        handler = getattr(plugin, name)
        if commanded is not None:
            handler = _parsing_handler(handler, function, commanded)
        if hooked is not None:
            plugin.add_hook(hooked[0], handler, hooked[1])
        if commanded is not None:
            plugin.add_command(commanded[0], handler, usage=_usage_for(function, commanded), **commanded[4])


def _marked_method_names(plugin_class):
    names = []
    for klass in reversed(plugin_class.__mro__):
        names.extend(
            name
            for name, member in vars(klass).items()
            if inspect.isfunction(member) and any(hasattr(member, marker) for marker in (_HOOK, _COMMAND))
        )
    return list(dict.fromkeys(names))


def _validated_arguments(args, min_args):
    if isinstance(args, (str, bytes)):
        raise TypeError("args must be a sequence of types, not a string")
    args = tuple(args)
    if any(argument not in (*ARGUMENT_TYPES, minqlx.Player) for argument in args):
        raise ValueError("args may only contain int, float, str and Player")
    if min_args is not None and min_args > len(args):
        raise ValueError("min_args is greater than len(args)")
    return args


def _validated_states(state):
    states = (state,) if isinstance(state, str) else tuple(state)
    if not states:
        raise ValueError("state must not be empty")
    if not all(isinstance(member, str) for member in states):
        raise TypeError("state must consist of strings")
    if unknown := [member for member in states if member not in GAME_STATES]:
        raise ValueError(f"unknown game state {unknown[0]!r}")
    return frozenset(states)


def _check_accepts(func, count, min_args):
    signature = inspect.signature(func)
    if unsupported := [extra for extra in {min_args, count} if not _binds(signature, extra)]:
        raise TypeError(f"{func.__name__} cannot take {unsupported[0]} parsed arguments")


def _binds(signature, extra):
    try:
        signature.bind(*[None] * (_FIXED_PARAMETERS + extra))
    except TypeError:
        return False
    return True


def _usage_for(function, commanded):
    _, args, min_args, usage, _ = commanded
    if usage is not None or args is None:
        return "" if usage is None else usage
    names = [
        parameter.name
        for parameter in list(inspect.signature(function).parameters.values())[_FIXED_PARAMETERS:]
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ][: len(args)]
    names += [f"arg{index + 1}" for index in range(len(names), len(args))]
    return " ".join(f"<{name}>" if index < min_args else f"[{name}]" for index, name in enumerate(names))


def _parsing_handler(handler, function, commanded):
    _, args, min_args, _, _ = commanded
    if args is None:
        return handler
    guard = getattr(function, _GAME, None)

    @functools.wraps(handler)
    def parsing(player, msg, channel):
        if guard is not None and _blocked(guard[0]):
            if guard[1] is not None:
                channel.reply(guard[1])
            return None
        words = msg[1:]
        if len(words) < min_args:
            return minqlx.RET_USAGE
        parsed = []
        for kind, word in zip(args, words):
            value = _parse(kind, word)
            if value is None:
                return minqlx.RET_USAGE
            parsed.append(value)
        return handler(player, msg, channel, *parsed)

    return parsing


def _parse(kind, word):
    if kind is str:
        return word
    if kind is int:
        if _INT64.fullmatch(word) and -(2**63) <= int(word) < 2**63:
            return int(word)
        return None
    if kind is float:
        if _FLOAT64.fullmatch(word) and math.isfinite(value := float(word)):
            return value
        return None
    return minqlx.Plugin.player(word)


def _blocked(states):
    try:
        running = minqlx.Game()
    except minqlx.NonexistentGameError:
        return True
    return states is not None and running.state not in states
