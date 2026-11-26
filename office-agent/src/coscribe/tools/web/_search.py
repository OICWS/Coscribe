"""The free search engines, asked all at once under one deadline.

Which engines a network can reach differs by country, by proxy and by the day: one network blocks
every engine, another lets two through, a broken proxy accepts the connection and reaches none.
Asking the engines in turn costs each unreachable one its whole timeout, so they are asked
together, the first answers are kept for a moment for the others to join, and a call where none
could be reached ends at the deadline with what failed, said so the person can act on it.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from ddgs import DDGS
from ddgs.engines import ENGINES

from ...runtime import without_credentials

# `ENGINES["text"]` is what ddgs has enabled; its encyclopedias answer only for things that have
# an article, so their results go after the search engines'.
_LAST = ("wikipedia", "grokipedia")
ENGINE_TIMEOUT_SECONDS = 6
DEADLINE_SECONDS = 8.0
# How long the other engines get to add their results once one has answered.
GRACE_SECONDS = 1.0
# A verdict of "nothing reachable" is reused this long, so the model's next reworded query fails
# at once instead of after another deadline.
UNREACHABLE_MEMORY_SECONDS = 30.0

_CONNECTION_WORDS = (
    "timed out",
    "timeout",
    "error sending request",
    "connect",
    "connection",
    "reset",
    "refused",
    "eof",
    "handshake",
    "tls",
    "ssl",
    "dns",
    "resolve",
    "proxy",
)


class SearchUnreachableError(ConnectionError):
    """No search engine could be reached; the message says why and what the person can do."""


class SearchEmptyError(LookupError):
    """The engines answered, and none had results for the query."""


_memory_lock = threading.Lock()
_unreachable: dict[str | None, tuple[float, str]] = {}


def engine_names() -> list[str]:
    names = list(ENGINES["text"])
    return [n for n in names if n not in _LAST] + [n for n in _LAST if n in names]


def _is_connection_failure(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(word in text for word in _CONNECTION_WORDS)


def _ask(name: str, query: str, max_results: int, proxy: str | None) -> list[dict[str, Any]]:
    engine = DDGS(proxy=proxy, timeout=ENGINE_TIMEOUT_SECONDS)
    return engine.text(query, backend=name, max_results=max_results)


def _unreachable_message(proxy: str | None, tried: int) -> str:
    if proxy:
        return (
            f"Couldn't reach any of the {tried} search engines through the proxy "
            f"{without_credentials(proxy)}: every connection failed or timed out. The proxy may "
            "be down, or reach nothing beyond it. Tell the person to check the proxy (Settings > "
            "General > Proxy has a Test connection); searching again now won't help."
        )
    return (
        f"Couldn't reach any of the {tried} search engines from this network: every connection "
        "failed or timed out, which is what a network that blocks them looks like. If the person "
        "uses a proxy, it goes in Settings > General > Proxy; searching again now won't help. "
        "A site this network can reach may still open in the browser, if one is connected."
    )


def search(query: str, max_results: int, proxy: str | None) -> list[dict[str, Any]]:
    """Results from every engine that answered in time, in `engine_names()` order, one per URL."""
    with _memory_lock:
        remembered = _unreachable.get(proxy)
    if remembered and time.monotonic() - remembered[0] < UNREACHABLE_MEMORY_SECONDS:
        raise SearchUnreachableError(remembered[1])
    names = engine_names()
    pool = ThreadPoolExecutor(max_workers=len(names), thread_name_prefix="web-search")
    futures: dict[Future[list[dict[str, Any]]], str] = {
        pool.submit(_ask, name, query, max_results, proxy): name for name in names
    }
    answers: dict[str, list[dict[str, Any]]] = {}
    failures: dict[str, BaseException] = {}
    deadline = time.monotonic() + DEADLINE_SECONDS
    pending = set(futures)
    try:
        while pending:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            done, pending = wait(pending, timeout=left, return_when=FIRST_COMPLETED)
            for future in done:
                name = futures[future]
                failure = future.exception()
                if failure is None:
                    answers[name] = future.result()
                else:
                    failures[name] = failure
            if any(answers.values()):
                deadline = min(deadline, time.monotonic() + GRACE_SECONDS)
    finally:
        # Threads still waiting on an unreachable engine end at their own timeout, unawaited.
        pool.shutdown(wait=False, cancel_futures=True)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        for result in answers.get(name) or []:
            url = str(result.get("href", ""))
            if url in seen:
                continue
            seen.add(url)
            results.append(result)
    if results:
        return results[:max_results]
    reached = set(answers) | {n for n, exc in failures.items() if not _is_connection_failure(exc)}
    if not reached:
        message = _unreachable_message(proxy, len(names))
        with _memory_lock:
            _unreachable[proxy] = (time.monotonic(), message)
        raise SearchUnreachableError(message)
    raise SearchEmptyError(
        f"No results for {query!r}: {len(reached)} search engine(s) answered with none "
        "(they also do this when they take a query for automated traffic). Try other words."
    )
