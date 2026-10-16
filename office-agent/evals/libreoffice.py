"""LibreOffice for the evaluation only (decision 0012): the judge and the checks see a produced
file as the pages LibreOffice draws, the same on every machine. Its installer doesn't put
`soffice` on PATH on Windows, so it is also looked for where it installs."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

_PROFILE_ROOT = Path(tempfile.gettempdir()) / "coscribe_lo_profiles"


def find_soffice() -> str | None:
    found = shutil.which("soffice")
    if found:
        return found
    candidates: list[Path] = []
    if sys.platform == "win32":
        for variable in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(variable)
            if base:
                candidates.append(Path(base) / "LibreOffice" / "program" / "soffice.exe")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / "Programs" / "LibreOffice" / "program" / "soffice.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _try_lock(handle: BinaryIO) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle: BinaryIO) -> None:
    if sys.platform == "win32":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def soffice_profile() -> Iterator[str]:
    """The `-env:UserInstallation=...` argument for one soffice run.

    Two soffice processes on one profile don't both work: the second hands
    its job to the first and exits with nothing made (or fails outright), so
    parallel tool calls lost previews and layout checks, and an open
    LibreOffice window blocked them all. Each concurrent run here gets a
    profile of its own; the profiles are kept and reused, since building
    one on first launch can take half a minute on Windows. The claim on a
    profile is an OS file lock, so it holds across processes (the web
    server and a `--check-wakes` run) and lapses if its holder dies."""
    _PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    index = 0
    while True:
        handle = (_PROFILE_ROOT / f"slot{index}.lock").open("a+b")
        if _try_lock(handle):
            break
        handle.close()
        index += 1
    try:
        profile = _PROFILE_ROOT / f"slot{index}"
        profile.mkdir(exist_ok=True)
        yield f"-env:UserInstallation={profile.as_uri()}"
    finally:
        _unlock(handle)
        handle.close()


def convert_to_pdf(file_path: Path, out_dir: Path, timeout: float = 60.0) -> Path | None:
    """`file_path` as a PDF in `out_dir`, or None when LibreOffice is missing or fails."""
    from coscribe.tools._office_bins import run_killable

    soffice = find_soffice()
    if soffice is None:
        return None
    try:
        with soffice_profile() as profile:
            run_killable(
                [
                    soffice,
                    "--headless",
                    profile,
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(out_dir),
                    str(file_path),
                ],
                timeout,
            )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return None
    pdf_path = out_dir / f"{file_path.stem}.pdf"
    return pdf_path if pdf_path.is_file() else None
