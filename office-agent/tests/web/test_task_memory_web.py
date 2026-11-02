"""A task's memory through the server (decision 0034): the task page reads it, and a person
sets or clears a value, checked against what the task declares."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools import TaskMemory  # noqa: E402

from .helpers import FakeToolCallingChatModel, _client_lg  # noqa: E402

_WORKFLOW = {
    "memory": [{"name": "seen", "label": "Already handled", "type": "list", "initial": []}],
    "steps": [{"id": "log", "title": "Log", "kind": "tool", "tool": "write_file",
               "args": {"path": "out.txt", "content": "{{memory.seen}}"}}],
}  # fmt: skip


def test_the_task_page_reads_and_edits_what_a_task_remembers_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = client.post(
            "/api/scheduled-tasks",
            json={"name": "M", "kind": "manual", "at": "", "workflow": _WORKFLOW},
        ).json()
        url = f"/api/scheduled-tasks/{task['trigger_id']}/memory"
        empty = client.get(url).json()
        TaskMemory(tmp_path / "state").keep(task["trigger_id"], {"seen": ["a"]}, "r1")
        kept = client.get(url).json()
        edited = client.put(f"{url}/seen", json={"value": ["a", "b"]}).json()
        wrong = client.put(f"{url}/seen", json={"value": "a"})
        unknown = client.put(f"{url}/other", json={"value": "a"})
        cleared = client.put(f"{url}/seen", json={"value": None}).json()
        missing = client.get("/api/scheduled-tasks/nope/memory")
        deleted = client.delete(f"/api/scheduled-tasks/{task['trigger_id']}")

    assert task["workflow"]["memory"][0]["name"] == "seen"
    assert empty == {"memory": {}}
    assert kept["memory"]["seen"]["value"] == ["a"] and kept["memory"]["seen"]["by"] == "r1"
    assert edited["memory"]["seen"]["value"] == ["a", "b"]
    assert edited["memory"]["seen"]["by"] == "you"
    assert wrong.status_code == 400 and "keeps a list" in wrong.json()["error"]
    assert unknown.status_code == 404
    assert cleared == {"memory": {}}
    assert missing.status_code == 404
    assert deleted.status_code == 200
    assert TaskMemory(tmp_path / "state").entries(task["trigger_id"]) == {}
