"""coscribe's own LibreOffice, downloaded on request, unpacked and not installed (decision 0026).

The official Windows MSI is fetched into a staging folder, checked against the size and sha256
pinned here, unpacked with `msiexec /a` (which copies the files and installs nothing, so it needs
no administrator rights), trimmed of what a headless conversion never reads, proved by converting
a small Word file, and only then moved into place in one rename. It lives in
`<state_dir>/libreoffice/<version>`; Settings removes it again.
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from ._office_bins import run_killable
from .libreoffice import convert_to_pdf, own_root, version_folders

# The official release, signed by the LibreOffice Build Team key
# C2839ECAD9408FBE9531C3E9F434A1EFAFEEAEA3; the hash is of the file that signature verified.
# The Document Foundation moves a release out of `stable/` once a newer one replaces it, so a
# new version means new pins, not a changed address.
LIBREOFFICE_VERSION = "26.8.1"


class _Pin(TypedDict):
    url: str
    size: int
    sha256: str


_PINS: dict[str, _Pin] = {
    "win32/amd64": {
        "url": "https://download.documentfoundation.org/libreoffice/stable/26.8.1/win/x86_64/"
        "LibreOffice_26.8.1_Win_x86-64.msi",
        "size": 374870016,
        "sha256": "c6298b10cfa1748bcbedad94c62ce771e240e5021bfd6d7a967cd571b04b5312",
    }
}
# What the trimmed copy takes on disk (587 MB measured), and the most it takes while installing:
# the download and the unpacked files exist together until the download is deleted.
INSTALLED_BYTES = 590 * 1024 * 1024
_NEEDED_BYTES = 2200 * 1024 * 1024

_TIMEOUT = 60.0
_CHUNK = 1 << 20
_UNPACK_SECONDS = 900.0
_CHECK_SECONDS = 180.0

# Cut from the unpacked folder (decision 0026): dictionaries, the interface in other languages,
# icon themes, the gallery, templates, help. Word, Excel and PowerPoint files still converted
# with all of it gone; `share/config/soffice.cfg` is not here because they did not without it.
_REMOVE = (
    "share/extensions/dict-*",
    "share/extensions/nlpsolver",
    "share/extensions/wiki-publisher",
    "share/config/images_*",
    "share/gallery",
    "share/template",
    "share/wizards",
    "share/autotext",
    "share/xpdfimport",
    "help",
    "readmes",
    "*.msi",
)
# Folders whose entries are kept only when they are English.
_ENGLISH_ONLY = (
    ("program/resource", "*", True),
    ("share/registry/res", "fcfg_langpack_*", False),
)

logger = logging.getLogger(__name__)

Progress = Callable[[int, int], None]
Step = Callable[[str], None]

# Windows Installer's own words for the codes people hit.
_MSI_CODES = {
    1625: "Windows refused to unpack LibreOffice (code 1625), usually because of a security "
    "policy or security software.",
    1619: "Windows could not open the downloaded package (code 1619).",
    1618: "Another installation is running (code 1618). Try again when it is done.",
}


class LibreOfficeUnavailable(RuntimeError):
    """The message is meant for the person."""


def libreoffice_offer() -> dict[str, str | int] | None:
    """What the download would be on this computer, None where there is none to offer."""
    pins = _PINS.get(_platform_key())
    if pins is None:
        return None
    return {
        "version": LIBREOFFICE_VERSION,
        "download_bytes": pins["size"],
        "installed_bytes": INSTALLED_BYTES,
    }


def _platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "win32" and machine == "x86_64":
        machine = "amd64"
    return f"{sys.platform}/{machine}"


def install_dir(state_dir: Path) -> Path:
    return own_root(state_dir) / LIBREOFFICE_VERSION


def installed(state_dir: Path) -> bool:
    return any(
        (install_dir(state_dir) / "program" / name).is_file()
        for name in ("soffice.com", "soffice.exe")
    )


def remove_libreoffice(state_dir: Path) -> None:
    """Delete coscribe's own copy, every version of it, and the profile it made."""
    shutil.rmtree(own_root(state_dir), ignore_errors=True)


def install_libreoffice(
    state_dir: Path,
    progress: Progress | None = None,
    step: Step | None = None,
    url: str | None = None,
) -> Path:
    """The launcher of coscribe's own LibreOffice, downloading and unpacking it first if this
    version is not there. `url` is a mirror of the same file; the pinned hash still applies."""
    if installed(state_dir):
        return _launcher(install_dir(state_dir))
    pins = _PINS.get(_platform_key())
    if pins is None:
        raise LibreOfficeUnavailable("LibreOffice can be downloaded on 64-bit Windows only.")
    root = own_root(state_dir)
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < _NEEDED_BYTES:
        raise LibreOfficeUnavailable(
            "Installing LibreOffice needs about 2.2 GB of free space for a few minutes; "
            "it takes about 590 MB afterwards."
        )
    say = step or (lambda _name: None)
    staging = Path(tempfile.mkdtemp(prefix=".s-", dir=root))
    try:
        say("download")
        package = staging / "LibreOffice.msi"
        _download(url or pins["url"], pins, package, progress)
        say("unpack")
        unpacked = staging / "u"
        _unpack(package, unpacked)
        package.unlink()
        say("trim")
        trim(unpacked)
        say("check")
        if _too_deep(unpacked):
            raise LibreOfficeUnavailable(
                "The folder Coscribe keeps its data in has too long a path for LibreOffice to run "
                "from. Move Coscribe's data folder somewhere with a shorter path and try again."
            )
        _check(unpacked, state_dir)
        final = install_dir(state_dir)
        shutil.rmtree(final, ignore_errors=True)
        try:
            os.replace(unpacked, final)
        except OSError as exc:
            raise LibreOfficeUnavailable(
                "LibreOffice could not be moved into place. "
                "Close any LibreOffice window and try again."
            ) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    for old in version_folders(state_dir):
        if old.name != LIBREOFFICE_VERSION:
            shutil.rmtree(old, ignore_errors=True)
    return _launcher(install_dir(state_dir))


def _launcher(folder: Path) -> Path:
    # soffice.com stays attached to the console and waits; soffice.exe returns at once.
    for name in ("soffice.com", "soffice.exe"):
        if (folder / "program" / name).is_file():
            return folder / "program" / name
    raise LibreOfficeUnavailable("The downloaded LibreOffice has no program in it.")


_ATTEMPTS = 3


def _download(url: str, pins: _Pin, target: Path, progress: Progress | None) -> None:
    """A mirror or a connection that drops part-way is tried again; a file that arrives whole and
    does not match the pin is not."""
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            digest, done = _fetch(url, pins["size"], target, progress)
        except OSError as exc:
            logger.warning("LibreOffice download attempt %d failed: %r", attempt, exc)
            if attempt == _ATTEMPTS:
                raise LibreOfficeUnavailable(
                    "Could not download LibreOffice: the connection failed or the disk refused "
                    "the file."
                ) from exc
            time.sleep(2.0 * attempt)
            continue
        if done != pins["size"] or digest != pins["sha256"]:
            raise LibreOfficeUnavailable(
                f"The downloaded LibreOffice {LIBREOFFICE_VERSION} does not match the pinned "
                "release (size or sha256), so it was not installed."
            )
        return


def _fetch(url: str, total: int, target: Path, progress: Progress | None) -> tuple[str, int]:
    digest = hashlib.sha256()
    done = 0
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as response, open(target, "wb") as sink:
        while chunk := response.read(_CHUNK):
            digest.update(chunk)
            sink.write(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    return digest.hexdigest(), done


def _unpack(package: Path, target: Path) -> None:
    """`msiexec /a` copies the package's files to `target` and installs nothing."""
    # One string, quoted as msiexec wants: a list would be re-quoted around the whole argument.
    command = f'msiexec.exe /a "{package}" /qn TARGETDIR="{target}"'
    try:
        run_killable(command, _UNPACK_SECONDS)
    except subprocess.CalledProcessError as exc:
        raise LibreOfficeUnavailable(
            _MSI_CODES.get(
                exc.returncode, f"Windows could not unpack LibreOffice (code {exc.returncode})."
            )
        ) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LibreOfficeUnavailable("Windows could not unpack LibreOffice in time.") from exc


def trim(folder: Path) -> None:
    for pattern in _REMOVE:
        for path in folder.glob(pattern):
            _delete(path)
    # Only the entries of the kind that holds a language: files directly in `resource` are not one.
    for relative, pattern, folders in _ENGLISH_ONLY:
        for path in (folder / relative).glob(pattern):
            if path.is_dir() == folders and not path.name.removeprefix("fcfg_langpack_").startswith(
                "en"
            ):
                _delete(path)


def _delete(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


_PDF = b"%PDF"
# Windows stops at 260 characters, a terminating character included, and LibreOffice nests its
# own files deeply: run from a long path (190 characters of test folder) it made no PDF at all.
_MAX_PATH = 259


def _too_deep(folder: Path) -> bool:
    deepest = max((len(str(p.relative_to(folder))) for p in folder.rglob("*")), default=0)
    return len(str(folder)) + 1 + deepest > _MAX_PATH


def _check(folder: Path, state_dir: Path) -> None:
    """Convert a small Word file to PDF with the trimmed copy, so a trim that broke it is found
    here and not by the first document."""
    from docx import Document  # heavy; only an install needs it

    work = Path(tempfile.mkdtemp(prefix="check-", dir=folder.parent))
    try:
        source = work / "check.docx"
        document = Document()
        document.add_paragraph("LibreOffice check")
        document.save(str(source))
        try:
            pdf = convert_to_pdf(_launcher(folder), source, work, work / "profile", _CHECK_SECONDS)
        except (
            subprocess.CalledProcessError,
            OSError,
            subprocess.TimeoutExpired,
            TimeoutError,
        ) as exc:
            # For the server log; the person gets a fixed text.
            deepest = max(len(str(p.relative_to(folder))) for p in folder.rglob("*"))
            logger.warning(
                "LibreOffice check failed: %r files=%s folder_chars=%d deepest_inside=%d",
                exc,
                sorted(p.name for p in work.iterdir()),
                len(str(folder)),
                deepest,
            )
            raise LibreOfficeUnavailable(
                "The downloaded LibreOffice did not convert a test file."
            ) from exc
        if not pdf.read_bytes().startswith(_PDF):
            raise LibreOfficeUnavailable("The downloaded LibreOffice did not convert a test file.")
    finally:
        shutil.rmtree(work, ignore_errors=True)
