"""Finding a LibreOffice on this computer (decision 0026).

LibreOffice is an optional engine: nothing needs it, so "not found" is a normal answer, not an
error. coscribe's own copy, which Settings downloads on request, comes first, then one the person
installed. The Windows launcher `soffice.exe` is a GUI program that returns at once and opens a
console window for `--version`; `soffice.com` next to it stays attached and prints, so that one is
preferred.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, TypedDict

from ._office_bins import run_killable

_VERSION = re.compile(r"LibreOffice (\d+(?:\.\d+)+)")
# A first start builds a user profile, which takes a while on a slow disk.
_VERSION_TIMEOUT = 30.0

Source = Literal["own", "system"]


class LibreOfficeStatus(TypedDict):
    found: bool
    source: Source | None
    path: str | None
    version: str | None


def own_root(state_dir: Path) -> Path:
    """Where coscribe's own copies live, one folder per version."""
    return Path(state_dir) / "libreoffice"


def _launcher_names() -> tuple[str, ...]:
    return ("soffice.com", "soffice.exe") if sys.platform == "win32" else ("soffice",)


def _in_program_folder(root: Path) -> Iterator[Path]:
    for name in _launcher_names():
        launcher = root / "program" / name
        if launcher.is_file():
            yield launcher
            return


_VERSION_FOLDER = re.compile(r"\d+\.\d+\.\d+")


def version_folders(state_dir: Path) -> list[Path]:
    """The copies on disk, newest first. Only a folder named like a version counts: beside them sit
    a half-unpacked staging folder and the profile LibreOffice builds on its first start."""
    root = own_root(state_dir)
    if not root.is_dir():
        return []
    found = [f for f in root.iterdir() if f.is_dir() and _VERSION_FOLDER.fullmatch(f.name)]
    return sorted(found, key=lambda f: tuple(int(part) for part in f.name.split(".")), reverse=True)


def profile_argument(folder: Path) -> str:
    """Runs use a profile of their own, so they leave the person's LibreOffice settings alone."""
    return f"-env:UserInstallation={folder.resolve().as_uri()}"


def _own_copies(state_dir: Path) -> Iterator[Path]:
    for folder in version_folders(state_dir):
        yield from _in_program_folder(folder)


def _installed_copies() -> Iterator[Path]:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            yield Path(found)
    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(variable)
            if base:
                yield from _in_program_folder(Path(base) / "LibreOffice")


def find_libreoffice(state_dir: Path) -> tuple[Path, Source] | None:
    """The program to run and whose it is, or None when this computer has no LibreOffice."""
    for path in _own_copies(state_dir):
        return path, "own"
    for path in _installed_copies():
        return path, "system"
    return None


@functools.lru_cache(maxsize=8)
def _version_of(path: str, modified_ns: int) -> str | None:
    """`modified_ns` only keys the cache, so a replaced copy is asked again."""
    del modified_ns
    try:
        result = subprocess.run(
            [path, "--headless", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_VERSION_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = _VERSION.search(result.stdout + result.stderr)
    return match.group(1) if match else None


def libreoffice_status(state_dir: Path) -> LibreOfficeStatus:
    """What Settings shows: whether one is found, which, and the version it reports (None when it
    was found but does not start)."""
    found = find_libreoffice(state_dir)
    if found is None:
        return {"found": False, "source": None, "path": None, "version": None}
    path, source = found
    version = _version_of(str(path), path.stat().st_mtime_ns)
    return {"found": True, "source": source, "path": str(path), "version": version}


_LOCK_NAMES = (".lock", "user/.lock")


# The export filter for each format LibreOffice can be asked for; a bare name picks its default.
_FILTERS = {
    "pdf": "pdf",
    "docx": "docx:MS Word 2007 XML",
    "xlsx": "xlsx:Calc MS Excel 2007 XML",
    "pptx": "pptx:Impress MS PowerPoint 2007 XML",
}
# Two runs sharing one profile hand each other their jobs and some convert nothing (#399), and
# coscribe's runs all use one profile of its own.
_RUN_LOCK = threading.Lock()


def run_profile(state_dir: Path) -> Path:
    return own_root(state_dir) / "profile"


def convert_to_pdf(
    launcher: Path, source: Path, outdir: Path, profile: Path, timeout: float = 180.0
) -> Path:
    return _convert(launcher, source, outdir, profile, "pdf", timeout)


def _convert(
    launcher: Path, source: Path, outdir: Path, profile: Path, to_format: str, timeout: float
) -> Path:
    """Convert `source` to `outdir/<name>.<to_format>` and return it.

    On Windows the launcher can return before LibreOffice has done the work (measured on a runner:
    exit 0, no output, no file yet), so this waits for the file and for the profile's lock to go,
    which is when the program has really exited and no longer holds files in its folder.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    run_killable(
        [
            str(launcher),
            profile_argument(profile),
            "--headless",
            "--convert-to",
            _FILTERS[to_format],
            "--outdir",
            str(outdir),
            str(source),
        ],
        timeout,
    )
    target = outdir / f"{source.stem}.{to_format}"
    while time.monotonic() - started < timeout:
        locked = any((profile / name).exists() for name in _LOCK_NAMES)
        if target.is_file() and not locked:
            return target
        time.sleep(0.25)
    raise TimeoutError(f"LibreOffice made no {target.name}")


def convert_with_libreoffice(
    state_dir: Path, source: Path, target: Path, to_format: str, timeout: float
) -> str | None:
    """Write `source` as `to_format` ("pdf", "docx", "xlsx" or "pptx") to `target` with the
    LibreOffice this computer has, in a profile of coscribe's own. Returns "LibreOffice", or None
    when there is none or it cannot write that format. Raises ValueError when it fails."""
    found = find_libreoffice(state_dir)
    if found is None or to_format not in _FILTERS:
        return None
    launcher = found[0]
    profile = run_profile(state_dir)
    with _RUN_LOCK:
        try:
            made = _convert(launcher, source, target.parent, profile, to_format, timeout)
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired, TimeoutError):
            raise ValueError("LibreOffice could not convert this file.") from None
    if made != target:
        os.replace(made, target)
    return "LibreOffice"
