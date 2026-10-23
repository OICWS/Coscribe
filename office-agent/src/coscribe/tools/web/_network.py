"""The web tools under a conversation's network setting (Edit environment > Network)."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar, cast

from ...runtime import NetworkGuard

F = TypeVar("F", bound=Callable[..., Any])


def request_hooks(network: NetworkGuard | None) -> dict[str, list[Callable[[Any], None]]]:
    return network.request_hooks() if network is not None else {}


def online_only(fn: F, network: NetworkGuard | None) -> F:
    """`fn` refused when the conversation has no network. Searching reaches only the search
    engine, so a limited conversation may search; opening a result is what the list limits."""
    if network is None:
        return fn

    @functools.wraps(fn)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        network.check_online()
        return fn(*args, **kwargs)

    return cast(F, guarded)
