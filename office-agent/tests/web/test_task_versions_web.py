"""A task's versions and the tasks it runs, through the server (decision 0035): the task page
lists and restores versions, saving refuses a call that can't work, and the permissions card
shows what each called task may use under its own name."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore  # noqa: E402

from .helpers import FakeToolCallingChatModel, _client_lg  # noqa: E402


def _workflow(content: str, *, url: str = "") -> dict[str, Any]:
    step = {"id": "log", "title": "Log", "kind": "tool", "tool": "write_file",
            "args": {"path": "out.txt", "content": content}}  # fmt: skip
    opened = {"id": "open", "title": "Open", "kind": "tool", "tool": "browser_navigate",
              "args": {"url": url}}  # fmt: skip
    return {"steps": [step, *([opened] if url else [])]}


def _task(client: Any, name: str, workflow: dict[str, Any]) -> Any:
    return client.post(
        "/api/scheduled-tasks",
        json={"name": name, "kind": "manual", "at": "", "workflow": workflow},
    )


def test_the_task_page_lists_compares_and_restores_versions_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client, "V", _workflow("one")).json()
        task_id = task["trigger_id"]
        client.patch(f"/api/scheduled-tasks/{task_id}", json={"workflow": _workflow("two")})
        url = f"/api/scheduled-tasks/{task_id}/versions"
        listed = client.get(url).json()
        restored = client.post(f"{url}/1/restore").json()
        after = client.get(url).json()
        listing = client.get("/api/scheduled-tasks").json()
        missing = client.post(f"{url}/9/restore")

    assert listed["current"] == 2
    assert [(v["number"], v["how"]) for v in listed["versions"]] == [(2, "edited"), (1, "created")]
    assert restored["workflow"]["steps"][0]["args"]["content"] == "one"
    assert restored["version"] == 3
    assert after["versions"][0] == {
        **after["versions"][0],
        "number": 3,
        "how": "restored",
        "from": 1,
    }
    assert next(t for t in listing if t["trigger_id"] == task_id)["version"] == 3
    assert missing.status_code == 404


def test_a_caller_is_checked_and_shows_what_its_called_task_may_use_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        called = _task(client, "Fetch", _workflow("x", url="https://sales.example.com/report"))
        called_id = called.json()["trigger_id"]
        ScheduledTriggerStore(tmp_path / "state").grant(called_id, "folders", str(tmp_path))
        call = {"id": "call", "title": "Fetch first", "kind": "run_task", "task": called_id}
        caller = {"steps": [call]}
        refused = _task(client, "Bad", {"steps": [{**call, "task": "nope"}]})
        saved = _task(client, "Report", caller)
        card = client.post("/api/workflows/permissions", json={"workflow": caller}).json()
        added = client.post(
            "/api/workflows/permissions", json={"workflow": caller, "previous": _workflow("y")}
        ).json()

    assert refused.status_code == 400 and "no longer exists" in refused.json()["error"]
    assert saved.status_code == 200
    tasks = card["permissions"]["tasks"]
    assert tasks == [{"task": called_id, "name": "Fetch", "folders": [str(tmp_path)],
                      "sites": ["sales.example.com"]}]  # fmt: skip
    assert added["added"]["tasks"] == tasks
