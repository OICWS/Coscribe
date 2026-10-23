"""coscribe's own Python for the script venv on Windows (tools/exec/own_python.py): downloaded
once, checked against its pinned SHA-256, and used ahead of the detected Pythons unless the
person chose one. The real download runs in the Windows CI job, where the script venv is made."""

from __future__ import annotations

import hashlib
import io
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

from coscribe.tools.exec import own_python, script_env


def _archive(with_python: bool = True) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        name = "python/python.exe" if with_python else "python/README"
        data = b"MZ"
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self) -> Any:
        yield self.body


class _Windows:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.monkeypatch = monkeypatch
        self.fetched: list[str] = []

    def serve(self, body: bytes) -> None:
        def stream(method: str, url: str, **kwargs: Any) -> _Response:
            self.fetched.append(url)
            return _Response(body)

        self.monkeypatch.setattr(own_python.httpx, "stream", stream)
        self.monkeypatch.setitem(
            own_python._BUILDS, "AMD64", ("x86_64", hashlib.sha256(body).hexdigest())
        )


@pytest.fixture
def windows(monkeypatch: pytest.MonkeyPatch) -> _Windows:
    monkeypatch.setattr(own_python, "_on_windows", lambda: True)
    monkeypatch.setattr(own_python.platform, "machine", lambda: "AMD64")
    return _Windows(monkeypatch)


def test_off_windows_there_is_no_download(tmp_path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("the answer off Windows")
    assert own_python.download_url() is None
    assert own_python.ensure_own_python(tmp_path) is None


def test_the_download_is_unpacked_once(tmp_path: Path, windows: _Windows) -> None:
    windows.serve(_archive())
    python = own_python.ensure_own_python(tmp_path)
    assert python == tmp_path / "python" / "python.exe" and python.is_file()
    assert own_python.ensure_own_python(tmp_path) == python
    assert len(windows.fetched) == 1
    assert "x86_64-pc-windows-msvc-install_only.tar.gz" in windows.fetched[0]


def test_a_download_that_is_not_the_pinned_file_is_refused(
    tmp_path: Path, windows: _Windows, monkeypatch: pytest.MonkeyPatch
) -> None:
    windows.serve(_archive())
    monkeypatch.setitem(own_python._BUILDS, "AMD64", ("x86_64", "0" * 64))
    with pytest.raises(RuntimeError, match="not the expected file"):
        own_python.ensure_own_python(tmp_path)
    assert not (tmp_path / "python").exists()


def test_an_archive_without_python_installs_nothing(tmp_path: Path, windows: _Windows) -> None:
    windows.serve(_archive(with_python=False))
    with pytest.raises(RuntimeError, match="no python.exe"):
        own_python.ensure_own_python(tmp_path)
    assert not (tmp_path / "python").exists()


def test_the_own_python_goes_first_unless_the_person_chose_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = tmp_path / "python" / "python.exe"
    monkeypatch.setattr(script_env, "ensure_own_python", lambda state: own)
    assert script_env._own_python_first(tmp_path, ["sys"]) == ([str(own), "sys"], "")
    (tmp_path / "script_env_interpreter.txt").write_text("C:/chosen/python.exe", encoding="utf-8")
    assert script_env._own_python_first(tmp_path, ["sys"]) == (["sys"], "")


def test_a_failed_download_falls_back_and_says_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(state: Path) -> Path:
        raise RuntimeError("Could not download Python from x: offline")

    monkeypatch.setattr(script_env, "ensure_own_python", fail)
    candidates, why = script_env._own_python_first(tmp_path, ["sys"])
    assert candidates == ["sys"] and "offline" in why
