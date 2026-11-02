# ruff: noqa: E402
"""Decision 0033 through the server: a task's run that waits for an answer or for a time, the
answer that continues it, the poll that wakes it, and the daily reminder."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from coscribe.runtime_lg import fire_trigger_now, poll_due_scheduled_tasks
from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore
from coscribe.web import scheduler as scheduler_module
from coscribe.web.background_events import BackgroundEventBus
from coscribe.workflows import pause_steps

from ..test_scheduled_tasks_resume import FakeToolCallingChatModel as ResumeModel
from ..test_scheduled_tasks_resume import _make_get_session, _trigger
from ..test_scheduled_tasks_resume import _settings as _resume_settings
from .helpers import FakeToolCallingChatModel, _client_lg, _settings, _wait_for_run_status

_ASK = {"id": "ask", "kind": "ask", "title": "Ask for the amount", "message": "How much?",
        "save_as": "got", "fields": [{"name": "amount", "label": "Amount", "type": "number"}]}
_WAIT = {"id": "later", "kind": "wait", "title": "Wait a while", "until": "duration",
         "minutes": 30}
_WRITE = {"id": "write", "kind": "tool", "title": "Save", "tool": "write_file",
          "args": {"path": "out.txt", "content": "done"}}  # fmt: skip


def _task(client: Any, steps: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    task = client.post(
        "/api/scheduled-tasks",
        json={"name": "Pauses", "kind": "manual", "at": "", "workflow": {"steps": steps}},
    ).json()
    run = client.post(f"/api/scheduled-tasks/{task['trigger_id']}/run", json={}).json()["run"]
    return task["trigger_id"], _wait_for_run_status(client, task["trigger_id"], run["run_id"])


def test_an_ask_steps_answer_is_checked_then_continues_the_run_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        trigger_id, parked = _task(client, [_ASK, _WRITE])
        url = f"/api/scheduled-tasks/{trigger_id}/runs/{parked['run_id']}/answer"
        blank = client.post(url, json={"approved": True, "values": {"amount": ""}})
        wrong = client.post(url, json={"approved": True, "values": {"amount": "lots"}})
        right = client.post(url, json={"approved": True, "values": {"amount": "4"}})
        finished = _wait_for_run_status(client, trigger_id, parked["run_id"])

    assert parked["status"] == "needs_approval"
    assert parked["steps"][-1]["pause"]["fields"][0]["name"] == "amount"
    assert blank.status_code == 422 and blank.json()["error"] == "Amount needs a value"
    assert wrong.status_code == 422
    assert right.status_code == 200
    assert finished["status"] == "completed"
    assert finished["steps"][0]["output"] == {"amount": 4}
    assert (tmp_path / "workspace" / "out.txt").read_text(encoding="utf-8") == "done"


def test_a_waiting_run_goes_on_when_told_or_is_stopped_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        trigger_id, waiting = _task(client, [_WAIT, _WRITE])
        base = f"/api/scheduled-tasks/{trigger_id}/runs"
        go_on = client.post(f"{base}/{waiting['run_id']}/answer", json={"approved": True})
        finished = _wait_for_run_status(client, trigger_id, waiting["run_id"])
        other_id, other = _task(client, [_WAIT, _WRITE])
        stopped = client.post(f"/api/scheduled-tasks/{other_id}/runs/{other['run_id']}/stop")
        after = _wait_for_run_status(client, other_id, other["run_id"])

    assert waiting["status"] == "waiting"
    assert waiting["steps"][-1]["pause"]["kind"] == "wait"
    assert go_on.status_code == 200 and finished["status"] == "completed"
    assert stopped.status_code == 200 and after["status"] == "stopped"


async def test_the_poll_wakes_a_run_whose_wait_is_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _resume_settings(tmp_path)
    settings.workspace_root.mkdir()
    store = ScheduledTriggerStore(settings.state_dir)
    store.save(_trigger("trig-soon", prompt="", workflow={"steps": [_WAIT, _WRITE]}))
    store.save(_trigger("trig-due", prompt="", workflow={"steps": [_WAIT, _WRITE]}))
    woken: list[tuple[str, str]] = []

    async def on_woken(trigger_id: str, run: Any) -> None:
        woken.append((trigger_id, run.status))

    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "cp.sqlite")) as checkpointer:
        get_session = await _make_get_session(
            settings, checkpointer, ResumeModel(responses=[]), monkeypatch
        )
        soon = await fire_trigger_now(settings.state_dir, "trig-soon", get_session)
        # Started 31 minutes ago, as if Coscribe was closed when its wait ended.
        monkeypatch.setattr(pause_steps, "clock", lambda: datetime.now() - timedelta(minutes=31))
        due = await fire_trigger_now(settings.state_dir, "trig-due", get_session)
        monkeypatch.setattr(pause_steps, "clock", datetime.now)
        fired = await poll_due_scheduled_tasks(settings.state_dir, get_session, on_ended=on_woken)

    assert soon is not None and soon.status == "waiting"
    assert due is not None and due.status == "waiting"
    assert fired == [] and woken == [("trig-due", "completed")]
    still = store.load("trig-soon")
    assert still is not None and still.runs[-1].status == "waiting"
    assert (settings.workspace_root / "out.txt").read_text(encoding="utf-8") == "done"


async def test_a_run_waiting_for_an_answer_is_reminded_once_a_day(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = ScheduledTriggerStore(settings.state_dir)
    store.save(_trigger("trig-ask", prompt="", workflow={"steps": [_ASK]}))
    _, run, _ = store.start_run("trig-ask", "manual")
    asked = datetime(2026, 11, 2, 9, 0)
    store.record_step("trig-ask", run.run_id, {
        "step_id": "ask", "status": "waiting", "started_at": asked.isoformat(),
        "pause": {"kind": "ask", "until": None, "fields": []},
    })  # fmt: skip
    store.finish_run("trig-ask", run.run_id, "needs_approval")
    bus = BackgroundEventBus()
    queue = bus.subscribe()

    async def unused(*_: object, **__: object) -> object:
        raise AssertionError("not called")

    scheduler = scheduler_module.Scheduler(
        settings, {}, bus, unused, unused, lambda: None, unused, unused
    )
    scheduler.remind_waiting(asked + timedelta(hours=5))
    scheduler.remind_waiting(asked + timedelta(days=1, hours=1))
    scheduler.remind_waiting(asked + timedelta(days=1, hours=9))
    scheduler.remind_waiting(asked + timedelta(days=2, hours=1))

    bodies = [queue.get_nowait()["body"] for _ in range(queue.qsize())]
    assert bodies == ["Waiting for your answer at Ask for the amount"] * 2
