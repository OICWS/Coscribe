"""Edit environment > Network: how far one conversation may reach the internet.

`none`: no web tool runs and scripts get no network. `limited` (the default): the web tools
reach only the listed domains ("*" for every site) and scripts get no network, since an
isolated script can be given the network only whole. `full`: everything, scripts included.
`<thread>.network.json` in the state folder; read at each call, so a change applies to the
next step of a running turn.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MODES = ("none", "limited", "full")
EVERY_SITE = "*"
MAX_DOMAINS = 200
_DEFAULT: dict[str, Any] = {"mode": "limited", "domains": [EVERY_SITE]}
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


class NetworkAccess:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)

    def _path(self, thread_id: str) -> Path:
        return self.state_dir / f"{thread_id}.network.json"

    def get(self, thread_id: str | None) -> dict[str, Any]:
        if thread_id is None:
            return dict(_DEFAULT)
        try:
            raw = json.loads(self._path(thread_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dict(_DEFAULT)
        if not isinstance(raw, dict) or raw.get("mode") not in MODES:
            return dict(_DEFAULT)
        domains = raw.get("domains")
        kept = [d for d in domains if isinstance(d, str)] if isinstance(domains, list) else []
        return {"mode": raw["mode"], "domains": kept}

    def set(self, thread_id: str, mode: Any, domains: Any) -> dict[str, Any]:
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
        data = {"mode": mode, "domains": cleaned}
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(thread_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
        return data

    def delete(self, thread_id: str) -> None:
        self._path(thread_id).unlink(missing_ok=True)


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
                "This conversation has no network access. The user can allow it under "
                "Edit environment > Network."
            )

    def check_url(self, url: str) -> None:
        self.check_online()
        sites = self.sites()
        host = urlsplit(url if "://" in url else f"https://{url}").hostname or ""
        if sites is not None and not _covers(sites, host):
            raise PermissionError(
                f"{host or url} is outside the domains this conversation may reach. The user "
                "can add it under Edit environment > Network."
            )

    def request_hooks(self) -> dict[str, list[Callable[[Any], None]]]:
        """httpx event hooks that check every request, so a redirect can't leave the list."""
        return {"request": [lambda request: self.check_url(str(request.url))]}
