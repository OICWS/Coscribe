"""Commands in Codex's Windows sandbox (decision 0022): when it counts as set up, and the
permission profile and command line a command gets. The sandbox itself runs only on Windows;
`test_windows_real.py` runs a real command in it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from coscribe.tools.exec import (
    Capabilities,
    CapabilityOff,
    command_sandbox,
    expect_sandbox,
    record_sandbox_setup,
    release_private_folders,
    sandbox_home,
    sandbox_status,
    sandboxed_command,
    start_command,
)
from coscribe.tools.exec import _private_folders as private_folders_module


@pytest.fixture
def on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command_sandbox, "supported", lambda: True)


def _codex(tmp_path: Path) -> Path:
    codex = tmp_path / "codex.exe"
    codex.write_text("")
    return codex


@pytest.mark.skipif(sys.platform == "win32", reason="the answer off Windows")
def test_off_windows_it_is_unsupported_and_commands_are_not_wrapped(tmp_path: Path) -> None:
    record_sandbox_setup(tmp_path, _codex(tmp_path))
    assert sandbox_status(tmp_path)["state"] == "unsupported"
    assert sandboxed_command(tmp_path, "dir", tmp_path, [tmp_path], [], False) is None


@pytest.mark.usefixtures("on_windows")
def test_it_is_ready_only_while_the_codex_that_set_it_up_is_still_there(tmp_path: Path) -> None:
    assert sandbox_status(tmp_path) == {"state": "off", "detail": ""}
    record_sandbox_setup(tmp_path, None, "The administrator said no.")
    assert sandbox_status(tmp_path) == {"state": "failed", "detail": "The administrator said no."}
    codex = _codex(tmp_path)
    record_sandbox_setup(tmp_path, codex)
    assert sandbox_status(tmp_path)["state"] == "ready"
    codex.unlink()
    assert sandbox_status(tmp_path)["state"] == "off"


@pytest.mark.usefixtures("on_windows")
def test_a_command_runs_through_cmd_in_a_profile_for_exactly_its_folders(tmp_path: Path) -> None:
    codex = _codex(tmp_path)
    record_sandbox_setup(tmp_path, codex)
    root, extra = tmp_path / "work", tmp_path / "reference"

    argv, env = sandboxed_command(tmp_path, 'echo "hi"', root, [root], [extra], False) or ([], {})

    home = sandbox_home(tmp_path)
    temp = Path(env["TEMP"])
    assert env == {"CODEX_HOME": str(home), "TEMP": str(temp), "TMP": str(temp)}
    profile = argv[3]
    script = Path(argv[-1])
    assert argv == [
        str(codex), "sandbox", "--permission-profile", profile, "-C", str(root), "--",
        "cmd.exe", "/d", "/c", str(script),
    ]  # fmt: skip
    # The line goes in a batch file: Codex would turn its quotes into \" for cmd.
    assert script.read_bytes() == b'@echo off\r\nchcp 65001 >nul\r\necho "hi"\r\n'
    assert script.parent == tmp_path / "command-sandbox" / "commands"
    config = (home / "config.toml").read_text(encoding="utf-8")
    assert config.startswith(
        'default_permissions = "coscribe-default"\n\n[windows]\nsandbox = "elevated"\n'
    )
    assert (
        f"[permissions.{profile}.filesystem]\n"
        '":root" = "read"\n'
        f'"{extra.as_posix()}" = "read"\n'
        f'"{script.parent.as_posix()}" = "read"\n'
        f'"{root.as_posix()}" = "write"\n'
        f'"{temp.as_posix()}" = "write"\n\n'
        f"[permissions.{profile}.network]\n"
        "enabled = false\n"
    ) in config


@pytest.mark.usefixtures("on_windows")
def test_the_same_folders_share_a_profile_and_old_profiles_are_dropped(tmp_path: Path) -> None:
    record_sandbox_setup(tmp_path, _codex(tmp_path))

    def profile(folder: str, network: bool = False) -> str:
        argv, _ = sandboxed_command(
            tmp_path, "dir", tmp_path, [tmp_path / folder], [], network
        ) or ([], {})
        return argv[3]

    first = profile("a")
    assert profile("a") == first
    assert profile("a", network=True) != first
    for n in range(command_sandbox._PROFILES_KEPT):
        profile(f"b{n}")
    config = (sandbox_home(tmp_path) / "config.toml").read_text(encoding="utf-8")
    assert f"[permissions.{first}.filesystem]" not in config
    assert config.count(".filesystem]") == command_sandbox._PROFILES_KEPT + 1


async def test_a_command_approved_for_the_sandbox_does_not_run_once_it_is_gone(
    tmp_path: Path,
) -> None:
    Capabilities(tmp_path).set("commands", True)
    Capabilities(tmp_path).set("commands_without_sandbox", True)
    folders: dict[str, list[Path]] = {"writable": [tmp_path], "readable": []}
    expect_sandbox("t1")

    with pytest.raises(CapabilityOff, match="removed after this command was approved"):
        await start_command(tmp_path, "t1", tmp_path, folders, "exit 0", {})
    # The next one was not approved on that ground, so it runs as before.
    proc = await start_command(tmp_path, "t1", tmp_path, folders, "exit 0", {})
    assert await proc.wait() == 0


@pytest.fixture
def icacls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Records icacls calls; a call on a path containing "fails" fails."""
    calls: list[tuple[str, ...]] = []

    def fake(*args: str) -> str | None:
        calls.append(args)
        return None if "fails" in args[0] else ""

    monkeypatch.setattr(private_folders_module, "_icacls", fake)
    return calls


_GRANT = "CodexSandboxUsers:(OI)(CI)(RX)"


@pytest.mark.usefixtures("on_windows")
def test_private_folders_are_denied_and_what_the_command_needs_in_them_is_let_back(
    tmp_path: Path, icacls: list[tuple[str, ...]]
) -> None:
    record_sandbox_setup(tmp_path, _codex(tmp_path))
    documents, appdata = tmp_path / "Documents", tmp_path / "AppData"
    root, reference, program = documents / "work", documents / "reference", appdata / "Python"
    for folder in (root, reference, program):
        folder.mkdir(parents=True)

    def run() -> tuple[list[str], dict[str, str]]:
        sandboxed = sandboxed_command(
            tmp_path, "dir", root, [root], [reference], False,
            hidden=[documents, appdata], programs=[program, tmp_path / "elsewhere"],
        )  # fmt: skip
        assert sandboxed is not None
        return sandboxed

    argv, env = run()
    run()

    config = (sandbox_home(tmp_path) / "config.toml").read_text(encoding="utf-8")
    section = config[config.index(f"[permissions.{argv[3]}.filesystem]") :]
    assert section.startswith(
        f"[permissions.{argv[3]}.filesystem]\n"
        '":root" = "read"\n'
        f'"{documents.as_posix()}" = "deny"\n'
        f'"{appdata.as_posix()}" = "deny"\n'
    )
    # Its own Temp, which it may write: the person's is in AppData.
    temp = Path(env["TEMP"])
    assert env["TMP"] == env["TEMP"] and temp.is_dir()
    assert f'"{temp.as_posix()}" = "write"' in section
    # Codex grants the folders it writes; the ones it only reads inside a denied folder are
    # coscribe's to grant, once each. The batch files are in the state dir, outside both.
    assert icacls == [(str(reference), "/grant", _GRANT), (str(program), "/grant", _GRANT)]


@pytest.mark.usefixtures("on_windows")
def test_a_private_folder_given_to_the_environment_is_not_denied_and_loses_an_old_deny(
    tmp_path: Path, icacls: list[tuple[str, ...]]
) -> None:
    record_sandbox_setup(tmp_path, _codex(tmp_path))
    documents = tmp_path / "Documents"
    (documents / "work").mkdir(parents=True)
    sandboxed_command(
        tmp_path, "dir", documents / "work", [documents / "work"], [], False, hidden=[documents]
    )
    icacls.clear()

    sandboxed_command(tmp_path, "dir", documents, [documents], [], False, hidden=[documents])

    config = (sandbox_home(tmp_path) / "config.toml").read_text(encoding="utf-8")
    assert config.count('"deny"') == 1  # the first profile's, kept with the profiles
    # Codex's deny entry would beat its grant on the folder it now writes.
    assert icacls == [(str(documents), "/remove:d", "CodexSandboxUsers")]


def test_a_failed_grant_stops_the_command_and_stays_in_the_ledger(
    tmp_path: Path, icacls: list[tuple[str, ...]], monkeypatch: pytest.MonkeyPatch
) -> None:
    documents = tmp_path / "Documents"
    reference = documents / "fails"
    reference.mkdir(parents=True)

    with pytest.raises(private_folders_module.GrantFailed, match="fails"):
        private_folders_module.prepare_folders(tmp_path, [documents], [], [reference])

    monkeypatch.setattr(private_folders_module, "private_folders", lambda: [])
    icacls.clear()
    left = release_private_folders(tmp_path)
    assert (str(reference), "/remove:g", "CodexSandboxUsers") in icacls
    assert left == [str(reference)]


def test_showing_them_again_takes_away_the_grants_and_denies_it_recorded(
    tmp_path: Path, icacls: list[tuple[str, ...]], monkeypatch: pytest.MonkeyPatch
) -> None:
    documents, reference = tmp_path / "Documents", tmp_path / "Documents" / "reference"
    reference.mkdir(parents=True)
    private_folders_module.prepare_folders(tmp_path, [documents], [], [reference])
    # Documents moved since: the recorded one is cleared all the same.
    monkeypatch.setattr(private_folders_module, "private_folders", lambda: [])
    icacls.clear()

    assert release_private_folders(tmp_path) == []
    assert release_private_folders(tmp_path) == []

    assert icacls == [
        (str(reference), "/remove:g", "CodexSandboxUsers"),
        (str(documents), "/remove:d", "CodexSandboxUsers"),
        (str(documents),),
    ]


def test_a_deny_that_icacls_still_lists_is_reported_and_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    documents = tmp_path / "Documents"
    documents.mkdir()
    listing = f"{documents} HOST\\CodexSandboxUsers:(OI)(CI)(IO)(DENY)(R,GR)\n"
    monkeypatch.setattr(
        private_folders_module, "_icacls", lambda *a: listing if len(a) == 1 else ""
    )
    monkeypatch.setattr(private_folders_module, "private_folders", lambda: [documents])

    assert release_private_folders(tmp_path) == [str(documents)]
    assert release_private_folders(tmp_path) == [str(documents)]
