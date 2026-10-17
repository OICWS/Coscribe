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
# Extra names the app is served under (a reverse proxy, a non-loopback `--host`), comma-separated.
ALLOWED_HOSTS_ENV = "COSCRIBE_ALLOWED_HOSTS"


def allowed_hosts() -> frozenset[str]:
    extra = {h.strip().lower() for h in os.environ.get(ALLOWED_HOSTS_ENV, "").split(",")}
    return _LOOPBACK | {h for h in extra if h}


def _hostname(netloc: str) -> str:
    """The host part of `host:port` or `[v6]:port`, lowercased, or "" when it does not parse."""
    try:
        return (urlsplit(f"//{netloc}").hostname or "").lower()
    except ValueError:
        return ""


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope["headers"]:
        if key == name:
            return str(value.decode("latin-1"))
    return None


def violation(scope: Scope) -> str | None:
    """Why this request must be refused, or None when it may pass."""
    allowed = allowed_hosts()
    host = _header(scope, b"host")
    if host is None or _hostname(host) not in allowed:
        return "Host is not this machine"
    origin = _header(scope, b"origin")
    if origin is not None and _hostname(origin.split("://", 1)[-1]) not in allowed:
        # Includes the literal "null" a sandboxed frame or a data: page sends.
        return "Origin is not this machine"
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
