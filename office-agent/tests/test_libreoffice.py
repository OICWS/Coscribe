"""Finding a LibreOffice (decision 0026): coscribe's own copy first, then an installed one."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from coscribe.tools import find_libreoffice, libreoffice_status
from coscribe.tools import libreoffice as lo

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="fake launchers are shell scripts")


def _launcher(folder: Path, text: str = "LibreOffice 26.8.1.1 abc123") -> Path:
    path = folder / "program" / "soffice"
    path.parent.mkdir(parents=True)
    path.write_text(f'#!/bin/sh\necho "{text}"\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture(autouse=True)
def _nothing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lo.shutil, "which", lambda name: None)
    lo._version_of.cache_clear()


def test_a_computer_without_libreoffice_is_not_an_error(tmp_path: Path) -> None:
    assert find_libreoffice(tmp_path) is None
    assert libreoffice_status(tmp_path) == {
        "found": False,
        "source": None,
        "path": None,
        "version": None,
    }


def test_coscribes_own_copy_is_found_and_reports_its_version(tmp_path: Path) -> None:
    launcher = _launcher(tmp_path / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path) == (launcher, "own")
    assert libreoffice_status(tmp_path) == {
        "found": True,
        "source": "own",
        "path": str(launcher),
        "version": "26.8.1.1",
    }


def test_an_installed_copy_is_found_on_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher(tmp_path / "system")
    monkeypatch.setattr(
        lo.shutil, "which", lambda name: str(launcher) if name == "soffice" else None
    )
    assert find_libreoffice(tmp_path / "state") == (launcher, "system")


def test_own_copy_wins_over_an_installed_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = _launcher(tmp_path / "system")
    monkeypatch.setattr(lo.shutil, "which", lambda name: str(system))
    own = _launcher(tmp_path / "state" / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path / "state") == (own, "own")


def test_the_newest_own_version_is_used(tmp_path: Path) -> None:
    _launcher(tmp_path / "libreoffice" / "25.8.7")
    newest = _launcher(tmp_path / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path) == (newest, "own")


def test_a_copy_that_does_not_start_is_found_without_a_version(tmp_path: Path) -> None:
    _launcher(tmp_path / "libreoffice" / "26.8.1", text="not a version line")
    status = libreoffice_status(tmp_path)
    assert status["found"] and status["version"] is None
