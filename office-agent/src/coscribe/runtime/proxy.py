"""Shared corporate-proxy detection -- see ROADMAP.md's "Unified
corporate-proxy support" backlog item: LLM provider SDKs already read
HTTP_PROXY/HTTPS_PROXY themselves (httpx/grpc's own env-var support), but
web_search (tools/web/websearch.py) and the Browser panel's headless Chrome
(web/browser_panel.py) each need it forwarded explicitly -- ddgs's
DDGS.text() has its own separate proxy= kwarg unrelated to the standard
env vars, and Chromium's env-var-based proxy auto-detection is
unreliable on Windows (this project's actual target platform), normally
needing an explicit --proxy-server= launch flag instead.

The proxy setting in Settings (issue #666) is written into `.env` as those same variables, so
every place that already loads `.env` applies it: System leaves them to the computer and to what
the person wrote there, Manual sets them to one address, and No proxy blanks them and sets
`NO_PROXY=*`, which httpx, requests and urllib read as "bypass every host" even where Windows has
a proxy of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit
from urllib.request import getproxies

import httpx

PROXY_MODES = ("system", "manual", "none")
DEFAULT_BYPASS = "localhost, 127.0.0.1"

# Different tools read different cases, and on POSIX both can be set at once.
PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)

_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")


class ProxyError(ValueError):
    """A proxy setting that can't be saved; the message is for the person."""


@dataclass(frozen=True)
class ProxySetting:
    mode: str = "system"
    address: str = ""
    bypass: str = DEFAULT_BYPASS
    username: str = ""
    password: str = ""


def configured_proxy() -> str | None:
    """HTTPS_PROXY (any case), falling back to HTTP_PROXY, if the user
    has one set -- via urllib's own getproxies() rather than a hand-
    rolled os.environ lookup so this also picks up Windows' system/
    registry proxy setting, not just an env var."""
    proxies = getproxies()
    return proxies.get("https") or proxies.get("http") or None


def without_credentials(url: str) -> str:
    """`url` with any `user:password@` taken out, up to the last `@` so a password holding an
    unescaped `/` or `@` goes too. Only a real scheme counts as one: in `user:a://b@proxy` the
    `://` is part of the password."""
    scheme = _SCHEME.match(url)
    prefix = scheme.group(0) if scheme else ""
    return prefix + url[len(prefix) :].rpartition("@")[2]


def parse_address(text: str) -> str:
    """`text` as `scheme://host:port`, or ProxyError saying what is wrong with it."""
    text = text.strip()
    if not text:
        raise ProxyError("Enter the proxy's address, for example http://proxy.example.com:8080.")
    if not _SCHEME.match(text):
        text = "http://" + text
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise ProxyError(f"{text} is not an address with a port number.") from None
    if parts.scheme.lower() not in ("http", "https"):
        raise ProxyError("Only HTTP proxies are supported, so the address starts with http://.")
    if parts.username is not None or parts.password is not None:
        raise ProxyError("Put the user name and password in their own fields, not the address.")
    if not parts.hostname or port is None:
        raise ProxyError(f"{text} needs a host and a port, for example proxy.example.com:8080.")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ProxyError(f"{text} has a path; a proxy address is only a host and a port.")
    return f"{parts.scheme.lower()}://{parts.netloc}"


def clean_bypass(text: str) -> str:
    """The "do not use for" list as `NO_PROXY` holds it: comma-separated, no spaces."""
    hosts = [host for host in re.split(r"[\s,;]+", text) if host]
    return ",".join(hosts)


def proxy_url(setting: ProxySetting) -> str:
    """The manual address with the user name and password in it, percent-encoded, the way the
    model SDKs and httpx read it from `HTTPS_PROXY`."""
    if not setting.username:
        return setting.address
    scheme, _, host = setting.address.partition("://")
    userinfo = quote(setting.username, safe="")
    if setting.password:
        userinfo += ":" + quote(setting.password, safe="")
    return f"{scheme}://{userinfo}@{host}"


def proxy_env(setting: ProxySetting, url: str) -> dict[str, str]:
    """What the setting writes into `.env`; `url` is what the proxy variables hold (the proxy's
    URL, or the keychain reference standing for it). Empty for System, which writes nothing."""
    if setting.mode == "manual":
        bypass = clean_bypass(setting.bypass)
        values = {"HTTP_PROXY": url, "HTTPS_PROXY": url, "ALL_PROXY": "", "NO_PROXY": bypass}
    elif setting.mode == "none":
        values = {"HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "", "NO_PROXY": "*"}
    else:
        return {}
    return values | {name.lower(): value for name, value in values.items()}


_REFUSED = "The proxy asks for a user name and password, or did not accept these."


def try_connection(proxy: str | None, target: str, timeout: float = 10.0) -> dict[str, Any]:
    """Whether `target` answers through `proxy` (None: directly). Any HTTP answer from the target
    counts, a 401 from an API without a key too: what is tested is the way there."""
    host = urlsplit(target).hostname or target
    error: str | None = None
    status: int | None = None
    try:
        with httpx.Client(proxy=proxy, trust_env=False, timeout=timeout) as client:
            status = client.get(target).status_code
    except httpx.ProxyError as exc:
        error = _REFUSED if "407" in str(exc) else f"The proxy refused the connection: {exc}."
    except httpx.TimeoutException:
        error = f"No answer from {host} within {timeout:g} s."
    except httpx.HTTPError as exc:
        error = f"Couldn't reach {host}: {exc}."
    if status == 407:
        error = _REFUSED
    return {"ok": error is None, "target": host, "status": status, "error": error}
