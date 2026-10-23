"""``run_python_script`` -- one of two tools in this package classified
``risk_category="EXEC"`` (see ``tools/exec/node_scripts.py`` for the other).

**Isolation where the machine allows it** (decision 0021). On Windows, when
the self-test passed, the script runs in an AppContainer (`isolation.py`)
that reaches only the conversation's folders: read-only ones `RX`, read-write
ones without delete or rename, and a child process inherits that. Elsewhere,
or when the self-test failed, the approval prompt showing the full script
text is the safety mechanism, and `script_guard.py` refuses writes outside
the folders: a guard rail against a model's mistakes, not a boundary, since
code calling the operating system directly gets past it.

Deliberately no import/library allowlist either, for the same reason
Claude Code's own Bash tool doesn't restrict what commands can run: any such
restriction is trivially bypassable (``__import__``, ``importlib``,
``subprocess.run(["pip", "install", ...])``) and would only offer a false
sense of security while blocking legitimate use. The one thing this *does*
control -- deliberately, and for a different reason -- is which Python
environment the script runs in: ``tools/exec/script_env.py``'s dedicated venv,
kept separate from coscribe's own runtime dependencies so a script
installing a package can't destabilize the agent itself. See that module's
docstring.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ...runtime import tool_metadata
from .._files_written import snapshot_workspace, with_files_written
from .._output_truncation import truncate_script_output
from .isolation import denied_note, for_scripts, scratch_root
from .running import Detachable, run_to_end
from .script_env import ensure_script_env, overlay_env, venv_python
from .script_guard import (
    blocked_write,
    locked_file_note,
    refusal_note,
    suggested_folder,
    writable_roots,
    write_python_wrapper,
)

# Matches Claude Code's own Bash tool exactly -- a default long enough for
# real data-processing work, capped short enough that an approved-but-
# runaway script can't hang a session indefinitely. Not guessed: this is
# the live, already-battle-tested balance that tool's own description
# documents (120s default, 600s/10min hard cap).
_DEFAULT_TIMEOUT = 120.0
_MAX_TIMEOUT = 600.0


def _run_python_script(
    workspace_root: Path,
    state_dir: Path,
    script: str,
    timeout: float,
    extra_writable: Sequence[Path] = (),
    session_env: Mapping[str, str] | None = None,
    detachable: Detachable | None = None,
    description: str = "",
    extra_readable: Sequence[Path] = (),
) -> dict[str, object]:
    timeout = min(max(timeout, 1.0), _MAX_TIMEOUT)
    venv_dir = ensure_script_env(state_dir)
    python = venv_python(venv_dir)
    isolation = for_scripts(
        state_dir,
        writable=[workspace_root, *extra_writable],
        readable=extra_readable,
        thread_id=detachable.thread_id if detachable else None,
    )

    scratch_dir = Path(tempfile.mkdtemp(prefix="coscribe_script_", dir=scratch_root(state_dir)))
    script_path = scratch_dir / "script.py"
    script_path.write_text(script, encoding="utf-8")
    # Windows has no UTF-8-by-default here: neither Path.write_text nor a
    # child process's own stdio pick it up automatically the way they do on
    # macOS/Linux (PEP 538/540's UTF-8 mode is opt-in via PYTHONUTF8, not a
    # Windows default). Without both of these, a script containing (or
    # printing) non-Latin1 text -- e.g. a Chinese comment or print() --
    # fails with `'charmap' codec can't encode characters ...`: cp1252/
    # cp936 (the console codepage) has no slot for most CJK text, so either
    # the write above or the child's own stdout write raises. This was a
    # real, live-reported failure on the user's Windows test machine.
    # Bytecode and font caches would be writes outside the allowed folders.
    child_env = {
        # The user's variables for this conversation come before what the
        # script runner itself needs, which they must not be able to undo.
        **overlay_env(os.environ, session_env),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "MPLCONFIGDIR": str(scratch_dir),
    }
    if isolation is not None:
        # The system temp folder is outside what the container may reach.
        child_env |= {"TEMP": str(scratch_dir), "TMP": str(scratch_dir)}
    wrapper, guard_config = write_python_wrapper(
        scratch_dir, writable_roots(workspace_root, [*extra_writable, scratch_dir])
    )
    before = snapshot_workspace(workspace_root)
    # A command let go on in the background owns the scratch directory from then on.
    handed_over = False
    try:
        ran = run_to_end(
            [str(python), str(wrapper), str(guard_config), str(script_path)],
            str(workspace_root),
            child_env,
            timeout,
            language="python",
            description=description,
            script=script,
            scratch_dir=scratch_dir,
            detachable=detachable,
            isolation=isolation,
        )
        if ran.detached is not None:
            handed_over = True
            return ran.detached
        if ran.timed_out:
            timeout_note = f"\n[timed out after {timeout}s]"
            timed_out: dict[str, object] = {
                "exit_code": None,
                "stdout": truncate_script_output(ran.stdout),
                "stderr": truncate_script_output(ran.stderr) + timeout_note,
                "timed_out": True,
            }
            return with_files_written(timed_out, before, workspace_root)
        blocked, stderr = blocked_write(ran.stderr)
        finished: dict[str, object] = {
            "exit_code": ran.returncode,
            "stdout": truncate_script_output(ran.stdout),
            "stderr": truncate_script_output(
                stderr
                + (refusal_note(blocked) if blocked else "")
                + locked_file_note(stderr)
                + (denied_note(stderr) if isolation is not None else "")
            ),
            "timed_out": False,
        }
        if blocked:
            finished["blocked_write"] = blocked
            folder = suggested_folder(blocked)
            if folder:
                finished["blocked_folder"] = folder
        return with_files_written(finished, before, workspace_root)
    finally:
        if not handed_over:
            shutil.rmtree(scratch_dir, ignore_errors=True)


def build_script_tools(
    workspace_root: str | Path,
    state_dir: str | Path,
    *,
    extra_writable: Sequence[str | Path] = (),
    extra_readable: Sequence[str | Path] = (),
    session_env: Callable[[], Mapping[str, str]] | None = None,
    detachable: Detachable | None = None,
) -> list[Callable[..., Any]]:
    """Return the tool callables the Coordinator agent can call. `state_dir`
    is required (not optional like other tools' preview support) -- the
    script-env venv this tool depends on has nowhere else to live."""
    root = Path(workspace_root)
    state = Path(state_dir)
    folders = [Path(p) for p in extra_writable]
    readable = [Path(p) for p in extra_readable]

    def run_python_script(
        script: str, description: str, timeout: float = _DEFAULT_TIMEOUT
    ) -> dict[str, object]:
        """Run a Python script and return its output. The ONLY tool that
        executes arbitrary code. On Windows, when this computer passed
        coscribe's isolation check, the script runs isolated: it can read the
        workspace and the folders added to this conversation, and write in the
        workspace and the read-write ones, but cannot delete, rename or move
        files there, nor reach any other folder; use delete_file or move_file
        for those. It has the network only if the user gave this conversation
        full network access; fetch with the web tools otherwise. If the check
        failed, the run is refused unless the user allowed it; unisolated, only
        writes outside those folders are refused. A refused
        write is named in the result's `blocked_write` -- then write inside the
        workspace, or ask the user to add that folder. It runs with its working
        directory set to the workspace root, so relative paths land there.

        Runs against a dedicated Python environment (not the one
        coscribe itself runs on) that already has openpyxl, python-docx,
        python-pptx, pandas, and pdfplumber available -- the same libraries
        this package's own document/spreadsheet/presentation tools use, so
        a script can read/write .xlsx/.docx/.pptx files the same way they
        do, just with arbitrary Python logic (loops, pandas, multi-step
        calculations) instead of one fixed tool call. Reach for this when a
        task doesn't fit the built-in document/spreadsheet/presentation
        tools' shape -- e.g. processing thousands of rows, or a multi-step
        transformation those tools can't express in one call. Any other
        package the script needs must already be installed in that
        environment (the user manages this from the Environment settings
        tab) -- `import` a package that isn't there and the script will
        fail with the normal Python ModuleNotFoundError; this tool cannot
        install packages on its own.

        `description` is a short, plain-language summary of what the
        script does (e.g. "Sum the Revenue column in sales.xlsx and print
        the total") -- shown alongside the script text wherever this call
        is presented for approval, so someone who doesn't read Python can
        still tell what's about to run.

        Args:
            script: the complete Python source to run
            description: one sentence, plain language, what this script does
            timeout: seconds to allow before killing the script (capped at 600)
        """
        return _run_python_script(
            root,
            state,
            script,
            timeout,
            folders,
            session_env() if session_env else None,
            detachable,
            description,
            readable,
        )

    return [
        tool_metadata(run_python_script, risk_category="EXEC", category="scripts"),
    ]
