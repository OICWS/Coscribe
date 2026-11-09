"""The offer of a connector from the built-in catalog, shown as a card in the chat (decision 0041).

The model only names an entry and why; the person connects it from the card, in their own
browser, as in Settings. The catalog lives in the web layer, so the server hands it in as a
function, and a conversation without one (the CLI) has no such tool.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Annotated, Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId
from langgraph.prebuilt import InjectedState

from ..runtime import tool_metadata
from ..tools import SCHEDULED_THREAD_PREFIX

TOOL_NAME = "suggest_connector"
OFFER_KEY = "connector_offer"
MAX_REASON_CHARS = 300
MAX_FOUND = 3

# Verbs most descriptions share, and things the built-in tools already do (files, the web), which
# would bring a connector into searches it doesn't fit.
_GENERIC = frozenset(
    "search read edit create update find work with your and the in of on to for data account "
    "accounts look up ask questions use manage add pull check files file web pages content "
    "documentation sites".split()
)
_WORD = re.compile(r"[a-z0-9]+")

Catalog = Callable[[], list[dict[str, Any]]]


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _GENERIC}


def matching_entries(entries: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """The entries not added yet that share a word with the search, the name first."""
    asked = _words(query)
    scored = []
    for entry in entries:
        if entry.get("added"):
            continue
        named = _words(f"{entry['name']} {entry.get('title', '')}")
        described = _words(entry.get("description", ""))
        score = 3 * len(asked & named) + len(asked & described)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda pair: -pair[0])
    return [
        {"name": e["name"], "title": e.get("title", e["name"]), "does": e.get("description", "")}
        for _, e in scored[:MAX_FOUND]
    ]


def _offered_before(messages: list[Any], name: str, call_id: str) -> bool:
    """An earlier offer of this entry: one that was shown, or an earlier call beside this one in
    the same reply (both would pass, as neither has a result yet)."""
    for message in messages:
        calls = message.tool_calls if isinstance(message, AIMessage) else []
        if any(call.get("id") == call_id for call in calls):
            for call in calls:
                if call.get("id") == call_id:
                    break
                if call["name"] == TOOL_NAME and _same(call["args"].get("name"), name):
                    return True
        if not isinstance(message, ToolMessage) or message.name != TOOL_NAME:
            continue
        try:
            result = json.loads(str(message.content))
        except ValueError:
            continue
        if isinstance(result, dict) and result.get(OFFER_KEY) == name:
            return True
    return False


def _same(asked: Any, name: str) -> bool:
    return isinstance(asked, str) and asked.strip().lower() == name


def _entry(entries: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    wanted = name.strip().lower()
    return next(
        (e for e in entries if wanted in (e["name"].lower(), str(e.get("title", "")).lower())),
        None,
    )


def build_connector_offer_tools(catalog: Catalog | None, thread_id: str) -> list[Any]:
    if catalog is None:
        return []
    unattended = thread_id.startswith(SCHEDULED_THREAD_PREFIX)

    def suggest_connector(
        state: Annotated[dict[str, Any], InjectedState],
        call_id: Annotated[str, InjectedToolCallId],
        name: str,
        reason: str,
    ) -> str:
        """Offer the person a connector they haven't added, from the built-in list, when the job
        needs a service you have no tool for (their Notion pages, Jira issues, Gmail, a CRM).
        They see a card with Connect and Not now and sign in in their own browser; you can't
        connect it yourself. After this call, end your turn with one short sentence: the
        connector's tools only work from the next turn, and you get a message when they choose.
        search_tools lists the connectors that fit a search, under "found"; a name that isn't one
        gets back the ones that fit it.

        Args:
            name: the connector's name, e.g. "notion", or what you need, e.g. "jira".
            reason: one sentence the person reads on the card: what you would do with it.
        """
        entries = catalog()
        entry = _entry(entries, name)
        if entry is None:
            # Where search_tools isn't there to list them (every tool bound), this is how the
            # model finds the name.
            fits = ", ".join(f"{e['name']} ({e['does']})" for e in matching_entries(entries, name))
            known = ", ".join(e["name"] for e in entries)
            found = f" Ones that fit: {fits}." if fits else ""
            return (
                f"There is no connector named {name!r} in the built-in list.{found} Names: {known}."
            )
        title = entry.get("title", entry["name"])
        if entry.get("added"):
            return (
                f"{title} is already added. Find its tools with search_tools({entry['name']!r}); "
                "if none come back it is waiting for sign-in, which the person finishes in "
                "Settings > Connectors."
            )
        if unattended:
            return (
                f"Nobody can connect {title} during this run. Do what you can without it and say "
                f"in your result that the task needs {title} connected in Settings > Connectors."
            )
        if _offered_before(list(state.get("messages", [])), entry["name"], call_id):
            return (
                f"You already offered {title} in this conversation; the person's answer is in "
                "it. Don't offer it again unless they ask."
            )
        return json.dumps(
            {
                OFFER_KEY: entry["name"],
                "title": title,
                "reason": " ".join(reason.split())[:MAX_REASON_CHARS],
                "next": f"The person sees a card to connect {title}. End your turn now with one "
                "short sentence and don't try another way meanwhile.",
            },
            ensure_ascii=False,
        )

    return [
        tool_metadata(
            suggest_connector,
            risk_category="READ",
            category="connectors",
            search_hint=lambda query: matching_entries(catalog(), query),
        )
    ]
