"""A script process the tool waits on, which the person can let go on in the background.

`subprocess.run` cannot be handed over half way, so the two script tools start the process
here instead and pump its output into memory. While a tool call waits, the chat's "Run in
background" button reaches it by the conversation and the script's text (`request_detach`):
the page has no id of the call (an approved call is announced without one), and two equal
scripts running at once in one conversation is not a case worth telling apart. A note the
person writes mid-turn lets go of every script the conversation waits on, so the model reads
it now rather than when the script ends, and a script still running at its time limit is let
go the same way rather than killed. The tool then gives the process to the background-task
store (`tools/bookkeeping/background_tasks.py`) and returns at once.
"""

from __future__ import annotations

import ast
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
from urllib.parse import quote

from .._output_truncation import truncate_script_output
from . import isolation as _isolation
from ._appcontainer import ContainerProcess
from .isolation import Isolation

_CHUNK = 65536
# How long a finished process may keep its pipes open through a child it left running.
_PIPE_GRACE_SECONDS = 5.0
_POLL_SECONDS = 0.1

_RUNNING: dict[tuple[str, str], RunningCommand] = {}


def request_detach(
    thread_id: str,
    script: str | None,
    loop: asyncio.AbstractEventLoop | None,
    why: str = "user",
) -> bool:
    """Whether a command of this conversation was waiting on this script (on any, for `None`).
    `loop` is the one that must hear about the background task later, from the watcher's
    thread; `why` picks what the model is told (`_LET_GO`)."""
    found = False
    for (owner, running), command in list(_RUNNING.items()):
        if owner == thread_id and script in (None, running):
            command.detach(loop, why)
            found = True
    return found


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
        self.why = "user"
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

    def detach(self, loop: asyncio.AbstractEventLoop | None, why: str = "user") -> None:
        self.loop = loop
        self.why = why
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

    def cut_output_dir(self, state_dir: Path) -> Path:
        """Where this conversation's cut script output is kept whole. Its file tools may read
        it (coordinator.py), so the model can search what a cut left out."""
        return Path(state_dir) / "script-output" / quote(self.thread_id, safe="")


@dataclass
class Ran:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    # What the tool returns when the command was let go on in the background.
    detached: dict[str, object] | None = None


_AFTER_LET_GO = (
    " It keeps running and its task shows in the Background tasks panel. When it ends, its "
    "outcome and the end of its output come to you in a message of their own, so don't check it "
    "again and again: go on with other work, or, if you need its result before you can go on, "
    "tell the user what you're waiting for and end your turn."
)
_LET_GO = {
    "user": "The user moved this command to the background.",
    "steer": (
        "The user wrote to you while this ran, so it moved to the background for you to read "
        "their message now; answer it before anything else."
    ),
    "timeout": "It was still running at its time limit of {timeout:g}s, so it moved to the "
    "background.",
}


def _only_waits(script: str, language: str) -> bool:
    """A Python script that does nothing but sleep: the model waiting out time it should have
    spent ending its turn. Moving that to the background would only hide the mistake."""
    if language != "python":
        return False
    try:
        body = ast.parse(script).body
    except SyntaxError:
        return False

    def waits(node: ast.stmt) -> bool:
        if isinstance(node, ast.Import | ast.ImportFrom | ast.Pass):
            return True
        if isinstance(node, ast.While | ast.For):
            return all(waits(inner) for inner in node.body)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            called = node.value.func
            name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", "")
            return name == "sleep"
        return False

    return bool(body) and all(waits(node) for node in body)


def timed_out_result(ran: Ran, timeout: float, keep: Path | None) -> dict[str, object]:
    return {
        "exit_code": None,
        "stdout": truncate_script_output(ran.stdout, keep),
        "stderr": truncate_script_output(ran.stderr, keep, "stderr")
        + f"\n[timed out after {timeout}s]",
        "timed_out": True,
    }


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
    isolation: Isolation | None = None,
) -> Ran:
    command = RunningCommand(argv, cwd, env, isolation)
    # Without a way to hand it over there is nothing for a button to do.
    key = (detachable.thread_id, script) if detachable is not None else None
    if key is not None:
        _RUNNING[key] = command
    try:
        outcome = command.wait(timeout)
        # Let go before it leaves _RUNNING, so a stop that comes now can't miss it.
        if outcome == "timed_out" and key is not None and not _only_waits(script, language):
            command.detach(None, "timeout")
            outcome = "detached"
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
                "note": _LET_GO[command.why].format(timeout=timeout) + _AFTER_LET_GO,
            },
        )
    if outcome == "timed_out":
        command.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            command.wait_exit(_PIPE_GRACE_SECONDS)
        command.finish()
        return Ran(None, command.stdout_text(), command.stderr_text(), timed_out=True)
    return Ran(command.returncode, command.stdout_text(), command.stderr_text())
