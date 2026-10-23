"""A script process the tool waits on, which the person can let go on in the background.

`subprocess.run` cannot be handed over half way, so the two script tools start the process
here instead and pump its output into memory. While a tool call waits, the chat's "Run in
background" button reaches it by the conversation and the script's text (`request_detach`):
the page has no id of the call (an approved call is announced without one), and two equal
scripts running at once in one conversation is not a case worth telling apart. The tool then
gives the process to the background-task store (`tools/bookkeeping/background_tasks.py`) and
returns at once.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from .._output_truncation import truncate_script_output
from . import isolation as _isolation
from ._appcontainer import ContainerProcess
from .isolation import Isolation

_CHUNK = 65536
# How long a finished process may keep its pipes open through a child it left running.
_PIPE_GRACE_SECONDS = 5.0
_POLL_SECONDS = 0.1

_RUNNING: dict[tuple[str, str], RunningCommand] = {}


def request_detach(thread_id: str, script: str, loop: asyncio.AbstractEventLoop | None) -> bool:
    """Whether a command of this conversation is waiting on this script. `loop` is the one that
    must hear about the background task later, from the watcher's thread."""
    command = _RUNNING.get((thread_id, script))
    if command is None:
        return False
    command.detach(loop)
    return True


def stop_commands(thread_id: str) -> None:
    """Ends the scripts a conversation's tool calls are still waiting on: stopping the turn
    cannot reach a tool's worker thread, which would sit on its process until it ended. Their
    tool calls then return, with the output so far. A script let go on in the background is
    no longer waited on and is stopped from its own panel."""
    for (owner, _script), command in list(_RUNNING.items()):
        if owner == thread_id:
            command.kill()


class RunningCommand:
    def __init__(
        self,
        argv: Sequence[str],
        cwd: str,
        env: Mapping[str, str],
        isolation: Isolation | None = None,
    ) -> None:
        self._proc: subprocess.Popen[bytes] | ContainerProcess
        if isolation is not None:
            self._proc = _isolation.start(argv, cwd, env, isolation)
        else:
            self._proc = subprocess.Popen(  # noqa: S603 -- the argv the approved script was given
                list(argv),
                cwd=cwd,
                env=dict(env),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Its own process group on POSIX, so a stop reaches what the script started.
                start_new_session=sys.platform != "win32",
            )
        self.loop: asyncio.AbstractEventLoop | None = None
        self.output_so_far = ""
        self._lock = threading.Lock()
        self._stdout = bytearray()
        self._stderr = bytearray()
        # Both streams in the order they arrived: a background log is one stream.
        self._written = bytearray()
        self._log: BinaryIO | None = None
        self._detached = threading.Event()
        self._pumps = [
            threading.Thread(
                target=self._pump, args=(self._proc.stdout, self._stdout), daemon=True
            ),
            threading.Thread(
                target=self._pump, args=(self._proc.stderr, self._stderr), daemon=True
            ),
        ]
        for pump in self._pumps:
            pump.start()

    @property
    def pid(self) -> int:
        return self._proc.pid

    @property
    def returncode(self) -> int | None:
        return self._proc.returncode

    def _pump(self, stream: Any, own: bytearray) -> None:
        # read1, not read: a plain read waits for a full chunk and holds a short line back.
        while chunk := stream.read1(_CHUNK):
            with self._lock:
                if self._log is None:
                    own += chunk
                    self._written += chunk
                else:
                    self._log.write(chunk)
                    self._log.flush()

    def stdout_text(self) -> str:
        with self._lock:
            return bytes(self._stdout).decode("utf-8", errors="replace").replace("\r\n", "\n")

    def stderr_text(self) -> str:
        with self._lock:
            return bytes(self._stderr).decode("utf-8", errors="replace").replace("\r\n", "\n")

    def detach(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self.loop = loop
        self._detached.set()

    def wait(self, timeout: float) -> str:
        """`exited`, `detached` or `timed_out`, whichever comes first (an exit wins a tie)."""
        deadline = time.monotonic() + timeout
        while True:
            if self._proc.poll() is not None:
                self.finish()
                return "exited"
            if self._detached.is_set():
                return "detached"
            left = deadline - time.monotonic()
            if left <= 0:
                return "timed_out"
            self._detached.wait(min(left, _POLL_SECONDS))

    def wait_exit(self, timeout: float) -> int:
        """Raises `subprocess.TimeoutExpired`."""
        code = self._proc.wait(timeout)
        self.finish()
        return code

    def finish(self) -> None:
        for pump in self._pumps:
            pump.join(_PIPE_GRACE_SECONDS)
        with self._lock:
            if self._log is not None:
                self._log.close()
                self._log = None

    def adopt(self, log_path: Path) -> None:
        """From here on the output goes to this file; what came so far is its start, and is
        kept as `output_so_far`."""
        with self._lock:
            so_far = bytes(self._written)
            log = log_path.open("wb")
            log.write(so_far)
            log.flush()
            self._log = log
            self._stdout.clear()
            self._stderr.clear()
            self._written.clear()
        self.output_so_far = so_far.decode("utf-8", errors="replace").replace("\r\n", "\n")

    def kill(self) -> None:
        """The whole tree: a script's children outlive a kill of the script alone."""
        if sys.platform == "win32":
            subprocess.run(  # noqa: S603 -- fixed arguments, a pid we started
                ["taskkill", "/F", "/T", "/PID", str(self._proc.pid)],
                capture_output=True,
                check=False,
            )
            return
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self._proc.pid, signal.SIGKILL)


# (conversation, command, language, description, scratch directory) -> the new background
# task's id. The scratch directory goes with the process: it is removed when the process ends.
HandOff = Callable[[str, RunningCommand, str, str, Path], str]


@dataclass(frozen=True)
class Detachable:
    """What a script tool needs to let a command go on in the background: the conversation it
    belongs to and the way to give it to that conversation's background tasks."""

    thread_id: str
    hand_off: HandOff


@dataclass
class Ran:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    # What the tool returns when the command was let go on in the background.
    detached: dict[str, object] | None = None


def run_to_end(
    argv: Sequence[str],
    cwd: str,
    env: Mapping[str, str],
    timeout: float,
    *,
    language: str,
    description: str,
    script: str,
    scratch_dir: Path,
    detachable: Detachable | None,
) -> Ran:
    command = RunningCommand(argv, cwd, env)
    # Without a way to hand it over there is nothing for a button to do.
    key = (detachable.thread_id, script) if detachable is not None else None
    if key is not None:
        _RUNNING[key] = command
    try:
        outcome = command.wait(timeout)
    finally:
        if key is not None and _RUNNING.get(key) is command:
            del _RUNNING[key]
    if outcome == "detached":
        assert detachable is not None  # only registered with one
        task_id = detachable.hand_off(
            detachable.thread_id, command, language, description, scratch_dir
        )
        so_far = command.output_so_far
        return Ran(
            None,
            "",
            "",
            detached={
                "status": "running_in_background",
                "task_id": task_id,
                "output_so_far": truncate_script_output(so_far),
                "note": (
                    "The user moved this command to the background. It keeps running and its "
                    "task shows in the Background tasks panel; read its output with "
                    "check_background_task."
                ),
            },
        )
    if outcome == "timed_out":
        command.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            command.wait_exit(_PIPE_GRACE_SECONDS)
        command.finish()
        return Ran(None, command.stdout_text(), command.stderr_text(), timed_out=True)
    return Ran(command.returncode, command.stdout_text(), command.stderr_text())
