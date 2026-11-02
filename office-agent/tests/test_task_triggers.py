"""What starts a task besides the clock, and what a run leaves for the next (decision 0034): every
few minutes, a new file in a folder, memory kept only by a finished run, and quiet runs."""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from coscribe.runtime_lg import fire_trigger_now, poll_due_scheduled_tasks
from coscribe.tools import FolderWatch, TaskMemory, compute_next_run_at
from coscribe.tools.bookkeeping import ScheduleRule
from coscribe.tools.bookkeeping.scheduled_tasks import (
    ScheduledTriggerStore,
    create_trigger,
    patch_trigger,
)
from coscribe.web.background_events import run_event

from .test_scheduled_tasks_resume import FakeToolCallingChatModel, _make_get_session, _settings

_FILE_TASK = {
    "inputs": [{"name": "doc", "label": "New file", "type": "file"}],
    "steps": [{"id": "log", "title": "Log it", "kind": "tool", "tool": "write_file",
               "args": {"path": "seen.txt", "content": "{{doc}}"}}],
}  # fmt: skip
_REMEMBERS = {
    "memory": [{"name": "last", "label": "Last run", "type": "text"}],
    "steps": [
        {"id": "log", "title": "Log it", "kind": "tool", "tool": "write_file",
         "args": {"path": "out.txt", "content": "last={{memory.last}}"}},
        {"id": "keep", "title": "Remember", "kind": "remember", "name": "last",
         "value": "{{run.date}}"},
    ],
}  # fmt: skip


def _old(path: Path) -> Path:
    """As if written a minute ago, so it counts as finished."""
    past = time.time() - 60
    os.utime(path, (past, past))
    return path


def test_every_few_minutes_runs_that_far_apart_within_bounds() -> None:
    rule = ScheduleRule(kind="every", at="", minutes=15)
    assert compute_next_run_at(rule, datetime(2026, 11, 2, 9, 7, 30)) == "2026-11-02T09:22:00"
    for minutes in (None, 4, 1441):
        with pytest.raises(ValueError, match="minutes must be 5-1440"):
            compute_next_run_at(ScheduleRule(kind="every", at="", minutes=minutes), datetime.now())


def test_a_folder_task_needs_a_real_folder_and_a_file_input(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path / "state")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    base: dict[str, Any] = {"name": "Inbox", "kind": "folder", "at": "", "prompt": ""}
    for watch, problem in [
        ({"folder": "relative/inbox", "input": "doc"}, "needs a folder"),
        ({"folder": str(tmp_path / "missing"), "input": "doc"}, "needs a folder"),
        ({"folder": str(inbox), "input": "other"}, "file inputs"),
    ]:
        with pytest.raises(ValueError, match=problem):
            create_trigger(store, **base, workflow=_FILE_TASK, watch=watch)

    trigger = create_trigger(
        store, **base, workflow=_FILE_TASK, watch={"folder": str(inbox), "pattern": "*.pdf",
                                                   "input": "doc"}
    )  # fmt: skip
    assert trigger.next_run_at is None
    assert trigger.schedule.pattern == "*.pdf"
    # Its runs may read the folder the files arrive in.
    assert trigger.permissions["folders"] == [str(inbox)]
    every = patch_trigger(store, trigger.trigger_id, {"kind": "every", "watch": {"minutes": 30}})
    assert every.schedule.minutes == 30 and every.next_run_at is not None


def test_the_folder_watch_counts_each_finished_file_once(tmp_path: Path) -> None:
    watch = FolderWatch(tmp_path / "state")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _old(_write(inbox / "already.pdf"))
    # The first look takes what is there as seen.
    assert watch.new_files("t", str(inbox), "*.pdf") == []

    _old(_write(inbox / "B.PDF"))
    _write(inbox / "fresh.pdf")  # still being written
    _old(_write(inbox / "part.pdf.crdownload"))
    _old(_write(inbox / "notes.txt"))
    assert watch.new_files("t", str(inbox), "*.pdf") == [str(inbox / "B.PDF")]
    assert watch.new_files("t", str(inbox), "*.pdf") == []

    # Replaced by a newer file of the same name, it counts again.
    _write(inbox / "B.PDF", "new")
    past = time.time() - 30
    os.utime(inbox / "B.PDF", (past, past))
    assert watch.new_files("t", str(inbox), "*.pdf") == [str(inbox / "B.PDF")]

    for i in range(7):
        _old(_write(inbox / f"batch{i}.pdf"))
    assert len(watch.new_files("t", str(inbox), "*.pdf")) == 5
    assert len(watch.new_files("t", str(inbox), "*.pdf")) == 2

    # Watching another folder starts from what is there.
    assert watch.new_files("t", str(tmp_path), "*") == []
    watch.forget("t")
    assert watch.new_files("t", str(inbox), "*.pdf") == []


def _write(path: Path, text: str = "x") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


async def test_a_new_file_in_the_folder_starts_a_run_with_its_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    settings.workspace_root.mkdir()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    store = ScheduledTriggerStore(settings.state_dir)
    watch = {"folder": str(inbox), "input": "doc"}
    trigger = create_trigger(
        store, name="Inbox", kind="folder", at="", prompt="", workflow=_FILE_TASK, watch=watch
    )
    ended: list[tuple[str, str]] = []

    async def on_ended(trigger_id: str, run: Any) -> None:
        ended.append((trigger_id, run.status))

    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "cp.sqlite")) as checkpointer:
        get_session = await _make_get_session(
            settings, checkpointer, FakeToolCallingChatModel(responses=[]), monkeypatch
        )
        first = await poll_due_scheduled_tasks(settings.state_dir, get_session, on_ended=on_ended)
        report = _old(_write(inbox / "report.pdf"))
        second = await poll_due_scheduled_tasks(settings.state_dir, get_session, on_ended=on_ended)
        third = await poll_due_scheduled_tasks(settings.state_dir, get_session, on_ended=on_ended)

    assert first == second == third == []
    assert ended == [(trigger.trigger_id, "completed")]
    saved = store.load(trigger.trigger_id)
    assert saved is not None and len(saved.runs) == 1
    assert saved.runs[0].inputs == {"doc": str(report)}
    assert (settings.workspace_root / "seen.txt").read_text(encoding="utf-8") == str(report)


async def test_only_a_finished_run_moves_the_memory_on_and_quiet_runs_fold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    settings.workspace_root.mkdir()
    store = ScheduledTriggerStore(settings.state_dir)
    keeps = create_trigger(store, name="Keeps", kind="manual", at="", prompt="",
                           workflow=_REMEMBERS)  # fmt: skip
    failing = {**_REMEMBERS, "steps": [*_REMEMBERS["steps"], {
        "id": "no", "title": "Never holds", "kind": "check",
        "conditions": [{"left": {"value": 1}, "op": "eq", "right": {"value": 2}}]}]}  # fmt: skip
    fails = create_trigger(store, name="Fails", kind="manual", at="", prompt="", workflow=failing)
    nothing_new = [{"left": {"ref": "memory.last"}, "op": "not_empty"}]
    quiet_steps = [{"id": "any", "title": "Anything new", "kind": "check", "otherwise": "end",
                    "conditions": nothing_new}]  # fmt: skip
    quiet = create_trigger(store, name="Quiet", kind="manual", at="", prompt="",
                           workflow={**_REMEMBERS, "steps": quiet_steps})  # fmt: skip

    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "cp.sqlite")) as checkpointer:
        get_session = await _make_get_session(
            settings, checkpointer, FakeToolCallingChatModel(responses=[]), monkeypatch
        )
        one = await fire_trigger_now(settings.state_dir, keeps.trigger_id, get_session)
        two = await fire_trigger_now(settings.state_dir, keeps.trigger_id, get_session)
        out = (settings.workspace_root / "out.txt").read_text(encoding="utf-8")
        failed = await fire_trigger_now(settings.state_dir, fails.trigger_id, get_session)
        quiet_runs = [
            await fire_trigger_now(settings.state_dir, quiet.trigger_id, get_session)
            for _ in range(3)
        ]

    memory = TaskMemory(settings.state_dir)
    assert one is not None and two is not None and one.status == two.status == "completed"
    # The second run read what the first kept.
    assert out == f"last={datetime.now().date().isoformat()}"
    assert memory.entries(keeps.trigger_id)["last"]["by"] == two.run_id
    assert failed is not None and failed.status == "failed"
    assert memory.values(fails.trigger_id) == {}

    assert all(r is not None and r.status == "completed" and r.quiet for r in quiet_runs)
    saved = store.load(quiet.trigger_id)
    assert saved is not None
    # A row of quiet runs keeps its latest, counting the ones it stands for.
    assert [(r.run_id, r.quiet) for r in saved.runs] == [
        (quiet_runs[1].run_id, 2),  # type: ignore[union-attr]
        (quiet_runs[2].run_id, 1),  # type: ignore[union-attr]
    ]
    assert run_event(saved, saved.runs[-1]) is None

    store.delete(keeps.trigger_id)
    assert memory.values(keeps.trigger_id) == {}
