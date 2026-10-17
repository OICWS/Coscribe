"""The local server refuses a cross-site page and a rebound hostname (web/local_guard.py)."""

from pathlib import Path

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from coscribe.web.local_guard import ALLOWED_HOSTS_ENV, LocalOnlyGuard

from .helpers import FakeToolCallingChatModel, _client_lg


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv(ALLOWED_HOSTS_ENV, raising=False)
    app = FastAPI()
    app.add_middleware(LocalOnlyGuard)

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/act")
    def act() -> dict[str, bool]:
        return {"done": True}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_text("hello")
        await socket.close()

    return TestClient(app, base_url="http://127.0.0.1:8000")


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:8000", "[::1]:8000", "localhost"])
def test_a_loopback_host_passes(client: TestClient, host: str) -> None:
    assert client.get("/ping", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize(
    "host", ["evil.example", "evil.example:8000", "127.0.0.1.evil.example", "0.0.0.0:8000"]
)
def test_a_rebound_or_foreign_host_is_refused(client: TestClient, host: str) -> None:
    assert client.get("/ping", headers={"Host": host}).status_code == 403


def test_a_cross_site_post_is_refused_and_does_not_run(client: TestClient) -> None:
    resp = client.post("/act", headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:5173", "http://localhost:8000", "http://[::1]:8000"]
)
def test_the_apps_own_origins_pass(client: TestClient, origin: str) -> None:
    assert client.post("/act", headers={"Origin": origin}).status_code == 200


@pytest.mark.parametrize(
    "origin", ["null", "file://", "https://evil.example", "http://localhost.evil.example"]
)
def test_other_origins_are_refused(client: TestClient, origin: str) -> None:
    assert client.post("/act", headers={"Origin": origin}).status_code == 403


def test_a_request_without_origin_passes_for_the_cli_and_the_shell(client: TestClient) -> None:
    assert client.post("/act").status_code == 200


def test_a_websocket_from_the_app_connects(client: TestClient) -> None:
    with client.websocket_connect(
        "/ws", headers={"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1:5173"}
    ) as ws:
        assert ws.receive_text() == "hello"


def test_a_cross_site_websocket_is_closed_before_accept(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect(
            "/ws", headers={"Host": "127.0.0.1:8000", "Origin": "https://evil.example"}
        ):
            pass
    assert refused.value.code == 1008


def test_a_rebound_websocket_is_closed_before_accept(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect("/ws", headers={"Host": "evil.example:8000"}):
            pass
    assert refused.value.code == 1008


@pytest.mark.parametrize(
    "origin",
    [
        "localhost",
        "http://evil.example\\@localhost",
        "http://localhost:abc",
        "http://localhost:99999",
        "ftp://localhost",
        "http://localhost/path",
    ],
)
def test_a_malformed_origin_is_refused(client: TestClient, origin: str) -> None:
    assert client.post("/act", headers={"Origin": origin}).status_code == 403


@pytest.mark.parametrize("host", ["localhost:8000, evil.example", "localhost:abc", "a@localhost"])
def test_a_malformed_host_is_refused(client: TestClient, host: str) -> None:
    assert client.get("/ping", headers={"Host": host}).status_code == 403


def test_two_origin_headers_are_refused(client: TestClient) -> None:
    headers = [("Origin", "http://localhost:5173"), ("Origin", "https://evil.example")]
    assert client.post("/act", headers=headers).status_code == 403


def test_a_cross_site_fetch_without_origin_is_refused(client: TestClient) -> None:
    assert client.get("/ping", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/ping", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_a_refusal_names_the_setting_that_allows_a_host(client: TestClient) -> None:
    detail = client.get("/ping", headers={"Host": "coscribe.lan:8000"}).json()["detail"]
    assert ALLOWED_HOSTS_ENV in detail


def test_a_configured_host_passes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, "coscribe.lan, other.lan:9000")
    assert client.get("/ping", headers={"Host": "coscribe.lan:8000"}).status_code == 200
    assert client.get("/ping", headers={"Host": "other.lan"}).status_code == 200
    assert client.get("/ping", headers={"Host": "stranger.lan"}).status_code == 403


def test_the_setup_app_carries_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from coscribe.web.app import create_setup_app

    monkeypatch.delenv(ALLOWED_HOSTS_ENV, raising=False)
    loop = asyncio.new_event_loop()
    try:
        app = create_setup_app(loop.create_future())
        with TestClient(app, base_url="http://127.0.0.1:8000") as c:
            assert c.get("/", headers={"Host": "evil.example"}).status_code == 403
            assert c.get("/").status_code == 200
    finally:
        loop.close()


def test_the_real_app_carries_the_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The line that adds the guard to create_app_lg is what every route's protection rests on."""
    monkeypatch.delenv(ALLOWED_HOSTS_ENV, raising=False)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        local = {"Host": "127.0.0.1:8000"}
        assert client.get("/api/threads", headers={"Host": "evil.example"}).status_code == 403
        assert client.get("/api/threads", headers=local).status_code == 200
        foreign = {**local, "Origin": "https://evil.example"}
        with pytest.raises(WebSocketDisconnect) as refused:
            with client.websocket_connect("/ws/some-thread", headers=foreign):
                pass
        assert refused.value.code == 1008
