"""Checks that need the real Windows parts, not a fake of them: the Credential Manager, cmd and
PowerShell, taskkill, the Store python stub, resvg's font lookup, Codex's command sandbox.

They run in `.github/workflows/windows-more-checks.yml` only (COSCRIBE_WINDOWS_REAL=1), so a
failure here does not reset the nightly run of green nights in windows.yml (decision 0009)."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from coscribe.code_runtime.install import ensure_codex
from coscribe.code_runtime.thread import reads_only
from coscribe.runtime.hooks import run_hook
from coscribe.runtime.secrets import SERVICE_NAME, resolve_secret, store_secret
from coscribe.tools.bookkeeping.background_tasks import build_background_task_tools
from coscribe.tools.exec import (
    Capabilities,
    bundled_sandbox,
    command_sandbox,
    record_sandbox_setup,
    release_private_folders,
    run_as_administrator,
    sandbox_codex,
    sandbox_home,
    sandbox_setup_argv,
    sandbox_uninstall_argv,
    script_env,
    start_command,
    warm_up_sandbox,
)

real = pytest.mark.skipif(
    sys.platform != "win32" or os.environ.get("COSCRIBE_WINDOWS_REAL") != "1",
    reason="needs a real Windows machine; set by windows-more-checks.yml",
)

_POWERSHELL = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"


def _cmdkey_list() -> str:
    return subprocess.run(["cmdkey", "/list"], capture_output=True, text=True, check=False).stdout


@real
def test_a_secret_goes_into_the_credential_manager_and_survives_a_new_process() -> None:
    import keyring

    ref = f"coscribe-check-{uuid.uuid4().hex}"
    try:
        stored = store_secret(ref, "s3cret-value")
        assert stored == {"keyring_ref": ref}, "store_secret fell back to plaintext"
        assert "WinVault" in type(keyring.get_keyring()).__name__
        assert ref in _cmdkey_list(), "the entry is not in Windows Credential Manager"
        assert resolve_secret(stored) == "s3cret-value"
        # The app is restarted: a separate process must read the same value.
        code = (
            "from coscribe.runtime.secrets import resolve_secret;"
            f"print(resolve_secret({{'keyring_ref': '{ref}'}}))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == "s3cret-value"
    finally:
        _forget(ref)


def _forget(ref: str) -> None:
    import keyring

    if keyring.get_password(SERVICE_NAME, ref) is not None:
        keyring.delete_password(SERVICE_NAME, ref)


@real
def test_an_entry_removed_behind_the_apps_back_is_reported_not_a_crash() -> None:
    ref = f"coscribe-check-{uuid.uuid4().hex}"
    stored = store_secret(ref, "gone-soon")
    assert isinstance(stored, dict)
    subprocess.run(["cmdkey", f"/delete:{SERVICE_NAME}:{ref}"], capture_output=True, check=False)
    _forget(ref)

    with pytest.raises(RuntimeError, match="re-enter it via Settings"):
        resolve_secret(stored)


@real
def test_a_hook_runs_under_cmd_and_under_powershell() -> None:
    payload = {"tool": "Bash"}

    assert run_hook("exit 0", payload).allowed
    denied = run_hook("echo blocked by cmd 1>&2 & exit 3", payload)
    assert not denied.allowed and denied.reason == "blocked by cmd"

    # The payload reaches a PowerShell hook on stdin.
    read = (
        "$p = [Console]::In.ReadToEnd(); "
        "if ($p -notmatch 'Bash') { [Console]::Error.Write('no payload'); exit 4 }"
    )
    assert run_hook(f'powershell -NoProfile -Command "{read}"', payload).allowed
    refused = run_hook(
        "powershell -NoProfile -Command \"[Console]::Error.Write('no'); exit 5\"", payload
    )
    assert not refused.allowed and refused.reason == "no"


@real
def test_format_hex_returns_the_bytes_unscrambled_and_counts_as_a_read(tmp_path: Path) -> None:
    (tmp_path / "data.bin").write_bytes(bytes(range(16)))
    # No -Count: Windows PowerShell 5.1, the one every Windows has, lacks it (added in 6.1).
    script = "Format-Hex -LiteralPath data.bin"
    command = (
        f"{_POWERSHELL} -NoProfile -Command "
        f'"[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; {script}"'
    )

    result = subprocess.run(
        command, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=True
    )

    assert "00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F" in result.stdout
    assert reads_only(command, str(tmp_path), tmp_path)


def _tools(tmp_path: Path, state: Path | None = None) -> dict[str, Any]:
    """The background tools; with `state`, one where the command sandbox is set up."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state = state or tmp_path / "state"
    Capabilities(state).set("commands", True)
    Capabilities(state).set("commands_without_sandbox", True)
    return {t.__name__: t for t in build_background_task_tools("t1", workspace, state)}


@real
def test_run_as_starts_the_command_elevated_with_its_environment_and_keeps_its_output(
    tmp_path: Path,
) -> None:
    """The path a standard user's setup takes (the runner is an administrator, so setup itself
    skips it): the exit code, the environment and the output all come back."""
    log = tmp_path / "it's here" / "administrator.log"
    log.parent.mkdir()
    argv = ["cmd.exe", "/d", "/c", "echo home=%CODEX_HOME%& exit /b 3"]
    wrapped = command_sandbox._through_run_as(argv, {"CODEX_HOME": str(tmp_path)}, log)
    done = subprocess.run(wrapped, capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 3, done.stdout + done.stderr
    assert log.read_text(encoding="utf-8-sig").strip() == f"home={tmp_path}"


@pytest.fixture(scope="module")
def sandboxed_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A state dir whose command sandbox is set up as Settings › Capabilities does it; the
    runner is an administrator, so Windows asks nobody."""
    state = tmp_path_factory.mktemp("sandbox-state")
    # The built-in sandbox where the job built it (#607), else the one that comes with Codex.
    codex = bundled_sandbox() or ensure_codex(state)
    assert run_as_administrator(sandbox_setup_argv(codex, state), state, 600) == ""
    record_sandbox_setup(state, codex)
    warm_up_sandbox(state)
    return state


async def _finished(tools: dict[str, Any], task_id: str) -> dict[str, Any]:
    for _ in range(600):
        result: dict[str, Any] = tools["check_background_task"](task_id)
        if result["status"] != "running":
            return result
        await asyncio.sleep(0.1)
    raise AssertionError("the command did not finish")


def _alive(pid: int) -> bool:
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False
    ).stdout
    return str(pid) in out


@real
async def test_the_first_sandboxed_command_after_setup_runs(
    tmp_path: Path, sandboxed_state: Path
) -> None:
    tools = _tools(tmp_path, sandboxed_state)
    started = await tools["run_background_command"](command="whoami", description="first")
    result = await _finished(tools, started["task_id"])
    assert "codexsandbox" in result.get("output", "").lower(), result.get("output")


@real
@pytest.mark.parametrize("sandboxed", [False, True])
async def test_stopping_a_background_command_ends_its_whole_process_tree(
    sandboxed: bool, tmp_path: Path, request: pytest.FixtureRequest
) -> None:
    state = request.getfixturevalue("sandboxed_state") if sandboxed else None
    tools = _tools(tmp_path, state)
    # In the workspace, the one folder a sandboxed command may write.
    pid_file = tmp_path / "workspace" / "child.pid"
    child = "import time; time.sleep(120)"
    parent = (
        "import subprocess, sys, time; "
        f"p = subprocess.Popen([sys.executable, '-c', '{child}']); "
        f"open(r'{pid_file}', 'w').write(str(p.pid)); time.sleep(120)"
    )
    command = f'whoami & "{sys.executable}" -c "{parent}"'

    started = await tools["run_background_command"](command=command, description="tree")
    # A sandboxed command's first run in a folder waits for Codex to grant it to the sandbox user.
    for _ in range(600):
        if pid_file.exists() and pid_file.read_text().strip():
            break
        await asyncio.sleep(0.1)
    task = tools["check_background_task"](started["task_id"])
    assert pid_file.exists(), task.get("output")
    grandchild = int(pid_file.read_text())
    assert _alive(grandchild)
    assert tools["check_background_task"](started["task_id"])["status"] == "running"

    await tools["kill_background_task"](started["task_id"])
    for _ in range(100):
        if tools["check_background_task"](started["task_id"])["status"] != "running":
            break
        await asyncio.sleep(0.1)
    for _ in range(100):
        if not _alive(grandchild):
            break
        await asyncio.sleep(0.1)

    assert tools["check_background_task"](started["task_id"])["status"] == "killed"
    assert not _alive(grandchild), "taskkill /T left the child running"


@real
def test_a_python_that_is_only_the_store_stub_is_replaced_by_a_working_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The Store alias exits at once with 9009 and a message; a .cmd in front of the real
    # Python on PATH behaves the same for shutil.which and for running it.
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (stub_dir / "python.cmd").write_text("@echo Python was not found 1>&2\n@exit /b 9009\n")
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ['PATH']}")

    chosen = script_env.resolve_python_command("python", None)

    assert chosen != "python"
    assert script_env.working_interpreters([chosen]) == [chosen]


@real
def test_chinese_text_is_drawn_with_the_installed_yahei(tmp_path: Path) -> None:
    import resvg_py

    assert Path("C:/Windows/Fonts/msyh.ttc").is_file(), "Microsoft YaHei is not installed"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">'
        '<text x="10" y="55" font-size="48" font-family="Microsoft YaHei">\u4e2d\u6587</text></svg>'
    )
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=200, background="#ffffff"))

    import io

    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert("L")
    ink = sum(image.histogram()[:128])
    assert ink > 400, f"the text drew {ink} dark pixels: no font was found"


def test_a_script_without_node_installed_says_what_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.exec.node_env import ensure_node_env

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    with pytest.raises(RuntimeError, match=r"node.*not found on PATH.*install Node\.js"):
        ensure_node_env(tmp_path / "state")


@real
async def test_a_sandboxed_command_writes_only_its_workspace_and_cannot_read_private_folders(
    tmp_path: Path, sandboxed_state: Path
) -> None:
    # A workspace in Documents, as a person's would be, with a file beside it, one on the
    # Desktop and one in AppData. Codex's setup lets its users read all of them; coscribe hides
    # them while Settings › Capabilities says so (the default), and shows them again when not.
    profile = Path(os.environ["USERPROFILE"])
    base = profile / "Documents" / f"coscribe-{uuid.uuid4().hex}"
    base.mkdir(parents=True)
    tools = _tools(base, sandboxed_state)
    outside = base / "outside"
    outside.mkdir()
    beside = outside / "secret.txt"
    beside.write_text("BESIDE-SECRET")
    tag = uuid.uuid4().hex
    desktop = profile / "Desktop" / f"coscribe-secret-{tag}.txt"
    # Beside the way down to the workspace: Documents itself is no longer denied whole.
    documents = profile / "Documents" / f"coscribe-secret-{tag}.txt"
    documents.write_text("DOCUMENTS-SECRET")
    roaming = Path(os.environ["APPDATA"]) / f"coscribe-secret-{tag}.txt"
    # Like .git-credentials or .netrc: a file at the profile's top, which Codex never opens.
    top = profile / f".coscribe-secret-{tag}"
    top.write_text("TOP-SECRET")
    desktop.parent.mkdir(exist_ok=True)
    desktop.write_text("DESKTOP-SECRET")
    roaming.write_text("ROAMING-SECRET")
    made = outside / "made.txt"
    connect = (
        "import tempfile; tempfile.TemporaryFile().close(); print('PY-RAN'); import socket; "
        "socket.create_connection(('1.1.1.1', 443), 5); print('NET-OPEN')"
    )
    reads = (
        f'type "{beside}" & type "{desktop}" & type "{roaming}" & type "{top}" & type "{documents}"'
    )
    # PowerShell can't start in a folder whose parents its user can't list (it falls back to C:\).
    where = "pwsh -NoProfile -Command \"'PWSH:' + (Get-Location).Path\" & "
    where += "powershell -NoProfile -Command \"'WINPS:' + (Get-Location).Path\""
    command = (
        f"whoami & echo inside> made.txt & {where} & {reads} & "
        f'echo outside> "{made}" & "{sys.executable}" -c "{connect}"'
    )

    async def run(line: str) -> str:
        started = await tools["run_background_command"](command=line, description="probe")
        return str((await _finished(tools, started["task_id"])).get("output", ""))

    try:
        output = await run(command)
        acls = _icacls(beside.parent, desktop.parent, roaming.parent)
        assert (base / "workspace" / "made.txt").read_text().strip() == "inside", output
        assert not made.exists(), output
        workspace = str(base / "workspace").lower()
        assert f"pwsh:{workspace}" in output.lower(), output
        assert f"winps:{workspace}" in output.lower(), output
        for secret in (
            "BESIDE-SECRET", "DESKTOP-SECRET", "ROAMING-SECRET", "TOP-SECRET", "DOCUMENTS-SECRET"
        ):  # fmt: skip
            assert secret not in output, output + acls
        assert "codexsandbox" in output.lower(), output
        # Its Temp is its own, so Python's tempfile works; the network is not Full, so offline.
        assert "PY-RAN" in output and "NET-OPEN" not in output, output

        Capabilities(sandboxed_state).set("commands_hide_private_folders", False)
        release_private_folders(sandboxed_state)
        shown = await run(reads)
        for secret in ("BESIDE-SECRET", "DESKTOP-SECRET", "ROAMING-SECRET"):
            assert secret in shown, shown + _icacls(beside.parent, desktop.parent, roaming.parent)
    finally:
        Capabilities(sandboxed_state).set("commands_hide_private_folders", True)
        desktop.unlink(missing_ok=True)
        documents.unlink(missing_ok=True)
        roaming.unlink(missing_ok=True)
        top.unlink(missing_ok=True)
        shutil.rmtree(base, ignore_errors=True)


def _icacls(*paths: Path) -> str:
    return "\n".join(
        subprocess.run(["icacls", str(p)], capture_output=True, text=True, check=False).stdout
        for p in paths
    )


@real
async def test_a_read_only_folder_and_a_program_inside_private_folders_stay_usable(
    tmp_path: Path, sandboxed_state: Path
) -> None:
    # The grants coscribe adds: a read-only folder in Documents and a program on PATH in
    # LOCALAPPDATA, both inside folders the profile denies.
    tag = uuid.uuid4().hex
    base = Path(os.environ["USERPROFILE"]) / "Documents" / f"coscribe-{tag}"
    # In a folder beside the workspace's, which is denied as the rest of Documents is.
    shelf = base.with_name(f"coscribe-shelf-{tag}")
    workspace, reference = base / "workspace", shelf / "reference"
    workspace.mkdir(parents=True)
    reference.mkdir(parents=True)
    (reference / "r.txt").write_text("REF-READ")
    program = Path(os.environ["LOCALAPPDATA"]) / f"coscribe-program-{tag}"
    program.mkdir()
    (program / "coscribe-hello.cmd").write_text("@echo HELLO-PROGRAM\r\n")
    Capabilities(sandboxed_state).set("commands", True)
    env = {**os.environ, "PATH": f"{program};{os.environ['PATH']}"}
    folders = {"writable": [workspace], "readable": [reference]}

    try:
        proc = await start_command(
            sandboxed_state, "t-grants", workspace, folders,
            f'whoami & type "{reference / "r.txt"}" & coscribe-hello', env,
        )  # fmt: skip
        out, _ = await proc.communicate()
        output = out.decode("utf-8", errors="replace")
        assert "codexsandbox" in output.lower(), output
        assert "REF-READ" in output, output + _icacls(shelf, reference)
        assert "HELLO-PROGRAM" in output, output + _icacls(program)
        # The deny entries name the sandbox's group, which the person is not in.
        groups = subprocess.run(
            ["whoami", "/groups"], capture_output=True, text=True, check=False
        ).stdout
        assert "codexsandboxusers" not in groups.lower(), groups
        assert (reference / "r.txt").read_text() == "REF-READ"
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(shelf, ignore_errors=True)
        shutil.rmtree(program, ignore_errors=True)


@real
async def test_the_unelevated_sandbox_needs_no_administrator_and_holds_writes(
    tmp_path: Path,
) -> None:
    """The mode a person without an administrator picks: no `codex sandbox setup`, and a
    command still writes only its workspace. Its network is held only by its environment, so
    this prints what a connection did rather than asserting it."""
    state = tmp_path / "state"
    # The built-in sandbox where the job built it (#607), else the one that comes with Codex.
    codex = bundled_sandbox() or ensure_codex(state)
    record_sandbox_setup(state, codex, mode="unelevated")
    assert warm_up_sandbox(state) == ""
    tools = _tools(tmp_path, state)
    outside = tmp_path / "outside"
    outside.mkdir()
    made = outside / "made.txt"
    connect = (
        "import tempfile; tempfile.TemporaryFile().close(); print('PY-RAN'); import socket; "
        "socket.create_connection(('1.1.1.1', 443), 5); print('NET-OPEN')"
    )
    command = (
        f'whoami & echo inside> made.txt & echo outside> "{made}" & '
        f'"{sys.executable}" -c "{connect}"'
    )
    started = await tools["run_background_command"](command=command, description="probe")
    output = str((await _finished(tools, started["task_id"])).get("output", ""))
    print("unelevated sandbox output:", output)
    assert (tmp_path / "workspace" / "made.txt").read_text().strip() == "inside", output
    assert not made.exists(), output
    assert "PY-RAN" in output, output


# Last in the file: it removes the sandbox the tests above share.
@real
async def test_a_command_fails_closed_when_the_sandbox_was_removed_behind_the_apps_back(
    tmp_path: Path, sandboxed_state: Path
) -> None:
    tools = _tools(tmp_path, sandboxed_state)
    codex = sandbox_codex(sandboxed_state)
    assert codex is not None
    home = {**os.environ, "CODEX_HOME": str(sandbox_home(sandboxed_state))}
    removed = subprocess.run(
        sandbox_uninstall_argv(codex), env=home, capture_output=True, text=True, check=False
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr

    started = await tools["run_background_command"](
        command="whoami & echo inside> made.txt", description="after removal"
    )
    result = await _finished(tools, started["task_id"])

    # Codex either refuses or sets the sandbox up again (the runner is an administrator); never
    # does the command run as the person.
    output = result.get("output", "")
    ran_as = output.splitlines()[0].lower() if output.strip() else ""
    assert os.environ["USERNAME"].lower() not in ran_as, output
    if result["status"] == "succeeded":
        assert "codexsandbox" in ran_as, output
    else:
        assert not (tmp_path / "workspace" / "made.txt").exists(), output
