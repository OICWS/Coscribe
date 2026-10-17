"""Tests for the first-run setup flow: cli.py's _load_settings_or_none
and web/app.py's create_setup_app -- the replacement for a fresh install
with no COSCRIBE_DEFAULT_MODEL/API key configured yet crashing the whole
process outright (see cli.py's _load_settings, still used unchanged by
the CLI itself).

_dotenv_path() (cli.py) resolves to a per-user app-data directory
(~/.config/coscribe/.env on Linux) whenever no ./.env already exists in
the cwd -- exactly the case this whole feature exists for -- so every
test here isolates *both* the cwd (monkeypatch.chdir) and HOME (so the
app-data fallback lands under tmp_path too, never the real user's own
~/.config/coscribe).

The setup app's own `configured: asyncio.Future[Settings]` is resolved
from inside a request handler and read back afterward in the same test --
in production (web/app.py's _run_web_server) both happen on the one
event loop `asyncio.run()` drives. httpx.AsyncClient + ASGITransport
(async tests, not the sync TestClient other test_*.py files use) keeps
that same single-event-loop shape here; TestClient's own portal runs the
ASGI app in a separate thread with a second event loop, which would make
resolving *this* particular future a real cross-loop, not just cross-
test-file-convention, difference from what production code actually
does.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import httpx
import pytest
import uvicorn

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.runtime import app_data_dir as _app_data_dir
from coscribe.web.app import _load_settings_or_none, _run_web_server, create_setup_app


def _isolate_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # load_dotenv(..., override=True) -- which both _load_settings_or_none
    # and create_setup_app's own POST handler call -- writes straight into
    # the real os.environ, bypassing monkeypatch's own tracking entirely
    # (it only auto-reverts monkeypatch.setenv/delenv calls, not arbitrary
    # direct os.environ mutations made by code under test). Without this,
    # an earlier test in this file configuring a real provider/model
    # leaks that value into every later test's *own* fresh tmp_path via
    # pydantic-settings' own "environment always wins over a blank/absent
    # env_file" behavior -- caught the hard way by a real order-dependent
    # failure, not written defensively up front.
    for key in ("COSCRIBE_DEFAULT_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_load_settings_or_none_is_none_with_nothing_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    assert _load_settings_or_none() is None


def test_load_settings_or_none_returns_settings_once_default_model_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    monkeypatch.setenv("COSCRIBE_DEFAULT_MODEL", "anthropic:claude-sonnet-4-5-20250929")

    settings = _load_settings_or_none()
    assert settings is not None
    assert settings.default_model == "anthropic:claude-sonnet-4-5-20250929"


async def test_setup_page_is_served_at_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    configured: asyncio.Future[object] = asyncio.get_running_loop().create_future()
    app = create_setup_app(configured)  # type: ignore[arg-type]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "coscribe-setup-marker" in resp.text


@pytest.mark.parametrize(
    ("payload", "expected_error_fragment"),
    [
        ({"provider": "not-a-real-provider", "model": "x", "api_key": "y"}, "Unknown provider"),
        ({"provider": "anthropic", "model": "", "api_key": "y"}, "Model cannot be blank"),
        ({"provider": "anthropic", "model": "x", "api_key": ""}, "API key cannot be blank"),
    ],
)
async def test_setup_post_rejects_bad_input_without_resolving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, str],
    expected_error_fragment: str,
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    configured: asyncio.Future[object] = asyncio.get_running_loop().create_future()
    app = create_setup_app(configured)  # type: ignore[arg-type]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        resp = await client.post("/api/setup", json=payload)
        result = resp.json()
        assert result["success"] is False
        assert expected_error_fragment in result["error"]
    assert not configured.done()


async def test_setup_post_writes_env_and_resolves_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    configured: asyncio.Future[object] = asyncio.get_running_loop().create_future()
    app = create_setup_app(configured)  # type: ignore[arg-type]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        resp = await client.post(
            "/api/setup",
            json={
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "api_key": "sk-ant-test-key",
            },
        )
        assert resp.json() == {"success": True}

    assert configured.done()
    settings = configured.result()
    assert settings.default_model == "anthropic:claude-sonnet-4-5-20250929"  # type: ignore[attr-defined]

    env_path = _app_data_dir() / ".env"
    env_text = env_path.read_text()
    assert "COSCRIBE_DEFAULT_MODEL='anthropic:claude-sonnet-4-5-20250929'" in env_text
    # A machine with a working keychain stores a reference, not the value.
    assert (
        "ANTHROPIC_API_KEY='sk-ant-test-key'" in env_text
        or "ANTHROPIC_API_KEY='__coscribe_keyring__:builtin-provider:ANTHROPIC_API_KEY'" in env_text
    )
    # Real bug, live-reported: this used to write only the global
    # COSCRIBE_DEFAULT_MODEL, never the per-provider COSCRIBE_ANTHROPIC_
    # DEFAULT_MODEL that get_providers (web/app.py) reads to decide whether
    # this provider appears in the model switcher at all -- so the very
    # provider first-run setup just configured would silently vanish from
    # the switcher's own dropdown the moment a second provider became the
    # active model. See test_web.py's own
    # test_get_providers_falls_back_to_the_global_default_model for the
    # get_providers side of this fix.
    assert "COSCRIBE_ANTHROPIC_DEFAULT_MODEL='claude-sonnet-4-5-20250929'" in env_text


async def test_setup_post_rejects_a_second_submission_once_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_dotenv(tmp_path, monkeypatch)
    configured: asyncio.Future[object] = asyncio.get_running_loop().create_future()
    app = create_setup_app(configured)  # type: ignore[arg-type]
    valid_payload = {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "api_key": "sk-ant-test-key",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        first = await client.post("/api/setup", json=valid_payload)
        assert first.json()["success"] is True

        second = await client.post("/api/setup", json=valid_payload)
        result = second.json()
        assert result["success"] is False
        assert "Already configured" in result["error"]


async def test_run_web_server_hands_over_to_the_real_app_on_the_same_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: no config yet -> _run_web_server serves the setup app
    -> a real HTTP POST configures it -> the same host:port then serves
    the real chat app, all inside one process/one call. This is the part
    a fake-transport test above can't cover: it's the actual proof that
    stopping the setup uvicorn.Server and starting a fresh one for
    create_app_lg really does hand over cleanly on a real socket, not
    just that create_setup_app's own routes behave in isolation."""
    _isolate_dotenv(tmp_path, monkeypatch)
    # The setup server starts on a listener the test bound itself, so no parallel
    # test can take the port before it. The real app then binds the port number
    # itself after the setup server let go, as it does in production; that gap
    # is the one this test is about.
    listener = socket.socket()
    # As uvicorn sets it on the sockets it binds: without it, the setup server's
    # connections still open block the real app's bind on Linux.
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    port = int(listener.getsockname()[1])
    served: list[uvicorn.Server] = []
    real_serve = uvicorn.Server.serve

    async def serve_on_the_listener(
        self: uvicorn.Server, sockets: list[socket.socket] | None = None
    ) -> None:
        first = not served
        served.append(self)
        try:
            await real_serve(self, sockets=[listener] if first else sockets)
        except SystemExit as exc:
            # uvicorn exits the process when it cannot bind or start; inside a
            # task that would end the whole test run instead of failing this test.
            raise RuntimeError(f"uvicorn server {len(served)} exited ({exc.code})") from exc

    monkeypatch.setattr(uvicorn.Server, "serve", serve_on_the_listener)

    server_task = asyncio.create_task(_run_web_server("127.0.0.1", port))
    try:
        async with httpx.AsyncClient() as client:
            setup_resp = await _retry_get(client, f"http://127.0.0.1:{port}/")
            assert "coscribe-setup-marker" in setup_resp.text

            post_resp = await client.post(
                f"http://127.0.0.1:{port}/api/setup",
                json={
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5-20250929",
                    "api_key": "sk-ant-test-key",
                },
            )
            assert post_resp.json() == {"success": True}

            for _ in range(50):
                await asyncio.sleep(0.1)
                if server_task.done():
                    await server_task  # raises why the real app never started
                try:
                    real_resp = await client.get(f"http://127.0.0.1:{port}/", timeout=2)
                except httpx.TransportError:
                    continue  # the gap between the two servers binding
                if "coscribe-setup-marker" not in real_resp.text:
                    break
            else:
                raise AssertionError("the real app never took over the port")

            # On Windows SO_REUSEADDR lets the real app bind beside a setup server
            # that never stopped, and both would accept: only new connections show it.
            assert len(served) == 2
            for _ in range(10):
                again = await client.get(
                    f"http://127.0.0.1:{port}/", headers={"Connection": "close"}
                )
                assert "coscribe-setup-marker" not in again.text
    finally:
        server_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await server_task
        listener.close()


async def _retry_get(client: httpx.AsyncClient, url: str, attempts: int = 30) -> httpx.Response:
    for _ in range(attempts):
        try:
            return await client.get(url)
        except httpx.TransportError:
            await asyncio.sleep(0.1)
    raise AssertionError(f"never got a response from {url}")
