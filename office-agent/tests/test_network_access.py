"""Edit environment > Network as the tools apply it (runtime/network_access.py): no web tool
runs with none, the web tools reach only the listed domains with limited, redirects included,
and scripts get the network only with full."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from coscribe.runtime import NetworkAccess, NetworkGuard
from coscribe.tools.exec import isolation
from coscribe.tools.exec.isolation import SelfTest
from coscribe.tools.web import websearch
from coscribe.tools.web.browser import BrowserHost, build_browser_tools
from coscribe.tools.web.http_request import build_http_tools
from coscribe.tools.web.images import build_image_tools


def _guard(tmp_path: Path, mode: str, domains: list[str]) -> NetworkGuard:
    NetworkAccess(tmp_path).set("t1", mode, domains)
    return NetworkGuard(tmp_path, "t1")


def test_a_new_conversation_reaches_any_site_but_its_scripts_are_offline(tmp_path: Path) -> None:
    guard = NetworkGuard(tmp_path, "t1")
    guard.check_url("https://anything.example")
    assert guard.sites() is None
    assert not guard.scripts_online()
    assert not NetworkGuard(tmp_path, None).scripts_online()


def test_limited_covers_the_listed_domains_and_their_subdomains(tmp_path: Path) -> None:
    guard = _guard(tmp_path, "limited", ["example.com"])
    guard.check_url("https://example.com/a")
    guard.check_url("https://docs.example.com/a")
    for url in ("https://notexample.com", "https://example.com.evil.net", "evil.net"):
        with pytest.raises(PermissionError, match="Edit environment > Network"):
            guard.check_url(url)
    assert guard.sites() == ["example.com"]


def test_none_refuses_every_web_step_and_full_opens_scripts(tmp_path: Path) -> None:
    guard = _guard(tmp_path, "none", [])
    with pytest.raises(PermissionError, match="no network access"):
        guard.check_online()
    assert guard.sites() == []
    assert _guard(tmp_path, "full", []).scripts_online()


def _serve(monkeypatch: pytest.MonkeyPatch, module: Any, handler: Any) -> list[str]:
    seen: list[str] = []
    real_client = httpx.Client

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return handler(request)

    def client(**kwargs: Any) -> Any:
        kwargs.pop("proxy", None)
        return real_client(transport=httpx.MockTransport(answer), **kwargs)

    monkeypatch.setattr(module.httpx, "Client", client)
    return seen


def _redirect_to_elsewhere(request: httpx.Request) -> httpx.Response:
    if request.url.host == "example.com":
        return httpx.Response(302, headers={"location": "https://evil.net/x"})
    return httpx.Response(200, text="<html><body>secret</body></html>")


def test_read_web_page_does_not_follow_a_redirect_off_the_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _serve(monkeypatch, websearch, _redirect_to_elsewhere)
    tools = websearch.build_websearch_tools(_guard(tmp_path, "limited", ["example.com"]))
    read = {tool.__name__: tool for tool in tools}["read_web_page"]
    with pytest.raises(PermissionError, match="evil.net"):
        read("https://example.com/start")
    assert seen == ["https://example.com/start"]
    with pytest.raises(PermissionError):
        read("https://evil.net/x")


def test_http_request_does_not_follow_a_redirect_off_the_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.web import http_request

    _guard(tmp_path, "limited", ["example.com"])
    seen = _serve(monkeypatch, http_request, _redirect_to_elsewhere)
    tools = {tool.__name__: tool for tool in build_http_tools(tmp_path, "t1")}
    with pytest.raises(PermissionError, match="evil.net"):
        tools["http_request"]("GET", "https://example.com/start")
    assert seen == ["https://example.com/start"]


def test_with_no_network_search_and_downloads_are_refused(tmp_path: Path) -> None:
    guard = _guard(tmp_path, "none", [])
    web = {tool.__name__: tool for tool in websearch.build_websearch_tools(guard)}
    images = {tool.__name__: tool for tool in build_image_tools(tmp_path, network=guard)}
    with pytest.raises(PermissionError):
        web["web_search"]("anything")
    with pytest.raises(PermissionError):
        images["search_images"]("cats")
    with pytest.raises(PermissionError):
        images["download_image"]("https://example.com/cat.png", "cat.png")
    assert not (tmp_path / "cat.png").exists()


def test_the_guarded_tools_keep_their_names_and_arguments(tmp_path: Path) -> None:
    import inspect

    guard = _guard(tmp_path, "limited", ["example.com"])
    for plain, guarded in zip(
        websearch.build_websearch_tools(), websearch.build_websearch_tools(guard), strict=True
    ):
        assert guarded.__name__ == plain.__name__
        assert guarded.__doc__ == plain.__doc__
        assert inspect.signature(guarded) == inspect.signature(plain)


class _Host(BrowserHost):
    def __init__(self) -> None:
        super().__init__()
        self.args: list[dict[str, Any]] = []

    def call(
        self, action: str, args: dict[str, Any], thread_id: str, timeout: float = 30
    ) -> dict[str, Any]:
        self.args.append(args)
        return {}


def _navigate(host: BrowserHost, guard: NetworkGuard) -> Any:
    tools = {tool.__name__: tool for tool in build_browser_tools("t1", host, network=guard)}
    return tools["browser_navigate"]


def test_the_browser_gets_the_list_to_check_each_step_and_nothing_with_no_network(
    tmp_path: Path,
) -> None:
    host = _Host()
    _navigate(host, _guard(tmp_path, "limited", ["example.com"]))("https://example.com")
    _navigate(host, _guard(tmp_path, "full", []))("https://example.com")
    assert host.args[0]["network_sites"] == ["example.com"]
    assert "network_sites" not in host.args[1]
    with pytest.raises(PermissionError):
        _navigate(host, _guard(tmp_path, "none", []))("https://example.com")
    assert len(host.args) == 2


def test_an_isolated_script_has_the_network_only_with_full_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    python = isolation.venv_python(state / "script-env")
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    monkeypatch.setattr(isolation, "available", lambda: True)
    monkeypatch.setattr(isolation, "self_test", lambda *a, **k: SelfTest(True, "", ""))
    monkeypatch.setattr(isolation, "venv_runtime", lambda venv: ())

    def network() -> bool:
        run = isolation.for_scripts(state, writable=[tmp_path], thread_id="t1")
        assert run is not None
        return run.network

    assert network() is False
    NetworkAccess(state).set("t1", "full", [])
    assert network() is True
    NetworkAccess(state).set("t1", "limited", ["*"])
    assert network() is False
