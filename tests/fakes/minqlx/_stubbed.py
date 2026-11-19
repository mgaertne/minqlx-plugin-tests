"""Builds runtime classes from the installed shinqlx-stubs package.

The stubs stay the single description of the minqlx interface: every class, property and method that they declare
exists here and raises NotImplementedError. Tests replace what they need with mockito or monkeypatch.
"""

import ast
import builtins
from abc import ABC
from importlib.metadata import distribution

STUB_DIRECTORY = distribution("shinqlx-stubs").locate_file("shinqlx-stubs")


def _unavailable(class_name, member):
    def unavailable(*_args, **_kwargs):
        raise NotImplementedError(f"{class_name}.{member} is not available in the test fake of minqlx")

    unavailable.__name__ = member
    return unavailable


def _accept_any_arguments(self, *_args, **_kwargs):
    pass


def _decorator_name(decorator):
    return decorator.id if isinstance(decorator, ast.Name) else decorator.attr


def _bases(node, known):
    bases = tuple(
        known.get(base.id) or getattr(builtins, base.id, None) or {"ABC": ABC}.get(base.id) for base in node.bases
    )
    return None if None in bases else bases


def _members(node):
    members = {}
    properties = {}
    for item in node.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        kinds = {_decorator_name(decorator) for decorator in item.decorator_list}
        function = _unavailable(node.name, item.name)
        if item.name in {"__init__", "__new__"}:
            members["__init__"] = _accept_any_arguments
        elif item.name.startswith("__"):
            continue
        elif "setter" in kinds:
            properties[item.name]["setter"] = function
        elif "property" in kinds:
            properties[item.name] = {"getter": function}
        elif "classmethod" in kinds:
            members[item.name] = classmethod(function)
        elif "staticmethod" in kinds:
            members[item.name] = staticmethod(function)
        else:
            members[item.name] = function
    for name, accessors in properties.items():
        members[name] = property(accessors["getter"], accessors.get("setter"))
    return members


def build(module, namespace):
    """Adds the classes that the stub of the module declares to namespace, skipping those with unknown bases."""
    for node in ast.parse(STUB_DIRECTORY.joinpath(f"{module}.pyi").read_text()).body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = _bases(node, namespace)
        if bases is not None:
            namespace[node.name] = type(node.name, bases, _members(node))
