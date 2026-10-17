# ruff: noqa: E402
"""Web tests: the thread-files service without the app."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")


from coscribe.web.thread_files import ThreadFiles

from .helpers import (
    _settings,
)


def test_thread_files_round_trip_a_workspace_sidecar_without_the_app(tmp_path: Path) -> None:
    files = ThreadFiles(_settings(tmp_path))

    files.write_workspace_sidecar("t1", [str(tmp_path / "a"), str(tmp_path / "b")])

    assert files.read_workspace_sidecar("t1") == [str(tmp_path / "a"), str(tmp_path / "b")]
    assert files.read_workspace_sidecar("other") == []
    files.write_workspace_sidecar("t1", [])
    assert not files.workspace_sidecar_path("t1").exists()


def test_thread_files_read_a_sidecar_from_before_multi_folder_threads(tmp_path: Path) -> None:
    files = ThreadFiles(_settings(tmp_path))
    files.workspace_sidecar_path("t1").parent.mkdir(parents=True)
    files.workspace_sidecar_path("t1").write_text(str(tmp_path / "old"), encoding="utf-8")

    assert files.read_workspace_sidecar("t1") == [str(tmp_path / "old")]


def test_thread_files_take_the_workspace_param_only_the_first_time(tmp_path: Path) -> None:
    files = ThreadFiles(_settings(tmp_path))

    assert files.resolve_folders("t1", None) == []
    assert files.resolve_folders("t1", str(tmp_path / "a")) == [tmp_path / "a"]
    assert files.resolve_folders("t1", str(tmp_path / "b")) == [tmp_path / "a"]


def test_thread_files_open_a_scheduled_run_in_its_tasks_folders(tmp_path: Path) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import (
        ScheduledTriggerStore,
        create_trigger,
        run_thread_id,
    )

    settings = _settings(tmp_path)
    folder = tmp_path / "task-folder"
    folder.mkdir()
    task = create_trigger(
        ScheduledTriggerStore(settings.state_dir),
        name="t",
        kind="manual",
        at="",
        prompt="p",
        workspace=str(folder),
    )
    files = ThreadFiles(settings)
    thread_id = run_thread_id(task.trigger_id, "r1")

    assert files.run_workspace(thread_id) == str(folder)
    assert files.resolve_folders(thread_id, None) == [folder]
    assert files.read_workspace_sidecar(thread_id) == [str(folder)]


def test_thread_files_delete_every_file_of_a_thread_and_no_other(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    files = ThreadFiles(settings)
    files.write_workspace_sidecar("t1", [str(tmp_path)])
    files.write_workspace_sidecar("t2", [str(tmp_path)])
    files.title_sidecar_path("t1").write_text("Renamed", encoding="utf-8")
    (settings.state_dir / "t1.tasks.json").write_text("[]", encoding="utf-8")

    files.delete("t1")

    assert not files.workspace_sidecar_path("t1").exists()
    assert not files.title_sidecar_path("t1").exists()
    assert not (settings.state_dir / "t1.tasks.json").exists()
    assert files.workspace_sidecar_path("t2").is_file()
