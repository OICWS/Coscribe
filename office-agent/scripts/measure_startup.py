#!/usr/bin/env python3
"""Startup and idle cost of the server (issue #478).

    python scripts/measure_startup.py                 dev server (`python -m coscribe.web.app`)
    python scripts/measure_startup.py --cmd <exe>     the PyInstaller sidecar
    python scripts/measure_startup.py --imports       the 30 slowest imports, by library

Cold start is the time from spawning the process to the first successful `GET /`. The idle
RSS is the process tree's resident memory a minute after that, with no conversation open.
Each run gets a fresh HOME and workspace, so nothing is cached between runs by the app (the
OS file cache is warm after the first run; the first run is reported separately).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "coscribe" / "web" / "static"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _tree_rss_kib(pid: int) -> int:
    """Resident memory of `pid` and its children, read from /proc (Linux) or tasklist (Windows)."""
    if sys.platform == "win32":
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -eq {pid} "
                f"-or $_.ParentProcessId -eq {pid} }} | Measure-Object WorkingSetSize -Sum).Sum",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return int(out) // 1024
    total = 0
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            status = (p / "status").read_text()
        except OSError:
            continue
        ppid = int(re.search(r"PPid:\s+(\d+)", status).group(1))  # type: ignore[union-attr]
        if int(p.name) == pid or ppid == pid:
            m = re.search(r"VmRSS:\s+(\d+) kB", status)
            total += int(m.group(1)) if m else 0
    return total


def run_once(cmd: list[str], idle_s: float) -> tuple[float, int | None]:
    port = _free_port()
    with tempfile.TemporaryDirectory() as tmp:
        env = {
            **os.environ,
            "HOME": tmp,
            "APPDATA": tmp,
            "USERPROFILE": tmp,
            "COSCRIBE_DEFAULT_MODEL": "claude-sonnet-5-5",
            "COSCRIBE_WORKSPACE_ROOT": str(Path(tmp) / "workspace"),
            "ANTHROPIC_API_KEY": "sk-ant-measure-startup",
        }
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            [*cmd, "--port", str(port)],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            url = f"http://127.0.0.1:{port}/"
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f"server exited with {proc.returncode} before ready")
                try:
                    urllib.request.urlopen(url, timeout=1).read()
                    break
                except urllib.error.HTTPError:
                    break  # answered, whatever the status
                except OSError:
                    time.sleep(0.02)
                if time.perf_counter() - t0 > 180:
                    raise RuntimeError("not ready after 180 s")
            ready = time.perf_counter() - t0
            rss = None
            if idle_s >= 0:
                time.sleep(idle_s)
                rss = _tree_rss_kib(proc.pid)
            return ready, rss
        finally:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()


def import_times(module: str, top: int) -> None:
    """The `top` slowest imports by cumulative time, then the total per top-level library."""
    r = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", f"import {module}"],
        capture_output=True,
        text=True,
        check=True,
    )
    rows: list[tuple[int, int, str]] = []
    for line in r.stderr.splitlines():
        m = re.match(r"import time:\s+(\d+) \|\s+(\d+) \| (\s*)(\S+)", line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(4)))
    total = sum(self_us for self_us, _, _ in rows)
    print(f"total self time of all imports: {total / 1000:.0f} ms")
    print(f"\n{top} slowest by cumulative time:")
    for self_us, cum_us, name in sorted(rows, key=lambda r: -r[1])[:top]:
        print(f"  {cum_us / 1000:8.1f} ms cum  {self_us / 1000:8.1f} ms self  {name}")
    per_lib: dict[str, int] = {}
    for self_us, _, name in rows:
        lib = name.split(".")[0]
        per_lib[lib] = per_lib.get(lib, 0) + self_us
    print("\nself time by top-level library:")
    for lib, us in sorted(per_lib.items(), key=lambda kv: -kv[1])[:top]:
        print(f"  {us / 1000:8.1f} ms  {lib}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", nargs="+", default=[sys.executable, "-m", "coscribe.web.app"])
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--idle", type=float, default=60.0, help="seconds to wait before reading RSS")
    ap.add_argument("--imports", metavar="MODULE", nargs="?", const="coscribe.web.app")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.imports:
        import_times(args.imports, args.top)
        return

    made_stub = False
    if not (STATIC / "index.html").exists() and args.cmd[0] == sys.executable:
        # GET / needs a built frontend; the measurement is of the server, not of the bundle.
        STATIC.mkdir(parents=True, exist_ok=True)
        (STATIC / "index.html").write_text("<html><head></head><body>stub</body></html>")
        made_stub = True
    try:
        times: list[float] = []
        rss: list[int] = []
        for i in range(args.runs):
            ready, kib = run_once(args.cmd, args.idle)
            times.append(ready)
            if kib is not None:
                rss.append(kib)
            print(
                f"run {i + 1}: ready {ready:.2f} s, idle RSS {kib and kib // 1024} MiB", flush=True
            )
    finally:
        if made_stub:
            (STATIC / "index.html").unlink()
    out = {
        "ready_s": {"median": statistics.median(times), "min": min(times), "max": max(times)},
        "rss_mib": {
            "median": int(statistics.median(rss)) // 1024,
            "min": min(rss) // 1024,
            "max": max(rss) // 1024,
        }
        if rss
        else None,
        "runs": times,
    }
    print(
        json.dumps(out, indent=2)
        if args.json
        else f"ready median {out['ready_s']['median']:.2f} s "
        f"(range {out['ready_s']['min']:.2f}-{out['ready_s']['max']:.2f}); "
        f"idle RSS median {out['rss_mib'] and out['rss_mib']['median']} MiB"
    )


if __name__ == "__main__":
    main()
