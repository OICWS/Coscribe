"""What a scheduled task can reach: its workspace, the Allowed folders and its own folders."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.runtime_lg import AuditLog

from .helpers import FakeToolCallingChatModel, _client_lg


def _task(client: object) -> str:
    created = client.post(  # type: ignore[attr-defined]
        "/api/scheduled-tasks", json={"name": "x", "kind": "manual", "at": "", "prompt": "p"}
    ).json()
    return str(created["trigger_id"])


def test_a_task_lists_its_workspace_the_allowed_folders_and_its_own_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared = tmp_path / "Shared reports"
    shared.mkdir()
    monkeypatch.setenv("COSCRIBE_EXTRA_WRITABLE_DIRS", str(shared))
    own = tmp_path / "Exports"
    own.mkdir()
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client)
        assert (
            client.post(f"/api/scheduled-tasks/{task}/folders", json={"path": str(own)}).status_code
            == 200
        )
        reach = client.get(f"/api/scheduled-tasks/{task}/reach").json()
        assert reach["workspace"]["id"] == "default"
        assert len(reach["workspace"]["folders"]) == 1
        assert {"path": str(shared), "permission": "write"} in reach["allowed"]
        assert reach["task"] == [str(own.resolve())]

        removed = client.delete(
            f"/api/scheduled-tasks/{task}/folders", params={"path": str(own.resolve())}
        )
        assert removed.json() == {"task": []}
        assert client.get(f"/api/scheduled-tasks/{task}/reach").json()["task"] == []

    entries = AuditLog(tmp_path / "state").read_all()
    assert any(e.tool_name == "allow_task_folder" for e in entries)


def test_only_a_folder_on_this_computer_is_allowed_for_a_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client)
        for path in ["", "relative/folder", str(tmp_path / "missing")]:
            refused = client.post(f"/api/scheduled-tasks/{task}/folders", json={"path": path})
            assert refused.status_code == 422
        assert (
            client.post(
                "/api/scheduled-tasks/nope/folders", json={"path": str(tmp_path)}
            ).status_code
            == 404
        )
        assert client.get("/api/scheduled-tasks/nope/reach").status_code == 404


def test_a_folder_input_is_checked_against_the_tasks_reach(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_only = tmp_path / "2025"
    read_only.mkdir()
    monkeypatch.setenv("COSCRIBE_EXTRA_READABLE_DIRS", str(read_only))
    outside = tmp_path / "Archive"
    outside.mkdir()
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client)
        reach = client.get(f"/api/scheduled-tasks/{task}/reach").json()
        workspace = Path(reach["workspace"]["folders"][0])

        def check(path: str) -> dict[str, object]:
            return client.post("/api/reach/check", json={"task": task, "path": path}).json()

        relative = check("reports")
        assert relative["inside"] == "workspace"
        assert relative["path"] == str(workspace / "reports")
        assert relative["exists"] is False and relative["writable"] is True

        in_allowed = check(str(read_only))
        assert (in_allowed["inside"], in_allowed["root"]) == ("allowed", str(read_only))
        assert (in_allowed["writable"], in_allowed["exists"]) == (False, True)
        assert check(str(outside))["inside"] is None

        client.post(f"/api/scheduled-tasks/{task}/folders", json={"path": str(outside)})
        assert check(str(outside / "Sales"))["inside"] == "task"

        # A task not saved yet is checked against the workspace it will use.
        unsaved = client.post(
            "/api/reach/check", json={"environment": "default", "path": str(outside)}
        )
        assert unsaved.json()["inside"] is None
        assert client.post("/api/reach/check", json={"path": " "}).status_code == 422
