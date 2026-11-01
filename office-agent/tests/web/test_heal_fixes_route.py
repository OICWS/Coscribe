# ruff: noqa: E402
"""Web tests: a run's report offers its heals as a fix the person saves into the task."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore

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
