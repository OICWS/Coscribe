"""Commands (cmd) in Codex's Windows sandbox (decision 0022).

`codex sandbox` runs a command as a local sandbox user that Codex creates once
(`codex sandbox setup --elevated`, which needs an administrator). That user may write only the
conversation's folders; network is off unless the environment's is Full. It reads what Codex
grants its users, the whole disk, less the person's private folders while Settings ›
Capabilities hides them (`_private_folders.py`); other drives stay readable, so an online command
still goes to the person (`conversation/approvals.py`). Settings ›
Capabilities sets the sandbox up and records here which Codex did it; this module reads that
record and builds the command line, so the tools need nothing from the code module. Elsewhere,
or until it is set up, a command runs as the person.

Without an administrator, the unelevated mode runs a command under the person's own restricted
token: it still writes only the conversation's folders, but reads everything the person can and
is offline only by its environment, so every command in it goes to the person."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ._private_folders import inside_any, prepare_folders

_RECORD = "command-sandbox.json"
# Codex reads permission profiles from config.toml only; each set of folders gets its own,
# named after them, so commands running at once in different environments never share one.
_PROFILES_KEPT = 64
_DEFAULT = "coscribe-default"
# A command's batch file outlives its start only so a slow sandbox can read it.
_COMMAND_FILES_KEPT_SECONDS = 3600
_lock = threading.Lock()
ELEVATED, UNELEVATED = "elevated", "unelevated"


def supported() -> bool:
    return sys.platform == "win32"


def sandbox_home(state_dir: Path) -> Path:
    """The sandbox's own Codex settings, apart from the code module's and the person's."""
    return Path(state_dir) / "command-sandbox" / "codex-home"


def _record_path(state_dir: Path) -> Path:
    return Path(state_dir) / _RECORD


def _read_record(state_dir: Path) -> dict[str, Any]:
    try:
        raw = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def record_sandbox_setup(
    state_dir: Path, codex: Path | None, error: str = "", mode: str = ELEVATED
) -> None:
    """What Settings › Capabilities found when it set the sandbox up (or removed it: None)."""
    path = _record_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"codex": str(codex) if codex else "", "error": error, "mode": mode}
    path.write_text(json.dumps(record), encoding="utf-8")


def sandbox_codex(state_dir: Path) -> Path | None:
    """The Codex that set the sandbox up, while it is set up and still there."""
    if not supported():
        return None
    codex = str(_read_record(state_dir).get("codex") or "")
    return Path(codex) if codex and Path(codex).is_file() else None


def sandbox_mode(state_dir: Path) -> str:
    """ELEVATED (its own users, set up by an administrator) or UNELEVATED (no administrator:
    the person's own restricted token, no denied reads, and offline only by its environment)."""
    return UNELEVATED if _read_record(state_dir).get("mode") == UNELEVATED else ELEVATED


def sandbox_status(state_dir: Path) -> dict[str, str]:
    """ "ready", "off" (never set up, or removed), "failed" (with why) or "unsupported", with
    the mode it was (last) set up in."""
    if not supported():
        return {"state": "unsupported", "detail": "The command sandbox needs Windows."}
    mode = sandbox_mode(state_dir)
    if sandbox_codex(state_dir) is not None:
        return {"state": "ready", "detail": "", "mode": mode}
    error = str(_read_record(state_dir).get("error") or "")
    state = "failed" if error else "off"
    return {"state": state, "detail": error, "mode": mode}


def _toml_key(path: str) -> str:
    return json.dumps(path.replace("\\", "/"))


def _section(name: str, profile: dict[str, Any]) -> str:
    # The elevated sandbox needs ":root" readable.
    lines = [f"[permissions.{name}.filesystem]", '":root" = "read"']
    lines += [f'{_toml_key(p)} = "deny"' for p in profile.get("denied", [])]
    lines += [f'{_toml_key(p)} = "read"' for p in profile["readable"]]
    lines += [f'{_toml_key(p)} = "write"' for p in profile["writable"]]
    lines += ["", f"[permissions.{name}.network]", f"enabled = {json.dumps(profile['network'])}"]
    return "\n".join(lines) + "\n"


def _read_profiles(home: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads((home / "profiles.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _ensure_profile(home: Path, profile: dict[str, Any]) -> str:
    """The name of a profile with exactly these folders and network in `home`'s config.toml,
    added if new."""
    name = "coscribe-" + hashlib.sha256(json.dumps(profile).encode()).hexdigest()[:16]
    with _lock:
        profiles = _read_profiles(home)
        if name in profiles:
            return name
        profiles = {**dict(list(profiles.items())[-(_PROFILES_KEPT - 1) :]), name: profile}
        home.mkdir(parents=True, exist_ok=True)
        (home / "profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
        # Codex refuses a config with profiles and no default (`codex sandbox uninstall` among
        # others); the default may read and write nothing it isn't given.
        none = {"readable": [], "writable": [], "network": False}
        # The mode is part of each profile's name, so a change of mode writes this line anew.
        mode = profile.get("mode", ELEVATED)
        config = f'default_permissions = "{_DEFAULT}"\n\n[windows]\nsandbox = "{mode}"\n\n'
        config += "\n".join(
            _section(key, value) for key, value in {_DEFAULT: none, **profiles}.items()
        )
        tmp = home / "config.toml.tmp"
        tmp.write_text(config, encoding="utf-8")
        os.replace(tmp, home / "config.toml")
    return name


def sandboxed_command(
    state_dir: Path,
    command: str,
    root: Path,
    writable: Sequence[Path],
    readable: Sequence[Path],
    network: bool,
    hidden: Sequence[Path] = (),
    programs: Sequence[Path] = (),
) -> tuple[list[str], dict[str, str]] | None:
    """The argv and environment that run `command` through cmd in the sandbox, in `root`, able
    to write only `writable` and not to read `hidden`, less what it is given and the `programs`
    folders (PATH); None while the sandbox is not set up. Runs icacls the first time a folder
    needs a grant, so call it off the event loop; raises GrantFailed when a grant fails."""
    codex = sandbox_codex(state_dir)
    if codex is None:
        return None
    mode = sandbox_mode(state_dir)
    if mode == UNELEVATED:
        # Codex can't deny a read without its own users.
        hidden = ()
    home = sandbox_home(state_dir)
    script = _command_file(state_dir, command)
    # The person's Temp is in AppData; a command gets its own, apart for each set of folders.
    temp = _temp_folder(state_dir, writable)
    given = [*writable, *readable, script.parent, temp]
    # A folder the environment was given stays readable even when it holds a private one.
    denied = [h for h in hidden if not any(inside_any(h, [g]) for g in given)]
    if hidden:
        prepare_folders(state_dir, denied, given, [*readable, script.parent, *programs])
    folders = {
        "writable": [*(str(p) for p in writable), str(temp)],
        "readable": [*(str(p) for p in readable), str(script.parent)],
        "network": network,
        "denied": [str(p) for p in denied],
        **({"mode": mode} if mode == UNELEVATED else {}),
    }
    profile = _ensure_profile(home, folders)
    argv = [str(codex), "sandbox", "--permission-profile", profile, "-C", str(root), "--"]
    argv += ["cmd.exe", "/d", "/c", str(script)]
    return argv, {"CODEX_HOME": str(home), "TEMP": str(temp), "TMP": str(temp)}


def _temp_folder(state_dir: Path, writable: Sequence[Path]) -> Path:
    key = hashlib.sha256(json.dumps(sorted(str(p) for p in writable)).encode()).hexdigest()[:16]
    folder = Path(state_dir) / "command-sandbox" / "temp" / key
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _command_file(state_dir: Path, command: str) -> Path:
    """`command` as a batch file. Codex quotes each argument for CommandLineToArgvW, so a quote
    in a command line passed as one argument reaches cmd as \\", which cmd doesn't read; a batch
    file keeps the line as typed, %VARIABLES% included. UTF-8 with chcp 65001 keeps non-ASCII
    paths."""
    folder = Path(state_dir) / "command-sandbox" / "commands"
    folder.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - _COMMAND_FILES_KEPT_SECONDS
    for old in folder.glob("*.cmd"):
        with contextlib.suppress(OSError):
            if old.stat().st_mtime < cutoff:
                old.unlink()
    script = folder / f"{uuid.uuid4().hex}.cmd"
    script.write_text(
        f"@echo off\r\nchcp 65001 >nul\r\n{command}\r\n", encoding="utf-8", newline=""
    )
    return script


def warm_up_sandbox(state_dir: Path) -> str:
    """Runs an empty command until one works, at most twice: the first command after setup is
    refused ("Access is denied") while Codex finishes granting its users (seen on the Windows
    runner), so it is not the person's. The error of the last try, or "" once one worked."""
    commands = Path(state_dir) / "command-sandbox" / "commands"
    error = "The command sandbox is not set up."
    for _ in range(2):
        sandboxed = sandboxed_command(state_dir, "rem", commands, [], [], False)
        if sandboxed is None:
            return error
        argv, env = sandboxed
        try:
            done = subprocess.run(
                argv, env={**os.environ, **env}, capture_output=True, text=True, timeout=120
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = f"A test command didn't finish: {exc}"
            continue
        if done.returncode == 0:
            return ""
        lines = (done.stderr or done.stdout).strip().splitlines()
        error = lines[-1] if lines else f"A test command exited with {done.returncode}."
    return error


def sandbox_setup_argv(codex: Path, state_dir: Path) -> list[str]:
    """Creates the sandbox users once. Names the person rather than `--current-user`: when a
    standard user's administrator approves the prompt, setup runs as that administrator."""
    user = os.environ.get("USERNAME", "")
    home = str(sandbox_home(state_dir))
    return [str(codex), "sandbox", "setup", "--elevated", "--user", user, "--codex-home", home]


def sandbox_uninstall_argv(codex: Path) -> list[str]:
    return [str(codex), "sandbox", "uninstall"]


# ERROR_CANCELLED: the administrator prompt was declined.
DECLINED = 1223


def run_as_administrator(argv: list[str], state_dir: Path, timeout: float) -> str:
    """Runs a `codex sandbox` setup or uninstall, which must already run elevated (Codex doesn't
    ask Windows itself); the error to show, or "" when it worked. Unless coscribe runs elevated,
    it goes through RunAs, which shows the administrator prompt; an elevated child's output can't
    be piped back, so it writes a log."""
    home = sandbox_home(state_dir)
    home.mkdir(parents=True, exist_ok=True)
    # The approving administrator's own profile would otherwise be the one Codex sets up.
    env = {"CODEX_HOME": str(home), "USERPROFILE": os.environ.get("USERPROFILE", "")}
    log = home / "administrator.log"
    log.unlink(missing_ok=True)
    if not _elevated():
        argv = _through_run_as(argv, env, log)
    try:
        done = subprocess.run(
            argv, env={**os.environ, **env}, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Codex didn't finish: {exc}"
    if done.returncode == 0:
        return ""
    if done.returncode == DECLINED:
        why = done.stderr.strip()
        return "Windows didn't run it as an administrator" + (f": {why}" if why else ".")
    logged = log.read_text(encoding="utf-8-sig", errors="replace") if log.is_file() else ""
    output = (logged or done.stderr or done.stdout).strip().splitlines()
    return output[-1] if output else f"Codex exited with {done.returncode}."


def _elevated() -> bool:
    if sys.platform != "win32":
        return True
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def _ps(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def _through_run_as(argv: list[str], env: dict[str, str], log: Path) -> list[str]:
    """`argv` in an elevated PowerShell started with RunAs. The elevated process doesn't inherit
    this one's environment, so `env` is set inside it; its output goes to `log`."""
    inner = "".join(f"$env:{key} = {_ps(value)}\n" for key, value in env.items())
    inner += f"$a = @({', '.join(_ps(a) for a in argv[1:])})\n"
    inner += f'& {_ps(argv[0])} @a 2>&1 | ForEach-Object {{ "$_" }} | '
    inner += f"Set-Content -Encoding UTF8 -LiteralPath {_ps(str(log))}\nexit $LASTEXITCODE\n"
    elevated = f"-NoProfile -NonInteractive -EncodedCommand {_encoded(inner)}"
    outer = (
        "try { $p = Start-Process -FilePath powershell.exe -Verb RunAs -Wait -PassThru "
        f"-WindowStyle Hidden -ArgumentList {_ps(elevated)} }} "
        f"catch {{ [Console]::Error.WriteLine($_.Exception.Message); exit {DECLINED} }}\n"
        "exit $p.ExitCode\n"
    )
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", _encoded(outer)]
