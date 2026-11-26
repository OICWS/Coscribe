"""Search and page reading through the person's own model provider, with the key they already gave.

The free engines are sites many networks can't reach; the model provider's API is reachable
wherever the person can chat at all. Which providers have a search is data in `runtime.models`
(`web_search.json`); this module speaks their APIs, the chat key as bearer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from ...runtime import configured_proxy
from ...runtime.models import provider_web_search

_TIMEOUT = httpx.Timeout(20.0, connect=6.0)
# The search API refuses longer queries outright.
_MAX_QUERY_CHARS = 128


class ProviderSearchError(RuntimeError):
    """The provider's search or fetch failed; the message says which and why."""


@dataclass(frozen=True)
class DeepSeekSearch:
    """DeepSeek's search API: `{query, count}` in, `results` of title, url and snippet out."""

    origin: str
    search_path: str
    fetch_path: str
    api_key: str = ""

    name = "DeepSeek"

    def __repr__(self) -> str:
        return f"DeepSeekSearch({self.origin!r})"

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.origin}{path}"
        try:
            with httpx.Client(proxy=configured_proxy(url), timeout=_TIMEOUT) as client:
                response = client.post(
                    url, json=body, headers={"Authorization": f"Bearer {self.api_key}"}
                )
        except httpx.HTTPError as exc:
            raise ProviderSearchError(f"{self.name} couldn't be reached ({exc}).") from exc
        if response.status_code == 402:
            raise ProviderSearchError(f"The {self.name} account has no balance left.")
        if response.status_code == 401:
            raise ProviderSearchError(f"{self.name} didn't accept the API key.")
        if response.status_code != 200:
            try:
                detail = str(response.json()["error"]["message"])
            except (ValueError, KeyError, TypeError):
                detail = response.reason_phrase
            raise ProviderSearchError(f"{self.name} answered {response.status_code}: {detail}")
        try:
            data = response.json()
        except ValueError:
            data = None
        if not isinstance(data, dict):
            # A captive portal or a gateway answers 200 with a page of its own.
            raise ProviderSearchError(f"{self.name} answered with something that isn't a result.")
        return data

    def search(self, query: str, max_results: int) -> list[dict[str, str]]:
        data = self._post(
            self.search_path,
            {"query": query[:_MAX_QUERY_CHARS], "count": max(1, min(max_results, 50))},
        )
        items = data.get("results") or []
        if not isinstance(items, list):
            raise ProviderSearchError(f"{self.name} answered with something that isn't a result.")
        return [
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("snippet") or item.get("summary") or ""),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def fetch(self, url: str) -> tuple[str, str]:
        """(title, the page as markdown)."""
        data = self._post(self.fetch_path, {"url": url})
        return str(data.get("title") or ""), str(data.get("content") or "")


ProviderSearch = DeepSeekSearch
CustomProviders = Callable[[], Mapping[str, Mapping[str, str]]]
# The request and answer shapes this module speaks, by models.dev provider id.
_SEARCH_APIS = {"deepseek": DeepSeekSearch}


def provider_search(custom_providers: CustomProviders | None) -> ProviderSearch | None:
    """The search of the first configured provider that has one (`runtime.models`), or None.
    Read at each call: the person may add a provider mid-conversation. ProviderSearchError when
    the provider settings can't be read, so a failed search says why it had no fallback."""
    if custom_providers is None:
        return None
    try:
        providers = custom_providers()
    except (OSError, ValueError, RuntimeError) as exc:
        raise ProviderSearchError(
            f"Coscribe couldn't read the model provider settings ({exc})."
        ) from exc
    for name, config in providers.items():
        base_url = config.get("base_url", "")
        info = provider_web_search(name, base_url)
        api = _SEARCH_APIS.get(info.provider) if info and info.kind == "search_api" else None
        if api is None or not info or not config.get("api_key"):
            continue
        parts = urlsplit(base_url)
        return api(f"{parts.scheme}://{parts.netloc}", info.search, info.fetch, config["api_key"])
    return None
