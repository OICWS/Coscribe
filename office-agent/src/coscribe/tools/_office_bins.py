"""Running an external program with a timeout that kills everything it started: an office
program launched through a script keeps running after a plain timeout ends the script."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys


def run_killable(
    command: list[str] | str, timeout: float, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """`subprocess.run(command, capture_output=True, timeout=timeout,
    check=True)`, except that a timeout kills the whole process group, not
    only the launcher: a launcher (`soffice`, PowerShell) starts the real
    program, and a plain timeout leaves that running. A string is the command line as
    Windows takes it, for a program like msiexec that reads a quoted `NAME="a b"` itself."""
    if sys.platform == "win32":
        group: dict[str, int | bool] = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        group = {"start_new_session": True}
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        **group,  # type: ignore[call-overload]
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True
                )
            else:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
    return subprocess.CompletedProcess(command, 0, stdout, stderr)
