"""Which providers can search the web with the person's own key (`web_search.json`).

A provider capability rather than a model's: DeepSeek's search API answers for the account,
whichever DeepSeek model the person chats with.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .catalog import catalog_provider

WEB_SEARCH_PATH = Path(__file__).parent / "web_search.json"


@dataclass(frozen=True)
class WebSearchInfo:
    """`kind` "search_api": `search` and `fetch` are paths on the provider's own origin."""

    provider: str
    kind: str
    search: str
    fetch: str
    source: str


@cache
def _rows() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = json.loads(WEB_SEARCH_PATH.read_text(encoding="utf-8"))[
        "providers"
    ]
    return data


def provider_web_search(name: str = "", base_url: str = "") -> WebSearchInfo | None:
    """How the coscribe provider named `name` at `base_url` searches the web, or None."""
    pid = catalog_provider(name, base_url)
    row = _rows().get(pid) if pid else None
    if pid is None or row is None:
        return None
    return WebSearchInfo(
        provider=pid,
        kind=row["kind"],
        search=row.get("search", ""),
        fetch=row.get("fetch", ""),
        source=row["source"],
    )
