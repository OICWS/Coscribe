import codecs
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from coscribe.tools.exec import script_guard
from coscribe.tools.exec.script_guard import (
    PYTHON_WRAPPER,
    blocked_write,
    locked_file_note,
    node_guard_args,
    refusal_note,
    suggested_folder,
    without_guard_warnings,
    writable_roots,
    write_python_wrapper,
)


def _run_python(tmp_path: Path, script: str, allowed: Path) -> subprocess.CompletedProcess[str]:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    wrapper, config = write_python_wrapper(scratch, [str(allowed.resolve())])
    script_path = scratch / "script.py"
    script_path.write_text(script, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(wrapper), str(config), str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(allowed),
    )


def test_python_guard_allows_writes_inside_the_allowed_folder(tmp_path: Path) -> None:
    allowed = tmp_path / "ws"
    allowed.mkdir()
    done = _run_python(
        tmp_path,
        f"import os\nos.makedirs({str(allowed / 'sub')!r})\n"
        f"open({str(allowed / 'sub' / 'a.txt')!r}, 'w').write('x')\nprint('ok')",
        allowed,
    )
    assert done.returncode == 0, done.stderr
    assert (allowed / "sub" / "a.txt").read_text() == "x"


@pytest.mark.parametrize(
    "statement",
    [
        "open({out!r}, 'w').write('x')",
        "open({out!r}, 'ab').write(b'x')",
        "import pathlib; pathlib.Path({out!r}).write_text('x')",
        "import shutil; shutil.copy({inside!r}, {out!r})",
        "import os; os.rename({inside!r}, {out!r})",
        "import os; os.mkdir({out!r})",
        "import os; os.remove({victim!r})",
    ],
)
def test_python_guard_refuses_writes_outside_and_names_the_path(
    tmp_path: Path, statement: str
) -> None:
    allowed = tmp_path / "ws"
    allowed.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (allowed / "in.txt").write_text("in")
    victim = outside / "victim.txt"
    victim.write_text("keep")
    target = outside / "out.txt"
    script = statement.format(out=str(target), inside=str(allowed / "in.txt"), victim=str(victim))
    done = _run_python(tmp_path, script, allowed)

    assert done.returncode != 0
    path, stderr = blocked_write(done.stderr)
    assert path is not None and Path(path).parent == outside
    assert "COSCRIBE_BLOCKED_WRITE" not in stderr
    assert victim.read_text() == "keep"
    assert not target.exists()


def test_python_guard_reports_a_refusal_the_script_handled_and_leaves_reads_alone(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "ws"
    allowed.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "data.txt").write_text("readable")
    done = _run_python(
        tmp_path,
        f"print(open({str(outside / 'data.txt')!r}).read())\n"
        f"try:\n    open({str(outside / 'x.txt')!r}, 'w')\n"
        "except PermissionError:\n    print('handled')",
        allowed,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["readable", "handled"]
    path, _ = blocked_write(done.stderr)
    assert path is not None and Path(path).name == "x.txt"


def test_writable_roots_include_the_workspace_added_folders_and_temp(tmp_path: Path) -> None:
    extra = tmp_path / "extra"
    extra.mkdir()
    roots = writable_roots(tmp_path / "ws", [extra])
    assert str((tmp_path / "ws").resolve()) in roots
    assert str(extra.resolve()) in roots
    assert len(roots) == len(set(roots)) == 3


def test_blocked_write_reads_a_node_permission_error() -> None:
    stderr = (
        "node:fs:2400\n  Error: Access to this API has been restricted. Use --allow-fs-write\n"
        "{\n  code: 'ERR_ACCESS_DENIED',\n  permission: 'FileSystemWrite',\n"
        "  resource: 'C:\\\\Users\\\\me\\\\out.txt'\n}\n"
    )
    path, kept = blocked_write(stderr)
    assert path == "C:\\Users\\me\\out.txt"
    assert kept == stderr


def test_guard_warnings_are_dropped_from_node_stderr() -> None:
    # Node 20 spells the switch --experimental-permission and warns about it
    # on every run; newer Nodes warn once per --allow-* flag instead.
    stderr = (
        "(node:2695) ExperimentalWarning: Permission is an experimental feature"
        " and might change at any time\n"
        "(node:2695) SecurityWarning: The flag --allow-child-process must be used"
        " with extreme caution.\n"
        "(Use `node --trace-warnings ...` to show where the warning was created)\n"
        "real error\n"
    )
    assert without_guard_warnings(stderr) == "real error\n"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_guard_limits_writes_when_this_node_has_a_permission_model(tmp_path: Path) -> None:
    node = shutil.which("node") or "node"
    allowed = tmp_path / "ws"
    allowed.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    guard = node_guard_args(node, [str(allowed.resolve())])
    if guard is None:
        pytest.skip("this Node has no permission model")
    script = tmp_path / "s.js"
    script.write_text(
        "const fs = require('fs');\n"
        f"fs.writeFileSync({str(allowed / 'a.txt')!r}, 'x');\n"
        f"fs.writeFileSync({str(outside / 'b.txt')!r}, 'x');\n",
        encoding="utf-8",
    )
    done = subprocess.run([node, *guard, str(script)], capture_output=True, text=True)

    assert done.returncode != 0
    assert (allowed / "a.txt").exists() and not (outside / "b.txt").exists()
    path, _ = blocked_write(done.stderr)
    assert path is not None and Path(path).name == "b.txt"


def test_suggested_folder_is_the_nearest_existing_one_but_never_a_drive_or_home(
    tmp_path: Path,
) -> None:
    (tmp_path / "reports").mkdir()
    nested = tmp_path / "reports" / "new" / "a.xlsx"
    assert suggested_folder(str(nested)) == str(tmp_path / "reports")
    (tmp_path / "reports" / "a.xlsx").write_text("x")
    assert suggested_folder(str(tmp_path / "reports" / "a.xlsx")) == str(tmp_path / "reports")
    assert suggested_folder(str(Path.home() / "a.xlsx")) is None
    assert suggested_folder(str(Path(tmp_path.anchor) / "a.xlsx")) is None


@pytest.mark.parametrize(
    "stderr",
    [
        'Traceback (most recent call last):\n  File "x.py", line 3, in <module>\n'
        "PermissionError: [Errno 13] Permission denied: 'C:\\\\Users\\\\a\\\\report.xlsx'",
        "PermissionError: [WinError 32] The process cannot access the file because it is "
        "being used by another process: 'C:\\\\Users\\\\a\\\\report.xlsx'",
    ],
)
def test_locked_file_note_names_the_file_and_says_to_ask_the_user(stderr: str) -> None:
    note = locked_file_note(stderr)

    assert "report.xlsx" in note
    assert "open in another program" in note


def test_locked_file_note_stays_quiet_for_other_errors() -> None:
    assert locked_file_note("ValueError: bad input") == ""
    assert locked_file_note("") == ""


def test_the_python_wrapper_and_its_config_are_written_beside_the_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str | None] = []
    real_write = Path.write_text

    def write_text(self: Path, data: str, encoding: str | None = None, **kw: object) -> int:
        seen.append(encoding)
        return real_write(self, data, encoding=encoding, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", write_text)

    wrapper, config = write_python_wrapper(tmp_path, ["/work/空间", "/tmp"])

    assert (wrapper, config) == (tmp_path / "guard_runner.py", tmp_path / "guard.json")
    assert wrapper.read_text(encoding="utf-8") == PYTHON_WRAPPER
    assert json.loads(config.read_text(encoding="utf-8")) == {"write": ["/work/空间", "/tmp"]}
    assert len(seen) == 2
    assert all(e is not None and codecs.lookup(e).name == "utf-8" for e in seen), seen


class _ScriptedNode:
    """Stands in for `subprocess.run` while probing a Node: each call gets the next return code
    (or exception) and is recorded."""

    def __init__(self, outcomes: list[int | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((args, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if kwargs.get("check") and outcome != 0:
            raise subprocess.CalledProcessError(outcome, args)
        return subprocess.CompletedProcess(args, outcome)


_ALLOWANCES = ["--allow-fs-read=*", "--allow-child-process", "--allow-worker"]


def test_probing_a_node_runs_each_flag_set_until_one_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _ScriptedNode([1, 2, 0])
    monkeypatch.setattr(script_guard.subprocess, "run", fake)

    flags = script_guard._probe_node_flags("/usr/bin/node")

    assert flags == (
        "--experimental-permission",
        "--disable-warning=ExperimentalWarning",
        "--disable-warning=SecurityWarning",
        *_ALLOWANCES,
    )
    assert [args for args, _ in fake.calls] == [
        ["/usr/bin/node", "--permission", "--allow-addons", *_ALLOWANCES, "-e", ""],
        ["/usr/bin/node", "--permission", *_ALLOWANCES, "-e", ""],
        ["/usr/bin/node", *flags, "-e", ""],
    ]
    assert all(
        kwargs == {"capture_output": True, "timeout": 20, "check": False}
        for _, kwargs in fake.calls
    )


def test_probing_a_node_gives_none_when_no_flag_set_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _ScriptedNode([1, 1, 1, 1])
    monkeypatch.setattr(script_guard.subprocess, "run", fake)

    assert script_guard._probe_node_flags("node") is None
    assert len(fake.calls) == 4


@pytest.mark.parametrize(
    "failure",
    [FileNotFoundError("no node"), subprocess.TimeoutExpired("node", 20)],
)
def test_probing_a_node_that_cannot_run_gives_none_without_trying_more(
    failure: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _ScriptedNode([failure, 0])
    monkeypatch.setattr(script_guard.subprocess, "run", fake)

    assert script_guard._probe_node_flags("node") is None
    assert len(fake.calls) == 1


def test_node_guard_args_probe_each_node_once_and_allow_writes_only_to_the_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probed: list[str] = []

    def probe(node: str) -> tuple[str, ...] | None:
        probed.append(node)
        return ("--permission",) if node == "node-new" else None

    monkeypatch.setattr(script_guard, "_node_guard_flags", {})
    monkeypatch.setattr(script_guard, "_probe_node_flags", probe)

    assert node_guard_args("node-new", ["/ws", "/tmp"]) == [
        "--permission",
        "--allow-fs-write=/ws",
        "--allow-fs-write=/tmp",
    ]
    assert node_guard_args("node-new", ["/other"]) == ["--permission", "--allow-fs-write=/other"]
    assert node_guard_args("node-old", ["/ws"]) is None
    assert node_guard_args("node-old", ["/ws"]) is None
    assert probed == ["node-new", "node-old"]


def test_the_refusal_note_names_the_path_and_says_what_to_do() -> None:
    assert refusal_note("/data/out.txt") == (
        '\n[coscribe] The script was stopped from writing "/data/out.txt": it is outside the '
        "workspace and the folders added to this conversation. Write inside the workspace "
        "instead, or ask the user to add that folder (the chat shows an Add folder button)."
    )


def test_the_locked_file_note_tells_the_model_to_ask_the_user() -> None:
    note = locked_file_note("PermissionError: [Errno 13] Permission denied: '/data/report.xlsx'")

    assert note == (
        '\n[coscribe] "report.xlsx" could not be written: it is probably open in another '
        "program (Excel, Word, a PDF viewer) or read-only. Ask the user to close it and "
        "try again; don't save a copy under another name unless they say so."
    )
