# ruff: noqa: E402
"""Web tests: a run's report offers its heals as a fix the person saves into the task, and a
heal no fix can keep as a revision drafted in a conversation."""

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore
from coscribe.web.routes import scheduled as scheduled_routes

from .helpers import FakeToolCallingChatModel, _client_lg, _create_workflow_task


def test_a_runs_named_fix_is_offered_once_and_saved_by_the_person_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _create_workflow_task(client)
        trigger_id = task["trigger_id"]
        store = ScheduledTriggerStore(tmp_path / "state")
        _, run, _ = store.start_run(trigger_id, "manual")
        healed = {"error": "No such folder", "did": "Saved it as summary.md instead.",
                  "args": {"path": "summary.md"}, "was": {"path": "out.md"}}  # fmt: skip
        record = {"step_id": "write", "status": "done", "iteration": [],
                  "agent": {"healed": healed}}  # fmt: skip
        store.record_step(trigger_id, run.run_id, record)
        store.finish_run(trigger_id, run.run_id, "completed")
        report_url = f"/api/scheduled-tasks/{trigger_id}/runs/{run.run_id}/report"

        fixes = client.get(report_url).json()["fixes"]
        saved = client.patch(
            f"/api/scheduled-tasks/{trigger_id}", json={"workflow": fixes["workflow"]}
        )
        after = client.get(report_url).json()["fixes"]

    assert fixes["fixes"] == [{"step_id": "write", "title": "Save", "name": "path",
                               "was": "out.md", "now": "summary.md"}]  # fmt: skip
    assert saved.status_code == 200, saved.text
    write = next(s for s in saved.json()["workflow"]["steps"] if s["id"] == "write")
    assert write["args"]["path"] == "summary.md"
    # Saved: the task no longer holds what the heal replaced, so nothing is offered again.
    assert after == {"fixes": [], "workflow": None, "left": []}


def test_a_run_with_heals_no_fix_keeps_is_offered_a_revision_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[str] = []

    async def start(state_dir: object, trigger_id: str, run_id: str, *args: object, **_: object):
        started.append(run_id)

    monkeypatch.setattr(scheduled_routes, "start_investigation", start)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        trigger_id = _create_workflow_task(client)["trigger_id"]
        store = ScheduledTriggerStore(tmp_path / "state")
        runs = []
        for healed in (
            {"error": "x", "did": "Wrote it in two parts.", "args": {}, "was": {}},
            None,
        ):
            _, run, _ = store.start_run(trigger_id, "manual")
            agent = {"healed": healed} if healed else {}
            record = {"step_id": "write", "status": "done", "iteration": [], "agent": agent}
            store.record_step(trigger_id, run.run_id, record)
            store.finish_run(trigger_id, run.run_id, "completed")
            runs.append(run.run_id)
        url = "/api/scheduled-tasks/{}/runs/{}/investigate"
        healed_run = client.post(url.format(trigger_id, runs[0]), json={})
        clean_run = client.post(url.format(trigger_id, runs[1]), json={})

    assert healed_run.status_code == 200, healed_run.text
    assert started == [runs[0]]
    # A run that finished as saved has nothing to revise.
    assert clean_run.status_code == 409


async def test_a_task_set_to_look_into_runs_drafts_the_revision_unasked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import create_trigger
    from coscribe.web import scheduler as scheduler_module
    from coscribe.web.background_events import BackgroundEventBus

    from .helpers import _NOTES_WORKFLOW, _settings

    started: list[tuple[str, bool]] = []

    async def start(*args: object, attended: bool, **_: object) -> None:
        started.append((str(args[2]), attended))

    monkeypatch.setattr(scheduler_module, "start_investigation", start)
    settings = _settings(tmp_path)
    store = ScheduledTriggerStore(settings.state_dir)
    task = create_trigger(
        store, name="Count", kind="manual", at="", prompt="", workflow=_NOTES_WORKFLOW
    )
    task.auto_investigate = True
    store.save(task)
    _, run, _ = store.start_run(task.trigger_id, "manual")
    healed = {"error": "x", "did": "Wrote it in two parts.", "args": {}, "was": {}}
    store.record_step(task.trigger_id, run.run_id, {"step_id": "write", "status": "done",
                                                     "agent": {"healed": healed}})  # fmt: skip
    finished = store.finish_run(task.trigger_id, run.run_id, "completed")
    assert finished is not None

    async def unused(*_: object, **__: object) -> object:
        raise AssertionError("not called")

    scheduler = scheduler_module.Scheduler(
        settings, {}, BackgroundEventBus(), unused, unused, lambda: None, unused, unused
    )
    await scheduler.announce_run(task.trigger_id, finished.find_run(run.run_id))
    await asyncio.sleep(0)  # the conversation starts in the background
    await scheduler.stop()

    # No one is watching: the conversation drafts, and the person reviews and saves.
    assert started == [(run.run_id, False)]
