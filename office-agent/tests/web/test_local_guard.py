"""The local server refuses a cross-site page and a rebound hostname (web/local_guard.py)."""

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from coscribe.web.local_guard import ALLOWED_HOSTS_ENV, LocalOnlyGuard


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


def test_a_configured_host_passes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, "coscribe.lan, other.lan")
    assert client.get("/ping", headers={"Host": "coscribe.lan:8000"}).status_code == 200
    assert client.get("/ping", headers={"Host": "stranger.lan"}).status_code == 403


def test_the_real_app_and_the_setup_app_carry_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
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
