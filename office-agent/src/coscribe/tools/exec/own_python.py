"""coscribe's own Python, offered for the script venv on Windows (issues #560, #586).

A system Python can be missing, a Store alias that only opens the Store, or installed where the
scripts' container then has to be granted read (Program Files, another user's AppData). So
Settings > Capabilities offers python-build-standalone's `install_only` build, downloaded into
`<state>/python` and checked against the SHA-256 pinned here, but only when the person asks:
a download nobody chose fails on networks that block GitHub (#586).
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

import httpx

from ...runtime import configured_proxy

# From the release's SHA256SUMS (astral-sh/python-build-standalone, tag 20261021); a new build
# means a new tag, version and hashes together. 3.12, not 3.13: from 3.13 on, Python resolves its
# own path with GetFinalPathNameByHandleW as it starts, which the scripts' container is denied
# (seen on the Windows runner), so every script printed "Failed to find real location" on stderr.
_RELEASE = "20261021"
_VERSION = "3.12.15"
_BUILDS = {
    "AMD64": ("x86_64", "be7f14464d1d66f84429ad27e01f6d1482963afff64a2fb5256b2a51c7b5d398"),
    "ARM64": ("aarch64", "c0660992e1907a8dc31e9069676b1415d585b53f17d0aa7e9075f4b06f38fd65"),
    "x86": ("i686", "490fd9caa3ed15db752379d6fdd0d9a8e8e44e392c3c9c0f274eface439c03ae"),
}
_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    "{release}/cpython-{version}%2B{release}-{arch}-pc-windows-msvc-install_only.tar.gz"
)
_TIMEOUT = 300.0


def _on_windows() -> bool:
    return sys.platform == "win32"


def own_python_path(state_dir: Path) -> Path:
    return state_dir / "python" / "python.exe"


def own_python_offer(state_dir: Path) -> dict[str, object]:
    """What Settings > Capabilities offers: whether this machine has a build, its version, and
    whether it is already here."""
    return {
        "available": download_url() is not None,
        "version": _VERSION,
        "downloaded": own_python_path(state_dir).is_file(),
    }


def download_url() -> tuple[str, str] | None:
    """The build for this Windows machine and its SHA-256, or None where there is none."""
    build = _BUILDS.get(platform.machine())
    if not _on_windows() or build is None:
        return None
    arch, sha256 = build
    return _URL.format(release=_RELEASE, version=_VERSION, arch=arch), sha256


def ensure_own_python(state_dir: Path) -> Path | None:
    """coscribe's own python.exe, downloaded on first use; None off Windows. Raises
    RuntimeError when the download or its check fails, so the caller can say why."""
    python = own_python_path(state_dir)
    if python.is_file():
        return python
    build = download_url()
    if build is None:
        return None
    url, sha256 = build
    state_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="python-download-", dir=state_dir) as work:
        archive = Path(work) / "python.tar.gz"
        digest = hashlib.sha256()
        try:
            with httpx.stream(
                "GET", url, follow_redirects=True, timeout=_TIMEOUT, proxy=configured_proxy(url)
            ) as response:
                response.raise_for_status()
                with archive.open("wb") as out:
                    for chunk in response.iter_bytes():
                        digest.update(chunk)
                        out.write(chunk)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Could not download Python from {url}: {exc}") from exc
        if digest.hexdigest() != sha256:
            raise RuntimeError(f"The Python download from {url} is not the expected file.")
        unpacked = Path(work) / "unpacked"
        with tarfile.open(archive) as tar:
            tar.extractall(unpacked, filter="data")
        if not (unpacked / "python" / "python.exe").is_file():
            raise RuntimeError(f"The Python download from {url} holds no python.exe.")
        # Moved in whole, so a download cut short never looks like an installed Python.
        shutil.rmtree(python.parent, ignore_errors=True)
        shutil.move(str(unpacked / "python"), str(python.parent))
    return python
