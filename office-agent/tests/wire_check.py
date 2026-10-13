"""Validates a payload sent over the chat WebSocket against conversation/wire.py.

Hand-rolled on typing introspection because pydantic's TypedDict support wants
typing_extensions.TypedDict on Python 3.11, and wire.py is stdlib only.
"""

import types
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, is_typeddict

from coscribe.conversation import wire


class WireError(AssertionError):
    pass


def check_event(payload: Any) -> None:
    """Raise WireError unless `payload` is exactly one server -> client event."""
    _check_top(payload, wire.SERVER_EVENTS, "event")


def check_client_message(payload: Any) -> None:
    _check_top(payload, wire.CLIENT_MESSAGES, "client message")


def _check_top(payload: Any, known: dict[str, list[Any]], what: str) -> None:
    if not isinstance(payload, dict):
        raise WireError(f"{what} is not an object: {payload!r}")
    kind = payload.get("type")
    if kind not in known:
        raise WireError(f"unknown {what} type {kind!r}; known: {sorted(known)}")
    errors = []
    for cls in known[kind]:
        try:
            _check(payload, cls, kind)
            return
        except WireError as exc:
            errors.append(str(exc))
    raise WireError(" | ".join(errors))


def _check(value: Any, expected: Any, path: str) -> None:
    if expected is Any:
        return
    if is_typeddict(expected):
        _check_typeddict(value, expected, path)
        return
    origin = get_origin(expected)
    if origin is Literal:
        if not any(value == a and type(value) is type(a) for a in get_args(expected)):
            raise WireError(f"{path}: {value!r} is not one of {get_args(expected)}")
        return
    if origin in (Union, types.UnionType):
        errors = []
        for member in get_args(expected):
            try:
                _check(value, member, path)
                return
            except WireError as exc:
                errors.append(str(exc))
        raise WireError(f"{path}: matches no member of the union ({'; '.join(errors)})")
    if origin is list:
        if not isinstance(value, list):
            raise WireError(f"{path}: expected a list, got {value!r}")
        (item,) = get_args(expected)
        for index, element in enumerate(value):
            _check(element, item, f"{path}[{index}]")
        return
    if origin is dict:
        if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
            raise WireError(f"{path}: expected an object with string keys, got {value!r}")
        _, item = get_args(expected)
        for key, element in value.items():
            _check(element, item, f"{path}.{key}")
        return
    if expected is type(None):
        if value is not None:
            raise WireError(f"{path}: expected null, got {value!r}")
        return
    if expected is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise WireError(f"{path}: expected a number, got {value!r}")
        return
    if expected is int and isinstance(value, bool):
        raise WireError(f"{path}: expected an int, got a bool")
    if not isinstance(value, expected):
        raise WireError(f"{path}: expected {expected.__name__}, got {value!r}")


def _check_typeddict(value: Any, cls: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise WireError(f"{path}: expected an object ({cls.__name__}), got {value!r}")
    hints = get_type_hints(cls)
    missing = sorted(cls.__required_keys__ - value.keys())
    extra = sorted(value.keys() - hints.keys())
    if missing or extra:
        raise WireError(
            f"{path}: {cls.__name__} has missing keys {missing} and unexpected keys {extra}"
        )
    for key, element in value.items():
        _check(element, hints[key], f"{path}.{key}")
