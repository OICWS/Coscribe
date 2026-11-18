"""An environment's Network page: how far its conversations may reach the internet.

`none`: no web tool runs and scripts get no network. `limited` (the default): the web tools
reach only the listed domains ("*" for every site) and scripts get no network, since an
isolated script can be given the network only whole. `full`: everything, scripts included.
Kept in the environment (`environments.py`); read at each call, so a change applies to the next
step of a running turn.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MODES = ("none", "limited", "full")
# How the built-in browser treats a site (decision 0050); a site with no entry asks.
BROWSER_LEVELS = ("allow", "ask", "off")
ASK = "ask"
EVERY_SITE = "*"
MAX_DOMAINS = 200
_DOMAIN = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


class NetworkError(ValueError):
    pass


def normalize_domain(text: str) -> str | None:
    """ "https://www.Example.com/a" or "*.example.com" -> "example.com": a domain covers its
    subdomains, as the browser panel's sites do."""
    text = text.strip().lower()
    if text == EVERY_SITE:
        return EVERY_SITE
    if text.startswith("*."):
        text = text[2:]
    host = urlsplit(text if "://" in text else f"https://{text}").hostname or ""
    host = host.removeprefix("www.").rstrip(".")
    return host if _DOMAIN.fullmatch(host) else None


def _covers(domains: list[str], host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(d == EVERY_SITE or host == d or host.endswith(f".{d}") for d in domains)


def clean_network(mode: Any, domains: Any, browser: Any = None) -> dict[str, Any]:
    """A network setting as it is kept, or NetworkError worded for the person. `browser` is kept
    only where it says something: with no network there is no browser, and "ask" is the default."""
    if mode not in MODES:
        raise NetworkError(f"mode must be one of {', '.join(MODES)}.")
    if not isinstance(domains, list) or not all(isinstance(d, str) for d in domains):
        raise NetworkError("domains must be a list of domains.")
    cleaned: list[str] = []
    for text in domains:
        if not text.strip():
            continue
        domain = normalize_domain(text)
        if domain is None:
            raise NetworkError(f"{text.strip()!r} isn't a domain, such as example.com.")
        cleaned.append(domain)
    cleaned = list(dict.fromkeys(cleaned))
    if len(cleaned) > MAX_DOMAINS:
        raise NetworkError(f"At most {MAX_DOMAINS} domains.")
    if mode == "limited" and not cleaned:
        raise NetworkError("Limited needs at least one domain; choose None to turn it off.")
    network: dict[str, Any] = {"mode": mode, "domains": cleaned}
    levels = _clean_levels(browser) if mode != "none" else {}
    if levels:
        network["browser"] = levels
    return network


def _clean_levels(browser: Any) -> dict[str, str]:
    if browser is None:
        return {}
    if not isinstance(browser, dict):
        raise NetworkError("browser must map a site to allow, ask or off.")
    levels: dict[str, str] = {}
    for text, level in browser.items():
        site = normalize_domain(str(text))
        if site is None or site == EVERY_SITE:
            raise NetworkError(f"{str(text).strip()!r} isn't a site, such as example.com.")
        if level not in BROWSER_LEVELS:
            raise NetworkError(f"{site} needs a browser level of allow, ask or off.")
        if level != ASK:
            levels[site] = level
    if len(levels) > MAX_DOMAINS:
        raise NetworkError(f"At most {MAX_DOMAINS} sites with a browser level.")
    return levels


def reaches(network: dict[str, Any], host: str) -> bool:
    """Whether a workspace with this setting may reach `host` at all."""
    if network.get("mode") == "none":
        return False
    return network.get("mode") == "full" or _covers(list(network.get("domains", [])), host)


class NetworkAccess:
    """A conversation's network setting: its environment's."""

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)

    def get(self, thread_id: str | None) -> dict[str, Any]:
        from .environments import Environments  # environments imports this module

        return dict(Environments(self.state_dir).for_thread(thread_id)["network"])


class NetworkGuard:
    """One conversation's network setting as the tools apply it."""

    def __init__(self, state_dir: str | Path, thread_id: str | None) -> None:
        self._access = NetworkAccess(state_dir)
        self._thread_id = thread_id

    def _setting(self) -> dict[str, Any]:
        return self._access.get(self._thread_id)

    def scripts_online(self) -> bool:
        return bool(self._setting()["mode"] == "full")

    def sites(self) -> list[str] | None:
        """The domains a web step may reach, or None for any."""
        setting = self._setting()
        if setting["mode"] == "none":
            return []
        if setting["mode"] == "full" or EVERY_SITE in setting["domains"]:
            return None
        return list(setting["domains"])

    def check_online(self) -> None:
        if self._setting()["mode"] == "none":
            raise PermissionError(
                "This conversation has no network access. The user can allow it in its "
                "environment's Network settings."
            )

    def check_url(self, url: str) -> None:
        self.check_online()
        sites = self.sites()
        host = urlsplit(url if "://" in url else f"https://{url}").hostname or ""
        if sites is not None and not _covers(sites, host):
            raise PermissionError(
                f"{host or url} is outside the domains this conversation may reach. The user "
                "can add it in its environment's Network settings."
            )

    def browser_levels(self) -> dict[str, str]:
        """The built-in browser's level for each site that has one; the desktop app asks for the
        rest."""
        return dict(self._setting().get("browser", {}))

    def request_hooks(self) -> dict[str, list[Callable[[Any], None]]]:
        """httpx event hooks that check every request, so a redirect can't leave the list."""
        return {"request": [lambda request: self.check_url(str(request.url))]}
