"""Prototype for issue #560, part 3: does Codex's own Windows sandbox hold coscribe's folders?

Run on Windows only:

    python scripts/prototype_codex_sandbox.py

Codex describes the folders and the network as a permission profile (config.toml
`[permissions.<name>]`): `":root" = "deny"`, `":minimal" = "read"`, then each folder `read` or
`write`, and `network.enabled = false`. This script writes that profile into a private
CODEX_HOME and runs the probe from prototype_script_sandbox.py through `codex sandbox` under each
Windows implementation Codex has (`mxc`, `elevated`, `unelevated`), then prints one table per
implementation. An implementation that refuses the profile or does not start is a result too:
the issue's fallback is to reduce what the code module may run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

assert sys.platform == "win32", "the Codex sandbox prototype runs on Windows only"

sys.path.insert(0, str(Path(__file__).parent))
import prototype_script_sandbox as box  # noqa: E402

CODEX_VERSION = "0.163.0"
# (implementation, root rule). The first run refused ":root" = "deny" on elevated ("requires
# effective `:root` read access") and any read-only carve-out on unelevated, so the second rule
# reads the disk, denies the user profile and opens the folders inside it again.
RUNS = (
    ("mxc", "deny"),
    ("elevated", "deny"),
    ("unelevated", "deny"),
    ("elevated", "read, profile denied"),
    ("elevated", "read"),
    ("unelevated", "read, all folders write"),
)


def toml_key(path: Path) -> str:
    # A literal string: backslashes stay as they are.
    return f"'{path}'"


def write_config(
    home: Path, impl: str, root: str, rw: Path, ro: Path, readable: list[Path]
) -> None:
    profile = Path(os.environ["USERPROFILE"])
    if root == "deny":
        roots = ['":root" = "deny"', '":minimal" = "read"']
    elif root == "read, profile denied":
        roots = ['":root" = "read"', f'{toml_key(profile)} = "deny"']
    else:
        roots = ['":root" = "read"']
    ro_access = "write" if root == "read, all folders write" else "read"
    lines = [
        'default_permissions = "coscribe"',
        "",
        "[windows]",
        f'sandbox = "{impl}"',
        "",
        "[permissions.coscribe.filesystem]",
        *roots,
        f'{toml_key(rw)} = "write"',
        f'{toml_key(ro)} = "{ro_access}"',
        *(f'{toml_key(p)} = "read"' for p in readable),
        "",
        "[permissions.coscribe.network]",
        "enabled = false",
        "",
    ]
    (home / "config.toml").write_text("\n".join(lines), encoding="utf-8")


def codex(
    exe: Path, home: Path, *args: str, timeout: float = 600
) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"CODEX_HOME": str(home)}
    try:
        return subprocess.run(
            [str(exe), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            exc.cmd, -1, str(exc.stdout or ""), f"timed out after {timeout}s"
        )


def table(output: str) -> tuple[int, int]:
    """Prints the probe's rows against the contract. Returns (rows seen, rows that differ)."""
    rows = {}
    for line in output.splitlines():
        try:
            row = json.loads(line)
            rows[row["check"]] = row
        except (ValueError, KeyError):
            if line.strip():
                print(f"  | {line[:300]}")
    differ = 0
    for check, want in box.EXPECTED.items():
        row = rows.get(check)
        got = None if row is None else row["ok"]
        differ += got != want
        mark = "ok " if got == want else "BAD"
        shown = "-" if got is None else ("allow" if got else "deny")
        print(
            f"{mark} {check:32} {'allow' if want else 'deny':6} {shown:6} {'' if row is None else row['detail'][:160]}"
        )
    return len(rows), differ


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="coscribe-codex-")).resolve()
    tools = base / "codex-bin"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--target",
            str(tools),
            f"openai-codex-cli-bin=={CODEX_VERSION}",
        ],
        check=True,
    )
    exe = next(tools.rglob("codex.exe"))
    venv = base / "script-env"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "Scripts" / "python.exe"
    subprocess.run([str(py), "-m", "pip", "install", "-q", "openpyxl", "pandas"], check=True)

    print(subprocess.run(["cmd", "/c", "ver"], capture_output=True, text=True).stdout.strip())
    home = base / "codex-home"
    home.mkdir()
    print(codex(exe, home, "--version").stdout.strip())
    print(codex(exe, home, "sandbox", "--help").stdout[:1500])

    rw, ro, scratch = base / "workspace", base / "reference", base / "scratch"
    outside = Path(os.environ["USERPROFILE"]) / "coscribe-codex-outside"
    for folder in (rw, ro, scratch, outside):
        folder.mkdir(parents=True, exist_ok=True)
    (ro / "input.txt").write_text("reference", encoding="utf-8")
    probe = scratch / "probe.py"
    probe.write_text(box.PROBE, encoding="utf-8")

    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    cfg = {
        "rw": str(rw),
        "ro": str(ro),
        "outside": str(outside),
        "profile": os.environ["USERPROFILE"],
        "loopback_port": listener.getsockname()[1],
    }
    readable = [venv, Path(sys.base_prefix), scratch]

    summary = {}
    elevated_ready = False
    try:
        for impl, root in RUNS:
            run_name = f"{impl} / root {root}"
            print(f"\n===== windows.sandbox = {impl}, :root {root} =====")
            (outside / "secret.txt").write_text("secret", encoding="utf-8")
            write_config(home, impl, root, rw, ro, readable)
            if impl == "elevated" and not elevated_ready:
                elevated_ready = True
                setup = codex(
                    exe, home, "sandbox", "setup", "--elevated", "--current-user", timeout=300
                )
                print(
                    f"setup --elevated: exit {setup.returncode}\n{(setup.stdout + setup.stderr).strip()[-1200:]}"
                )
            smoke = codex(
                exe,
                home,
                "sandbox",
                "-P",
                "coscribe",
                "-C",
                str(rw),
                "--",
                "cmd.exe",
                "/d",
                "/c",
                "echo SANDBOX_OK",
                timeout=120,
            )
            print(f"smoke: exit {smoke.returncode} {(smoke.stdout + smoke.stderr).strip()[-600:]}")
            if "SANDBOX_OK" not in smoke.stdout:
                summary[run_name] = "did not run a command"
                log = home / ".sandbox" / "sandbox.log"
                if log.exists():
                    print(
                        f"sandbox.log tail:\n{log.read_text(encoding='utf-8', errors='replace')[-1500:]}"
                    )
                continue
            run = codex(
                exe,
                home,
                "sandbox",
                "-P",
                "coscribe",
                "-C",
                str(rw),
                "--",
                str(py),
                str(probe),
                json.dumps(cfg),
            )
            print(f"probe: exit {run.returncode}")
            seen, differ = table(run.stdout + "\n" + run.stderr)
            stray = [p.name for p in outside.iterdir() if p.name != "secret.txt"]
            print(
                f"secret.txt still outside: {(outside / 'secret.txt').exists()}; files left outside: {stray}"
            )
            summary[run_name] = f"{seen} checks ran, {differ} differ from the contract"
            for p in list(rw.iterdir()):
                shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
            for p in outside.iterdir():
                p.unlink(missing_ok=True)
    finally:
        listener.close()
        if elevated_ready:
            print(codex(exe, home, "sandbox", "uninstall", timeout=120).stdout[-400:])
        shutil.rmtree(outside, ignore_errors=True)
        shutil.rmtree(base, ignore_errors=True)

    print("\n===== summary =====")
    for impl, text in summary.items():
        print(f"{impl:40} {text}")
    # Recording, not gating: which implementation holds is the question, not a pass/fail.
    return 0


if __name__ == "__main__":
    sys.exit(main())
