# ruff: noqa: E402
"""Web tests: Settings › Capabilities, the optional LibreOffice found or downloaded on request."""

import stat
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools import LibreOfficeUnavailable
from coscribe.tools import libreoffice as lo
from coscribe.web.routes.settings import libreoffice as routes

from .helpers import FakeToolCallingChatModel, _client_lg

# Windows runs a batch file given as the program; elsewhere a shell script stands in.
_LAUNCHER = "soffice.cmd" if sys.platform == "win32" else "soffice"


@pytest.fixture(autouse=True)
def _nothing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lo.shutil, "which", lambda _name: None)
    monkeypatch.setattr(lo, "_launcher_names", lambda: (_LAUNCHER,))
    lo._version_of.cache_clear()


def _put_a_copy_in(state_dir: Path) -> None:
    launcher = state_dir / "libreoffice" / "26.8.1" / "program" / _LAUNCHER
    launcher.parent.mkdir(parents=True)
    if sys.platform == "win32":
        launcher.write_text("@echo LibreOffice 26.8.1.1 abc\n")
        return
    launcher.write_text('#!/bin/sh\necho "LibreOffice 26.8.1.1 abc"\n')
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)


def _wait_until_done(client: Any) -> dict[str, Any]:
    for _ in range(100):
        status = client.get("/api/libreoffice").json()
        if not status["working"]:
            return status
        time.sleep(0.05)
    raise AssertionError("the download never finished")


def test_status_says_nothing_is_found_and_what_a_download_would_be(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    offer = {"version": "26.8.1", "download_bytes": 1, "installed_bytes": 2}
    monkeypatch.setattr(routes, "libreoffice_offer", lambda: offer)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        status = client.get("/api/libreoffice").json()
    assert status["found"] is False
    assert status["offer"] == offer
    assert status["working"] is False


def test_a_download_runs_in_the_background_and_leaves_a_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def fake_install(state_dir: Path, progress: Any, step: Any) -> None:
        step("download")
        progress(5, 10)
        seen.append("progress")
        step("unpack")
        _put_a_copy_in(state_dir)

    monkeypatch.setattr(routes, "install_libreoffice", fake_install)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        started = client.post("/api/libreoffice")
        assert started.status_code == 200
        done = _wait_until_done(client)
    assert seen == ["progress"]
    assert done["found"] and done["source"] == "own" and done["version"] == "26.8.1.1"
    assert done["error"] == ""


def test_a_second_download_while_one_runs_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    def slow_install(state_dir: Path, progress: Any, step: Any) -> None:
        release.wait(5)
        _put_a_copy_in(state_dir)

    monkeypatch.setattr(routes, "install_libreoffice", slow_install)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.post("/api/libreoffice")
        assert client.post("/api/libreoffice").status_code == 409
        assert client.delete("/api/libreoffice").status_code == 409
        release.set()
        _wait_until_done(client)


def test_a_failed_download_says_why_and_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(state_dir: Path, progress: Any, step: Any) -> None:
        raise LibreOfficeUnavailable("A policy on this computer blocks installing programs.")

    monkeypatch.setattr(routes, "install_libreoffice", failing)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.post("/api/libreoffice")
        done = _wait_until_done(client)
    assert done["found"] is False
    assert done["error"] == "A policy on this computer blocks installing programs."


def test_an_unexpected_failure_shows_a_fixed_text_not_the_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(state_dir: Path, progress: Any, step: Any) -> None:
        raise RuntimeError("C:\\Users\\someone\\secret path")

    monkeypatch.setattr(routes, "install_libreoffice", broken)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.post("/api/libreoffice")
        done = _wait_until_done(client)
    assert done["error"] == "LibreOffice could not be installed."


def test_remove_deletes_coscribes_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_install(state_dir: Path, progress: Any, step: Any) -> None:
        _put_a_copy_in(state_dir)

    monkeypatch.setattr(routes, "install_libreoffice", fake_install)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.post("/api/libreoffice")
        assert _wait_until_done(client)["found"] is True
        removed = client.delete("/api/libreoffice").json()
    assert removed["found"] is False
