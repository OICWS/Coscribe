"""Refuse requests that reach the local server from somewhere other than the user's own app.

The server trusts "reachable on loopback", but a web page open in the user's browser can reach
loopback too: a cross-site page can open the chat WebSocket (which also answers approvals), and a
hostname rebound to 127.0.0.1 makes the browser treat the server as that page's own origin. Two
checks close both: the `Host` must name this machine, and a browser-sent `Origin` must too. A
request without an `Origin` (the CLI, the desktop shell, scripts) is not a browser page and
passes the second check; the first still applies to it.

An ASGI middleware, not Starlette's `BaseHTTPMiddleware`, because that one does not see
WebSocket handshakes.
"""

import json
import os
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
# Extra host names the app is served under (a reverse proxy, a non-loopback `--host`),
# comma-separated; ports are ignored on both sides of the comparison.
ALLOWED_HOSTS_ENV = "COSCRIBE_ALLOWED_HOSTS"
_HINT = f" (list the names it is served under in {ALLOWED_HOSTS_ENV}, comma-separated)"


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
    if "cross-site" in _headers(scope, b"sec-fetch-site"):
        # A browser sends no Origin on a cross-site <img> or navigation GET, but does say so here.
        return "Request comes from another site"
    return None


class LocalOnlyGuard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        reason = violation(scope)
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
