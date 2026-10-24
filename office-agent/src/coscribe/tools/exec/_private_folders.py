"""The person's private folders, hidden from sandboxed commands (decision 0022, #601).

Codex's elevated sandbox must read ":root", and its setup lets its users read every folder of the
profile. A "deny" entry in the permission profile makes Codex put a deny-read entry for its users
on a folder, and that one holds: an entry coscribe adds itself is reset on the profile's own
folders at each run. Codex grants nothing to a "read" folder inside a denied one, so coscribe
grants its users read on those (an environment's read-only folders, the batch files, programs on
PATH) and keeps a ledger of them. Codex leaves some of its deny entries behind when they leave the
profile, so turning this off, or removing the sandbox, takes them away here."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterable
from pathlib import Path

# The local group `codex sandbox setup` creates for its sandbox users.
SANDBOX_GROUP = "CodexSandboxUsers"
_LEDGER = Path("command-sandbox") / "read-grants.json"
_ICACLS_SECONDS = 600
_lock = threading.Lock()

# FOLDERID_* GUIDs: these move with OneDrive backup or a person's own redirection.
_KNOWN_FOLDERS = {
    "Documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "Pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "Videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    "Music": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
}


def _known_folder(name: str) -> Path | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class _Guid(ctypes.Structure):
        _fields_ = [
            ("d1", wintypes.DWORD),
            ("d2", wintypes.WORD),
            ("d3", wintypes.WORD),
            ("d4", ctypes.c_ubyte * 8),
        ]

    guid = _Guid()
    ctypes.oledll.ole32.CLSIDFromString(_KNOWN_FOLDERS[name], ctypes.byref(guid))
    out = ctypes.c_wchar_p()
    try:
        ctypes.oledll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out))
    except OSError:
        return None
    try:
        return Path(out.value) if out.value else None
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)


def private_folders() -> list[Path]:
    """The folders a sandboxed command may not read while this is on: the person's documents,
    OneDrive and AppData. Never a drive's root, which Codex refuses to deny."""
    if sys.platform != "win32":
        return []
    found: list[Path] = []
    profile = os.environ.get("USERPROFILE", "")
    for name in _KNOWN_FOLDERS:
        found.append(_known_folder(name) or Path(profile, name))
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial", "APPDATA", "LOCALAPPDATA"):
        if os.environ.get(var):
            found.append(Path(os.environ[var]))
    unique: dict[str, Path] = {}
    for folder in found:
        if folder.is_dir() and folder.parent != folder:
            unique.setdefault(os.path.normcase(str(folder)), folder)
    return list(unique.values())


def inside_any(path: Path, folders: Iterable[Path]) -> bool:
    key = os.path.normcase(os.path.abspath(path))
    for folder in folders:
        root = os.path.normcase(os.path.abspath(folder))
        if key == root or key.startswith(root.rstrip("\\/") + os.sep):
            return True
    return False


def _ledger(state_dir: Path) -> list[str]:
    try:
        raw = json.loads((Path(state_dir) / _LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(p) for p in raw] if isinstance(raw, list) else []


def _write_ledger(state_dir: Path, paths: list[str]) -> None:
    path = Path(state_dir) / _LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(paths), encoding="utf-8")


def _icacls(*args: str) -> bool:
    try:
        done = subprocess.run(
            ["icacls", *args], capture_output=True, timeout=_ICACLS_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def grant_reads(state_dir: Path, folders: Iterable[Path], hidden: Iterable[Path]) -> None:
    """Lets the sandbox's users read each of `folders` that lies inside a `hidden` one. Once per
    folder: the grant is inherited by what is made in it later."""
    hidden = list(hidden)
    with _lock:
        granted = _ledger(state_dir)
        known = {os.path.normcase(p) for p in granted}
        for folder in folders:
            if not folder.is_dir() or not inside_any(folder, hidden):
                continue
            key = os.path.normcase(str(folder))
            if key in known:
                continue
            if _icacls(str(folder), "/grant", f"{SANDBOX_GROUP}:(OI)(CI)(RX)"):
                granted.append(str(folder))
                known.add(key)
        _write_ledger(state_dir, granted)


def release_private_folders(state_dir: Path) -> None:
    """Takes away the grants in the ledger and every deny entry for the sandbox's users on the
    private folders, so they read as before."""
    with _lock:
        for granted in _ledger(state_dir):
            _icacls(granted, "/remove:g", SANDBOX_GROUP)
        for folder in private_folders():
            _icacls(str(folder), "/remove:d", SANDBOX_GROUP)
        _write_ledger(state_dir, [])
