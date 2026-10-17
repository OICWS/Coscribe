"""Refuse requests that reach the local server from somewhere other than the user's own app.

The server trusts "reachable on loopback", but a web page open in the user's browser can reach
loopback too: a cross-site page can open the chat WebSocket (which also answers approvals), and a
hostname rebound to 127.0.0.1 makes the browser treat the server as that page's own origin. Two
checks close both: the `Host` must name this machine, and a browser-sent `Origin` must too. A
request without an `Origin` (the CLI, the desktop shell, scripts) is not a browser page and
passes the second check; the first still applies to it.

Those two checks still let a page served from another loopback port through (`localhost:5173`
is loopback too), so each launch also makes a token: the app's own page is served with it, and
a WebSocket handshake or any request that changes state must carry it. A page on another port
cannot read the token (the app sends no CORS headers) and cannot send the header without a
preflight the app refuses. A GET needs no token, because an image, a download link or an iframe
cannot send headers; instead a browser GET that says it comes from another site, or from another
port of this machine (`Sec-Fetch-Site: same-site`), is refused, since some GET routes start a
session or an environment. `tests/web/test_launch_token.py` lists the GET routes read for
side effects.

An ASGI middleware, not Starlette's `BaseHTTPMiddleware`, because that one does not see
WebSocket handshakes.
"""

import hmac
import json
import os
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from starlette.responses import HTMLResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
# Extra host names the app is served under (a reverse proxy, a non-loopback `--host`),
# comma-separated; ports are ignored on both sides of the comparison.
ALLOWED_HOSTS_ENV = "COSCRIBE_ALLOWED_HOSTS"
_HINT = f" (list the names it is served under in {ALLOWED_HOSTS_ENV}, comma-separated)"
# A fixed token for a dev setup whose page does not come from this server (Vite on :5173 adds it
# to what it proxies); every other launch makes a new one.
TOKEN_ENV = "COSCRIBE_LAUNCH_TOKEN"
TOKEN_HEADER = b"x-coscribe-token"
_READ_ONLY = frozenset({"GET", "HEAD", "OPTIONS"})
# These routes check a token of their own (the desktop app's browser host); a new route under
# this prefix must check it too.
_OWN_TOKEN_PREFIX = "/internal/browser-host"
# The page an identity provider sends the browser back to is a cross-site navigation by nature;
# it carries the sign-in's own `state` instead.
_OAUTH_CALLBACK = "/api/mcp/oauth/callback"


def _hostname(netloc: str, scheme: str | None = None) -> str:
    """The host of `host:port`, `[v6]:port` or `scheme://host:port`, lowercased; "" when it does
    not parse strictly. Browsers never send the odd forms refused here (userinfo, backslashes, a
    bad port, a bare name where an origin is due), so refusing them costs nothing."""
    if "\\" in netloc:
        return ""
    try:
        if scheme is None:
            parts = urlsplit(f"//{netloc}")
        else:
            parts = urlsplit(netloc)
            if parts.scheme not in ("http", "https") or parts.path or parts.query or parts.fragment:
                return ""
        if parts.username is not None or parts.password is not None:
            return ""
        _ = parts.port  # raises ValueError for a non-numeric or out-of-range port
        return (parts.hostname or "").lower()
    except ValueError:
        return ""


def allowed_hosts() -> frozenset[str]:
    extra = {_hostname(h.strip()) for h in os.environ.get(ALLOWED_HOSTS_ENV, "").split(",")}
    return _LOOPBACK | {h for h in extra if h}


def _headers(scope: Scope, name: bytes) -> list[str]:
    return [value.decode("latin-1") for key, value in scope["headers"] if key == name]


def violation(scope: Scope) -> str | None:
    """Why this request must be refused, or None when it may pass."""
    allowed = allowed_hosts()
    hosts = _headers(scope, b"host")
    if len(hosts) != 1 or _hostname(hosts[0]) not in allowed:
        return "Host is not this machine" + _HINT
    origins = _headers(scope, b"origin")
    if len(origins) > 1 or (origins and _hostname(origins[0], scheme="origin") not in allowed):
        # Includes the literal "null" a sandboxed frame or a data: page sends.
        return "Origin is not this machine"
    site = _headers(scope, b"sec-fetch-site")
    is_http = scope["type"] == "http"
    cross_site_page = is_http and scope["method"] == "GET" and scope["path"] == _OAUTH_CALLBACK
    if "cross-site" in site and not cross_site_page:
        # A browser sends no Origin on a cross-site <img> or navigation GET, but does say so here.
        return "Request comes from another site"
    if "same-site" in site and is_http and scope["method"] in _READ_ONLY:
        # Another port of this machine: the app's own page is same-origin, and a write there
        # is stopped by the token, which a GET does not carry.
        return "Request comes from another page on this machine"
    return None


def launch_token() -> str:
    return os.environ.get(TOKEN_ENV) or secrets.token_urlsafe(32)


def page_with_token(page: Path, token: str) -> HTMLResponse:
    """The app's page with the launch token in a `<meta>` for its scripts to read."""
    meta = f'<meta name="coscribe-token" content="{token}">'
    html = page.read_text(encoding="utf-8").replace("</head>", f"{meta}</head>", 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


def _token_missing(scope: Scope, token: str) -> bool:
    """Whether this request has to carry the token and does not."""
    path = scope.get("path", "")
    own_token = path == _OWN_TOKEN_PREFIX or path.startswith(_OWN_TOKEN_PREFIX + "/")
    if scope["type"] == "http" and (scope["method"] in _READ_ONLY or own_token):
        return False
    given = _headers(scope, TOKEN_HEADER)
    if not given and scope["type"] == "websocket":
        # A browser cannot set a header on a WebSocket handshake.
        given = parse_qs(scope["query_string"].decode("latin-1")).get("token", [])
    return not any(hmac.compare_digest(value.encode(), token.encode()) for value in given)


class LocalOnlyGuard:
    def __init__(self, app: ASGIApp, token: str | None = None) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        reason = violation(scope)
        if reason is None and self.token and _token_missing(scope, self.token):
            reason = "Launch token missing or wrong"
        if reason is None:
            await self.app(scope, receive, send)
        elif scope["type"] == "websocket":
            await receive()  # the handshake request; a close before accept answers it with 403
            await send({"type": "websocket.close", "code": 1008, "reason": reason})
        else:
            body = json.dumps({"detail": reason}).encode()
            start: Message = {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
            await send(start)
            await send({"type": "http.response.body", "body": body})
