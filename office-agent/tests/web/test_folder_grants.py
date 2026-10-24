# ruff: noqa: E402
"""Web tests: which folders keep scripts' grants at start, and the uninstaller's revoke."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.web import app as app_module
from coscribe.web import folder_grants
from coscribe.web.thread_files import ThreadFiles
from tests.environment_helpers import in_environment

from .helpers import _settings


def test_the_folders_in_use_are_every_environments_and_scheduled_runs(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    for folder in ("a", "b", "c"):
        (tmp_path / folder).mkdir()
    in_environment(settings.state_dir, "t1", folders=[str(tmp_path / "a"), str(tmp_path / "b")])
    ThreadFiles(settings).write_workspace_sidecar("scheduled-x-r1", [str(tmp_path / "c")])
    used = folder_grants.folders_in_use(settings)
    assert settings.workspace_root in used
    assert {tmp_path / "a", tmp_path / "b", tmp_path / "c"} <= set(used)


def test_the_uninstallers_flag_revokes_every_grant_and_starts_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    calls: list[object] = []
    monkeypatch.setattr(app_module, "_load_settings_or_none", lambda: settings)
    monkeypatch.setattr(
        app_module, "sweep_folder_grants", lambda state, folders: calls.append((state, folders))
    )
    monkeypatch.setattr(app_module, "_run_web_server", lambda *a: pytest.fail("server started"))
    monkeypatch.setattr(sys, "argv", ["coscribe-server", "--revoke-folder-grants"])
    app_module.main()
    assert calls == [(settings.state_dir, None)]
