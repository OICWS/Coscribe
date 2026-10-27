"""Tests for runtime/proxy.py -- the shared corporate-proxy detection
used by both tools/web/websearch.py and web/browser_panel.py (see that
module's own docstring for why these two needed it forwarded explicitly
rather than relying on their own libraries' unrelated env-var handling).
"""

import http.server
import threading
from collections.abc import Callable, Iterator

import pytest

from coscribe.runtime import (
    ProxyError,
    ProxySetting,
    configured_proxy,
    parse_address,
    proxy_env,
    proxy_url,
    try_connection,
    without_credentials,
)

_PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "NO_PROXY",
    "no_proxy",
)


def _clear_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _PROXY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_configured_proxy_is_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)

    assert configured_proxy() is None


def test_configured_proxy_reads_uppercase_https_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")

    assert configured_proxy() == "http://proxy.example.com:8080"


def test_configured_proxy_reads_lowercase_https_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("https_proxy", "http://proxy.example.com:8080")

    assert configured_proxy() == "http://proxy.example.com:8080"


def test_configured_proxy_falls_back_to_http_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example.com:3128")

    assert configured_proxy() == "http://proxy.example.com:3128"


def test_configured_proxy_prefers_https_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTP_PROXY", "http://plain-proxy.example.com:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://tls-proxy.example.com:8080")

    assert configured_proxy() == "http://tls-proxy.example.com:8080"


def test_no_proxy_star_beats_a_proxy_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "")
    monkeypatch.setenv("NO_PROXY", "*")

    assert configured_proxy() is None


def test_configured_proxy_leaves_out_a_host_on_the_bypass_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`proxy=` given to httpx wins over `NO_PROXY`, so the tools ask for the proxy per address."""
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")
    monkeypatch.setenv("NO_PROXY", "localhost,.corp.local")

    assert configured_proxy("https://wiki.corp.local/page") is None
    assert configured_proxy("http://localhost:8000/") is None
    assert configured_proxy("https://example.com/") == "http://proxy.example.com:8080"


@pytest.mark.parametrize(
    ("typed", "address"),
    [
        ("proxy.example.com:8080", "http://proxy.example.com:8080"),
        ("  http://proxy.example.com:8080/ ", "http://proxy.example.com:8080"),
        ("HTTP://10.0.0.1:3128", "http://10.0.0.1:3128"),
        ("http://[::1]:3128", "http://[::1]:3128"),
    ],
)
def test_parse_address_accepts_a_host_and_port(typed: str, address: str) -> None:
    assert parse_address(typed) == address


@pytest.mark.parametrize(
    ("typed", "says"),
    [
        ("", "Enter the proxy's address"),
        ("proxy.example.com", "needs a host and a port"),
        ("socks5://proxy.example.com:1080", "Only HTTP proxies"),
        ("http://alice:pw@proxy.example.com:8080", "their own fields"),
        ("http://proxy.example.com:8080/path", "has a path"),
        ("http://proxy.example.com:port", "not an address with a port number"),
    ],
)
def test_parse_address_says_what_is_wrong(typed: str, says: str) -> None:
    with pytest.raises(ProxyError, match=says):
        parse_address(typed)


def test_proxy_url_percent_encodes_the_user_name_and_password() -> None:
    setting = ProxySetting(
        mode="manual", address="http://proxy:8080", username="DOMAIN\\alice", password="p@ss:w/rd"
    )

    assert proxy_url(setting) == "http://DOMAIN%5Calice:p%40ss%3Aw%2Frd@proxy:8080"
    assert proxy_url(ProxySetting(mode="manual", address="http://proxy:8080")) == (
        "http://proxy:8080"
    )


def test_proxy_env_for_each_mode() -> None:
    manual = ProxySetting(mode="manual", address="http://proxy:8080", bypass="localhost; .corp")

    assert proxy_env(manual, "URL") == {
        "HTTP_PROXY": "URL",
        "HTTPS_PROXY": "URL",
        "ALL_PROXY": "",
        "NO_PROXY": "localhost,.corp,127.0.0.1,::1",
        "http_proxy": "URL",
        "https_proxy": "URL",
        "all_proxy": "",
        "no_proxy": "localhost,.corp,127.0.0.1,::1",
    }
    assert proxy_env(ProxySetting(mode="none"), "")["NO_PROXY"] == "*"
    assert proxy_env(ProxySetting(mode="none"), "")["https_proxy"] == ""
    assert proxy_env(ProxySetting(mode="system"), "") == {}


def test_a_typed_bypass_list_never_sends_this_computer_to_the_proxy() -> None:
    manual = ProxySetting(mode="manual", address="http://p:1", bypass="*.corp.local; 10.0.0.0/8")

    assert proxy_env(manual, "URL")["NO_PROXY"] == "*.corp.local,10.0.0.0/8,localhost,127.0.0.1,::1"


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        ("http://alice:hunter2@proxy:8080", "http://proxy:8080"),
        ("alice:a://b@proxy:8080", "proxy:8080"),
        ("http://proxy:8080", "http://proxy:8080"),
    ],
)
def test_without_credentials(url: str, shown: str) -> None:
    assert without_credentials(url) == shown


class _Handler(http.server.BaseHTTPRequestHandler):
    """A target that answers 204, or a proxy that asks for a password."""

    def do_GET(self) -> None:  # noqa: N802 -- the stdlib's name
        status = 407 if self.server.asks_for_password else 204  # type: ignore[attr-defined]
        self.send_response(status)
        if status == 407:
            self.send_header("Proxy-Authenticate", 'Basic realm="corp"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_CONNECT = do_GET  # noqa: N815

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def local_server() -> Iterator[Callable[[bool], str]]:
    servers: list[http.server.HTTPServer] = []

    def start(asks_for_password: bool) -> str:
        server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        server.asks_for_password = asks_for_password  # type: ignore[attr-defined]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()


def test_try_connection_reaches_a_target_directly(local_server: Callable[[bool], str]) -> None:
    target = local_server(False)

    assert try_connection(None, target + "/") == {
        "ok": True,
        "target": "127.0.0.1",
        "status": 204,
        "error": None,
    }


def test_try_connection_reports_a_proxy_asking_for_a_password(
    local_server: Callable[[bool], str],
) -> None:
    proxy = local_server(True)

    plain = try_connection(proxy, "http://example.invalid/")
    tunnelled = try_connection(proxy, "https://example.invalid/")

    assert plain["ok"] is False and "user name and password" in plain["error"]
    assert tunnelled["ok"] is False and "user name and password" in tunnelled["error"]


def test_try_connection_reports_a_proxy_that_is_not_there() -> None:
    result = try_connection("http://127.0.0.1:9", "https://example.invalid/", timeout=3)

    assert result["ok"] is False and result["error"]
