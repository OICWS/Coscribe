"""A run with a parallel step (decision 0036), through the server: retrying a step inside a
lane goes on in that lane, and the lane that finished isn't run again."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from .helpers import FakeToolCallingChatModel, _client_lg, _wait_for_run_status


def _workflow(allowed: str) -> dict[str, Any]:
    write = {
        "id": "write",
        "kind": "tool",
        "title": "Write",
        "tool": "write_file",
        "args": {"path": "out/a.md", "content": "A", "overwrite": True},
    }
    check = {
        "id": "allowed",
        "kind": "check",
        "title": "Allowed",
        "conditions": [{"left": {"value": allowed}, "op": "eq", "right": {"value": "yes"}}],
    }
    lanes = [{"label": "Write", "steps": [write]}, {"label": "Check", "steps": [check]}]
    step = {"id": "both", "kind": "parallel", "title": "Both", "lanes": lanes}
    return {"steps": [step]}


def test_retrying_a_lane_step_goes_on_in_that_lane_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="unused")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        created = client.post(
            "/api/scheduled-tasks",
            json={"name": "Both", "kind": "manual", "at": "", "workflow": _workflow("no")},
        ).json()
        trigger_id = created["trigger_id"]
        run = client.post(f"/api/scheduled-tasks/{trigger_id}/run", json={}).json()["run"]
        failed = _wait_for_run_status(client, trigger_id, run["run_id"])

        fixed = {"name": "Both", "kind": "manual", "at": "", "workflow": _workflow("yes")}
        assert client.put(f"/api/scheduled-tasks/{trigger_id}", json=fixed).status_code == 200
        retry = f"/api/scheduled-tasks/{trigger_id}/runs/{run['run_id']}/retry"
        assert client.post(retry, json={"step_id": "allowed"}).status_code == 200
        done = _wait_for_run_status(client, trigger_id, run["run_id"])
        activity = client.get(f"/api/threads/{run['thread_id']}/activity").json()

    assert failed["status"] == "failed"
    assert failed["error"] == "Both: Check: 1 of 1 checks failed"
    assert done["status"] == "completed", done["error"]
    assert {t["name"]: t["count"] for t in activity["tools"]} == {"write_file": 1}
    statuses = {s["step_id"]: s["status"] for s in done["steps"]}
    assert statuses == {"write": "done", "allowed": "done", "both": "done"}
