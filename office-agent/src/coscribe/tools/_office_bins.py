"""Running an external program with a timeout that kills everything it started: an office
program launched through a script keeps running after a plain timeout ends the script."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import threading
import time


def run_killable(
    command: list[str] | str, timeout: float, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """`subprocess.run(command, capture_output=True, timeout=timeout,
    check=True)`, except that a timeout kills the whole process group, not
    only the launcher: a launcher (`soffice`, PowerShell) starts the real
    program, and a plain timeout leaves that running. A string is the command line as
    Windows takes it, for a program like msiexec that reads a quoted `NAME="a b"` itself."""
    with _start_in_group(command, subprocess.PIPE, env) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(process)
            process.communicate()
            raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
    return subprocess.CompletedProcess(command, 0, stdout, stderr)


def _start_in_group(
    command: list[str] | str, stderr: int, env: dict[str, str] | None
) -> subprocess.Popen[bytes]:
    if sys.platform == "win32":
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=stderr,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=stderr, env=env, start_new_session=True
    )


def kill_tree(process: subprocess.Popen[bytes]) -> None:
    """Ends `process` and everything it started (it was started in a group of its own)."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)


def run_until_marker(
    command: list[str], timeout: float, marker: str, env: dict[str, str] | None = None
) -> subprocess.Popen[bytes] | None:
    """`run_killable`, except that it returns as soon as the program prints `marker` on a line of
    its own: the program, still running, with its output read in the background so it never
    blocks on a full pipe; the caller waits for it or kills its tree. None when the program ended
    first, successfully. Output and errors share one pipe, so a failure's message is the first
    line the program printed."""
    process = _start_in_group(command, subprocess.STDOUT, env)
    lines: list[bytes] = []
    settled = threading.Event()
    saw_marker = False

    def read() -> None:
        nonlocal saw_marker
        assert process.stdout is not None
        for line in process.stdout:
            if line.strip() == marker.encode():
                saw_marker = True
                settled.set()
            else:
                lines.append(line)
        process.wait()
        settled.set()

    threading.Thread(target=read, daemon=True).start()
    deadline = time.monotonic() + timeout
    if not settled.wait(timeout):
        kill_tree(process)
        process.wait()
        raise subprocess.TimeoutExpired(command, timeout)
    if saw_marker:
        return process
    process.wait(max(deadline - time.monotonic(), 0.1))
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, b"", b"".join(lines))
    return None
