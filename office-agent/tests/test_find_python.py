"""The Pythons offered in Settings > Environment (tools/exec/find_python.py, #586)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from coscribe.tools.exec import find_python, own_python


def test_each_python_that_runs_is_offered_once_with_its_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_alias = r"C:\Users\a\AppData\Local\Microsoft\WindowsApps\python.exe"
    candidates = [sys.executable, sys.executable, store_alias, str(tmp_path / "missing.exe")]
    monkeypatch.setattr(find_python, "_candidates", lambda state_dir: iter(candidates))
    found = find_python.find_pythons(tmp_path)
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert found == [{"path": sys.executable, "version": version}]


def test_coscribe_s_own_python_comes_first_once_downloaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(find_python.shutil, "which", lambda name: None)
    assert next(find_python._candidates(tmp_path)) != str(own_python.own_python_path(tmp_path))
    own = own_python.own_python_path(tmp_path)
    own.parent.mkdir(parents=True)
    own.write_bytes(b"")
    assert next(find_python._candidates(tmp_path)) == str(own)


def test_the_launcher_s_list_gives_its_paths() -> None:
    listing = (
        " -V:3.13 *        C:\\Users\\a\\AppData\\Local\\Programs\\Python\\Python313\\python.exe\n"
        " -V:3.11          C:\\Program Files\\Python311\\python.exe\n"
        " -3.9-64          C:\\Python39\\python.exe\n"
        "No other line names a path\n"
    )
    assert list(find_python.launcher_paths(listing)) == [
        "C:\\Users\\a\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
        "C:\\Program Files\\Python311\\python.exe",
        "C:\\Python39\\python.exe",
    ]


def test_the_usual_folders_are_searched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local, roaming = tmp_path / "local", tmp_path / "roaming"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "programdata"))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "programfiles"))
    monkeypatch.setattr(find_python.Path, "home", lambda: tmp_path / "home")
    installs = [
        local / "Programs" / "Python" / "Python312" / "python.exe",
        roaming / "uv" / "python" / "cpython-3.12.4-windows-x86_64-none" / "python.exe",
        tmp_path / "home" / "miniconda3" / "python.exe",
    ]
    for exe in installs:
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
    assert sorted(find_python._usual_folders()) == sorted(str(exe) for exe in installs)


def test_python_2_and_a_program_that_is_not_python_are_left_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Ran:
        def __init__(self, out: str, code: int = 0) -> None:
            self.stdout, self.stderr, self.returncode = out, "", code

    answers = {"py2": Ran("Python 2.7.18"), "server": Ran("usage: coscribe-server", 2)}
    monkeypatch.setattr(find_python.subprocess, "run", lambda argv, **kw: answers[argv[0]])
    assert find_python.python_version("py2") is None
    assert find_python.python_version("server") is None
