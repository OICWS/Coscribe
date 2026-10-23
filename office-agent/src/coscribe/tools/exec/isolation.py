"""What a script may reach, held by Windows instead of by the script (issue #560).

A run is started in one AppContainer (`_appcontainer.py`). Each folder it may use gets an ACE for
a capability derived from the folder's path, written once, when a run first needs it, and kept:
later runs only hold the capability. A run of one conversation holds only its own folders'
capabilities, so another conversation's folder stays closed to it even though the ACE is there.

Rights, per folder:
- read: read and list (`RX`).
- write: read plus create, overwrite and append (`RX,W`), without DELETE. Removing, renaming and
  replace-by-rename are refused by Windows, so a delete can only go through a trusted tool.

Every grant is recorded in `folder-grants.json` before `icacls` writes it, so a crash between the
two leaves an entry that `revoke_all` still removes. Volumes without ACLs (FAT, exFAT) cannot be
closed this way; SMB shares are not reachable from a container at all.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from . import _appcontainer
from ._appcontainer import NETWORK_CAPABILITIES, ContainerProcess, ContainerUnavailable

Access = Literal["read", "write"]

_RIGHTS: dict[Access, str] = {"read": "RX", "write": "RX,W"}
_REGISTRY = "folder-grants.json"
_SELF_TEST = "isolation-self-test.json"
_lock = threading.Lock()


@dataclass(frozen=True)
class Isolation:
    """The folders and the network one run may use. `runtime` is what the interpreter needs to
    start (the venv, its base installation, the npm directory): read only, like `readable`."""

    state_dir: Path
    writable: tuple[Path, ...] = ()
    readable: tuple[Path, ...] = ()
    runtime: tuple[Path, ...] = ()
    network: bool = True


def available() -> bool:
    return sys.platform == "win32"


def capability_name(path: Path, access: Access) -> str:
    key = os.path.normcase(str(path.resolve()))
    return f"coscribe.folder.{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}.{access}"


def _folder_id(path: Path) -> float | None:
    """Tells a folder from one deleted and made again under the same name, which has lost the
    ACE. On Windows `st_ctime` is the creation time."""
    try:
        return path.stat().st_ctime
    except OSError:
        return None


def _icacls(*args: str) -> bool:
    done = subprocess.run(  # noqa: S603 -- fixed program, paths and SIDs we made
        ["icacls", *args, "/Q"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return done.returncode == 0


@dataclass
class _Grant:
    path: str
    access: Access
    capability: str
    sid: str
    folder_id: float | None = None

    def key(self) -> tuple[str, Access]:
        return (os.path.normcase(self.path), self.access)


@dataclass
class FolderGrants:
    """The ACEs coscribe wrote on the person's folders."""

    state_dir: Path
    _grants: dict[tuple[str, Access], _Grant] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        try:
            raw = json.loads((self.state_dir / _REGISTRY).read_text(encoding="utf-8"))
            for entry in raw.get("grants", []):
                grant = _Grant(**entry)
                self._grants[grant.key()] = grant
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        target = self.state_dir / _REGISTRY
        data = {"grants": [vars(g) for g in self._grants.values()]}
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(temp, target)

    def entries(self) -> list[tuple[str, Access]]:
        return [(g.path, g.access) for g in self._grants.values()]

    def ensure(self, path: Path, access: Access) -> tuple[str, bool]:
        """The capability that opens `path`, and whether its ACE is in place. A folder already
        granted costs nothing; a failed grant (no right to change the ACL) is not recorded, so
        the next run tries again."""
        resolved = path.resolve()
        name = capability_name(resolved, access)
        folder_id = _folder_id(resolved)
        with _lock:
            known = self._grants.get((os.path.normcase(str(resolved)), access))
            if known is not None and known.folder_id == folder_id:
                return name, True
            sid = _appcontainer.capability_sid(name)
            grant = _Grant(str(resolved), access, name, sid, folder_id)
            self._grants[grant.key()] = grant
            self._save()
            ok = _icacls(str(resolved), "/grant", f"*{sid}:(OI)(CI)({_RIGHTS[access]})")
            if not ok:
                del self._grants[grant.key()]
                self._save()
            return name, ok

    def revoke(self, path: Path) -> None:
        """Takes both ACEs off a folder the person removed."""
        key = os.path.normcase(str(path.resolve()))
        with _lock:
            for access in ("read", "write"):
                grant = self._grants.get((key, access))
                if grant is None:
                    continue
                # A folder that is gone has no ACE left to remove.
                if (
                    _icacls(grant.path, "/remove:g", f"*{grant.sid}")
                    or not Path(grant.path).exists()
                ):
                    del self._grants[(key, access)]
            self._save()

    def prune(self, keep: Iterable[Path]) -> None:
        """Revokes every folder not in `keep`: the folders some conversation or the settings
        still name. Called at start, it also covers a folder removed while coscribe was off."""
        kept = {os.path.normcase(str(Path(p).resolve())) for p in keep}
        for path in {g.path for g in self._grants.values()}:
            if os.path.normcase(path) not in kept:
                self.revoke(Path(path))

    def revoke_all(self) -> None:
        """For uninstall: leaves no ACE of coscribe's on the person's folders."""
        self.prune(())


def capabilities_for(isolation: Isolation) -> tuple[list[str], list[Path]]:
    """The capabilities a run holds, and the folders whose grant failed (the run cannot reach
    them; the runtime ones may still be readable through the system's own ACL)."""
    grants = FolderGrants(isolation.state_dir)
    names: list[str] = []
    failed: list[Path] = []
    wanted: list[tuple[Path, Access]] = [
        *((p, "write") for p in isolation.writable),
        *((p, "read") for p in (*isolation.readable, *isolation.runtime)),
    ]
    for path, access in wanted:
        if not path.exists():
            continue
        name, ok = grants.ensure(path, access)
        if ok:
            names.append(name)
        else:
            failed.append(path)
    if isolation.network:
        names.extend(NETWORK_CAPABILITIES)
    return names, failed


def start(
    argv: Sequence[str], cwd: str, env: Mapping[str, str], isolation: Isolation
) -> ContainerProcess:
    capabilities, _failed = capabilities_for(isolation)
    return _appcontainer.start(argv, str(Path(cwd).resolve()), env, capabilities)


# ---- Self-test -----------------------------------------------------------------------------

_PROBE = r"""
import json, os, socket, sys
inside, outside = sys.argv[1], sys.argv[2]
def check(name, fn):
    try:
        fn()
        print(json.dumps({"check": name, "ok": True}), flush=True)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        print(json.dumps({"check": name, "ok": False, "detail": detail}), flush=True)
def write(path):
    with open(path, "w") as fh:
        fh.write("x")
check("write inside", lambda: write(os.path.join(inside, "probe.txt")))
check("delete inside", lambda: os.remove(os.path.join(inside, "probe.txt")))
check("write outside", lambda: write(os.path.join(outside, "probe.txt")))
check("read outside", lambda: open(os.path.join(outside, "secret.txt")).read())
check("network", lambda: socket.create_connection(("1.1.1.1", 443), timeout=3).close())
"""

# What each check must do for the isolation to hold.
_EXPECTED = {
    "write inside": True,
    "delete inside": False,
    "write outside": False,
    "read outside": False,
    "network": False,
}


@dataclass(frozen=True)
class SelfTest:
    ok: bool
    # The check that differed, in the words Settings shows; empty when all held.
    failed: str = ""
    detail: str = ""


# Raised when the probe or what it checks changes, so every machine tests again.
_PROBE_REVISION = "1"


def _machine_key(python: Path) -> dict[str, str]:
    return {"windows": platform.version(), "python": str(python), "probe": _PROBE_REVISION}


def self_test(
    state_dir: Path, python: Path, runtime: Sequence[Path], *, fresh: bool = False
) -> SelfTest:
    """Whether a script started by `python` is held to its folders on this machine. Cached until
    Windows, the interpreter or coscribe changes; `fresh` runs it again (Settings' re-test)."""
    if not available():
        return SelfTest(False, "not Windows")
    cache = state_dir / _SELF_TEST
    key = _machine_key(python)
    if not fresh:
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if saved.get("key") == key:
                return SelfTest(**saved["result"])
        except (OSError, ValueError, TypeError, KeyError):
            pass
    result = _run_self_test(state_dir, python, runtime)
    state_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"key": key, "result": vars(result)}), encoding="utf-8")
    return result


def _run_self_test(state_dir: Path, python: Path, runtime: Sequence[Path]) -> SelfTest:
    base = Path(tempfile.mkdtemp(prefix="isolation-test-", dir=state_dir)).resolve()
    inside, outside = base / "inside", base / "outside"
    inside.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("x", encoding="utf-8")
    script = inside / "probe.py"
    script.write_text(_PROBE, encoding="utf-8")
    isolation = Isolation(state_dir, writable=(inside,), runtime=tuple(runtime), network=False)
    try:
        try:
            proc = start(
                [str(python), "-I", str(script), str(inside), str(outside)],
                str(inside),
                {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
                isolation,
            )
            # Both pipes at once: a child blocked on a full stderr would never finish stdout.
            errors: list[bytes] = []
            reader = threading.Thread(target=lambda: errors.append(proc.stderr.read()))
            reader.start()
            out = proc.stdout.read()
            reader.join()
            err = errors[0] if errors else b""
            proc.wait(60)
        except (ContainerUnavailable, OSError, subprocess.TimeoutExpired) as exc:
            return SelfTest(False, "start a script in isolation", str(exc)[:300])
        rows = {}
        for line in out.decode("utf-8", "replace").splitlines():
            try:
                row = json.loads(line)
                rows[row["check"]] = row
            except (ValueError, KeyError):
                continue
        if not rows:
            text = err.decode("utf-8", "replace").strip()
            return SelfTest(False, "start a script in isolation", text[-300:])
        for check, want in _EXPECTED.items():
            row = rows.get(check)
            if row is None or row["ok"] != want:
                detail = "" if row is None else str(row.get("detail", ""))
                return SelfTest(False, check, detail[:300])
        return SelfTest(True)
    finally:
        FolderGrants(state_dir).revoke(inside)
        shutil.rmtree(base, ignore_errors=True)
