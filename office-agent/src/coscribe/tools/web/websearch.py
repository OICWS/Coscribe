"""Live web search for grounding -- current events, facts to verify,
anything beyond what the model already knows from training. Distinct
from search_files/search_pdf (which search *local* workspace content) and
not a RAG/document-retrieval system: this queries the open web directly
through a search engine, no local index or embedding store involved.

Uses the standalone ``ddgs`` package's free, no-key engines, each asked on its own and all at
once (`_search.py`), rather than its "auto" mode, which asks them two at a time and waits out each
unreachable one's timeout in turn.
"""

from __future__ import annotations

import functools
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httpx

from ...runtime import NetworkGuard, configured_proxy, tool_metadata, without_credentials
from . import _search
from ._network import online_only, request_hooks

DEFAULT_MAX_RESULTS = 5
# The free engines turn a query away now and then and answer it on a second try moments later;
# handed back, the model spends a whole step rewording a query that was fine. A network that
# reaches no engine is not retried: a second try fails the same way.
_SEARCH_ATTEMPTS = 2
_SEARCH_RETRY_SECONDS = 1.5


def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict[str, str]]:
    """Search the live web for current information beyond your training
    data -- news, facts to verify, anything time-sensitive. Not for
    finding things already in this workspace (use search_files/
    search_pdf instead), and not a substitute for actually reading a
    document you've already been given.

    Args:
        query: what to search for
        max_results: how many results to return (default 5)
    """
    # ddgs reads only its own proxy= argument (or DDGS_PROXY), not HTTP(S)_PROXY or Windows'
    # setting, so the proxy is looked up here.
    proxy = configured_proxy()
    for attempt in range(_SEARCH_ATTEMPTS):
        try:
            results = _search.search(query, max_results, proxy)
            break
        except _search.SearchEmptyError:
            if attempt == _SEARCH_ATTEMPTS - 1:
                raise
            time.sleep(_SEARCH_RETRY_SECONDS)
    return [
        {
            "title": str(result.get("title", "")),
            "url": str(result.get("href", "")),
            "snippet": str(result.get("body", "")),
        }
        for result in results
    ]


DEFAULT_PAGE_CHARS = 20_000
# A site that answers at all connects within seconds; the longer read timeout is for slow pages.
_PAGE_TIMEOUT = httpx.Timeout(20.0, connect=6.0)
# Page chrome that isn't the content, dropped before converting.
_CHROME_TAGS = ("script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form")
_USER_AGENT = "Mozilla/5.0 (compatible; coscribe)"


def _page_text(html: str) -> tuple[str, str]:
    """(title, the page's main text as markdown)."""
    # Imported here: bs4 (and the lxml it prefers) and markdownify are only needed once a page is
    # read, not for every server start.
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(_CHROME_TAGS):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    text = markdownify(str(root), heading_style="ATX")
    return title, re.sub(r"\n{3,}", "\n\n", text).strip()


def _unreachable_page(url: str, proxy: str | None, exc: Exception) -> str:
    host = urlsplit(url).hostname or url
    reason = "timed out" if isinstance(exc, httpx.TimeoutException) else f"failed ({exc})"
    if proxy:
        return (
            f"Couldn't connect to {host} through the proxy {without_credentials(proxy)}: the "
            f"connection {reason}. The proxy may be down or unable to reach this site; the "
            "browser may still open it, if one is connected."
        )
    return (
        f"Couldn't connect to {host}: the connection {reason}. This network may block the site; "
        "the browser may still open it, if one is connected. A proxy goes in Settings > General "
        "> Proxy."
    )


def read_web_page(url: str, start: int = 0, max_chars: int = DEFAULT_PAGE_CHARS) -> dict[str, Any]:
    """Read a web page's text, as markdown -- an article, documentation, a
    result from web_search. For a page you need to log in to, click
    through, or that only renders in a browser, use the browser connector
    instead, if one is connected.

    Args:
        url: the page's full http(s) address
        start: where to continue from in a long page -- the previous
            call's next_start
        max_chars: how much text to return at most (default 20000)
    """
    return _read_web_page(url, start, max_chars, None)


def _read_web_page(
    url: str, start: int, max_chars: int, network: NetworkGuard | None
) -> dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"{url!r} isn't an http(s) address")
    proxy = configured_proxy(url)
    with httpx.Client(
        proxy=proxy,
        follow_redirects=True,
        timeout=_PAGE_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
        event_hooks=request_hooks(network),
    ) as client:
        try:
            response = client.get(url)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError) as exc:
            raise ConnectionError(_unreachable_page(url, proxy, exc)) from exc
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "html" in content_type or not content_type:
        title, text = _page_text(response.text)
    elif content_type.startswith("text/") or "json" in content_type:
        title, text = "", response.text
    else:
        raise ValueError(
            f"{url} is {content_type.split(';')[0]}, not a page to read -- download it instead"
        )
    chunk = text[start : start + max_chars]
    end = start + len(chunk)
    return {
        "url": str(response.url),
        "title": title,
        "content": chunk,
        "total_chars": len(text),
        "next_start": end if end < len(text) else None,
    }


def build_websearch_tools(network: NetworkGuard | None = None) -> list[Callable[..., Any]]:
    """`network`: the conversation's setting, checked at each call and at each redirect."""

    @functools.wraps(read_web_page)
    def read_web_page_within(
        url: str, start: int = 0, max_chars: int = DEFAULT_PAGE_CHARS
    ) -> dict[str, Any]:
        return _read_web_page(url, start, max_chars, network)

    return [
        tool_metadata(online_only(web_search, network), risk_category="READ", category="web"),
        tool_metadata(read_web_page_within, risk_category="READ", category="web"),
    ]
