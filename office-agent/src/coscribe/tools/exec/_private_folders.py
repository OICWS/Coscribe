"""The person's private folders, hidden from sandboxed commands (decision 0022, #601).

Codex's elevated sandbox must read ":root", and its setup lets its users read every folder of the
profile. A "deny" entry in the permission profile makes Codex put a deny-read entry for its users
on a folder, and that one holds: an entry coscribe adds itself is reset on the profile's own
folders at each run. Codex grants nothing to a "read" folder inside a denied one, so coscribe
grants its users read on those (an environment's read-only folders, the batch files, programs on
PATH). Codex leaves some of its deny entries behind when they leave the profile, so a ledger
holds every folder denied or granted, written before the change, and turning this off or removing
the sandbox takes them away from what it lists, checking that they are gone."""

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
_LEDGER = Path("command-sandbox") / "private-folders.json"
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


# Where credentials usually are; the profile's top only hides its own files, not its folders.
_CREDENTIAL_FOLDERS = (".ssh", ".aws", ".azure", ".kube", ".docker", ".gnupg")


class GrantFailed(OSError):
    """The sandbox's users could not be let read a folder a command needs."""


def private_folders() -> list[Path]:
    """The folders a sandboxed command may not read while this is on: the person's documents,
    OneDrive, AppData and credential folders. Never a drive's root, which Codex refuses."""
    if sys.platform != "win32":
        return []
    found: list[Path] = []
    profile = os.environ.get("USERPROFILE", "")
    for name in _KNOWN_FOLDERS:
        found.append(_known_folder(name) or Path(profile, name))
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial", "APPDATA", "LOCALAPPDATA"):
        if os.environ.get(var):
            found.append(Path(os.environ[var]))
    if profile:
        found += [Path(profile, name) for name in _CREDENTIAL_FOLDERS]
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


def _key(path: str | Path) -> str:
    return os.path.normcase(str(path))


def _ledger(state_dir: Path) -> dict[str, list[str]]:
    try:
        raw = json.loads((Path(state_dir) / _LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    return {kind: [str(p) for p in raw.get(kind, [])] for kind in ("granted", "denied")}


def _write_ledger(state_dir: Path, ledger: dict[str, list[str]]) -> None:
    # Replaced whole: a torn ledger would forget entries that are still on the folders.
    path = Path(state_dir) / _LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger), encoding="utf-8")
    os.replace(tmp, path)


def _icacls(*args: str) -> str | None:
    """icacls's output, or None when it failed."""
    try:
        done = subprocess.run(
            ["icacls", *args], capture_output=True, text=True, timeout=_ICACLS_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def prepare_folders(
    state_dir: Path, denied: Iterable[Path], given: Iterable[Path], readable: Iterable[Path]
) -> None:
    """Before a command whose profile denies `denied`: records them, takes a deny Codex left on a
    folder now `given` to the environment, and lets the sandbox's users read each of `readable`
    inside a denied folder. Raises GrantFailed when one can't be granted."""
    denied = list(denied)
    with _lock:
        ledger = _ledger(state_dir)
        now = {_key(d) for d in denied}
        given = list(given)
        # Codex's explicit deny would beat its explicit grant on a folder it now writes.
        for before in ledger["denied"]:
            if _key(before) not in now and inside_any(Path(before), given):
                _icacls(before, "/remove:d", SANDBOX_GROUP)
        known_denied = {_key(p) for p in ledger["denied"]}
        ledger["denied"] += [str(d) for d in denied if _key(d) not in known_denied]
        known = {_key(p) for p in ledger["granted"]}
        wanted = [
            f for f in readable if f.is_dir() and inside_any(f, denied) and _key(f) not in known
        ]
        # Written first: a grant cut short still leaves entries to take away.
        ledger["granted"] += [str(f) for f in wanted]
        _write_ledger(state_dir, ledger)
        for folder in wanted:
            if _icacls(str(folder), "/grant", f"{SANDBOX_GROUP}:(OI)(CI)(RX)") is None:
                raise GrantFailed(
                    f"Couldn't let the command sandbox read {folder}, which the command needs "
                    "and which is inside a private folder."
                )


def _still_denied(output: str) -> bool:
    return any(SANDBOX_GROUP.lower() in line.lower() and "(DENY)" in line and "(I)" not in line
               for line in output.splitlines())  # fmt: skip


def release_private_folders(state_dir: Path) -> list[str]:
    """Takes away the grants and the sandbox users' deny entries on every folder in the ledger
    and on today's private folders, so they read as before. The folders it couldn't clear stay
    in the ledger and are returned."""
    with _lock:
        ledger = _ledger(state_dir)
        left: dict[str, list[str]] = {"granted": [], "denied": []}
        for granted in ledger["granted"]:
            if Path(granted).exists() and _icacls(granted, "/remove:g", SANDBOX_GROUP) is None:
                left["granted"].append(granted)
        folders = {_key(p): p for p in [*ledger["denied"], *map(str, private_folders())]}
        for folder in folders.values():
            if not Path(folder).exists():
                continue
            _icacls(folder, "/remove:d", SANDBOX_GROUP)
            after = _icacls(folder)
            if after is None or _still_denied(after):
                left["denied"].append(folder)
        _write_ledger(state_dir, left)
    return [*left["granted"], *left["denied"]]
