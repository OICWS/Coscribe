"""coscribe's own Python, which the script venv is made from on Windows (issue #560).

A system Python can be missing, a Store alias that only opens the Store, or installed where the
scripts' container then has to be granted read (Program Files, another user's AppData). So the
first script venv on Windows is made from python-build-standalone's `install_only` build,
downloaded once into `<state>/python` and checked against the SHA-256 pinned here. An
interpreter the person chose in Settings > Environment still comes first, and a failed download
falls back to the Pythons found on this computer.
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
# means a new tag, version and hashes together.
_RELEASE = "20261021"
_VERSION = "3.13.17"
_BUILDS = {
    "AMD64": ("x86_64", "e10b46d9b03a3a494297f336770f55f86474d683061137b1cf595e12e47bcef5"),
    "ARM64": ("aarch64", "dd7f2c489a30356b02dc0aca8c210400a09952b06a955d432313d605f8850765"),
    "x86": ("i686", "3229c099ee4608e2388444f539d9574d19e3fd65e26528545f5781ed83d7784c"),
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
                "GET", url, follow_redirects=True, timeout=_TIMEOUT, proxy=configured_proxy()
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
