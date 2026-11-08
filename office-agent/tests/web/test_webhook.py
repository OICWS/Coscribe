"""A task that starts on an event a program on the machine sends it (decision 0040), through the
listener's real socket: the key, the refusals, the sample, the limits and the listener's life."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from coscribe.runtime_lg.audit import AuditLog
from coscribe.tools import ScheduledTriggerStore

from .helpers import FakeToolCallingChatModel, _client_lg, _settings, _wait_for_run_status

_WORKFLOW = {
    "inputs": [{"name": "amount", "label": "Amount", "type": "number"}],
    "steps": [
        {
            "id": "s",
            "title": "Write",
            "kind": "tool",
            "tool": "write_file",
            "args": {"path": "amount.txt", "content": "Amount: {{amount}}"},
        }
    ],
}


def _task(client: Any, **watch: Any) -> dict[str, Any]:
    response = client.post(
        "/api/scheduled-tasks",
        json={"name": "Invoices", "kind": "webhook", "at": "", "workflow": _WORKFLOW,
              "approval_mode": "auto", "watch": watch},
    )  # fmt: skip
    assert response.status_code == 200, response.text
    return response.json()


def _send(url: str, key: str | None, body: Any, **headers: str) -> httpx.Response:
    sent = {"Content-Type": "application/json", **headers}
    if key is not None:
        sent["Authorization"] = f"Bearer {key}"
    return httpx.post(url, content=json.dumps(body), headers=sent, timeout=10)


def test_an_event_with_the_key_starts_a_run_and_anything_else_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client, inputs_from={"amount": "total"})
        hook = client.get(f"/api/scheduled-tasks/{task['trigger_id']}/webhook").json()
        assert hook["listening"] and hook["url"].startswith("http://127.0.0.1:")
        url, key = hook["url"], hook["key"]
        other = url.rsplit("/", 1)[0] + "/nope"

        assert _send(url, None, {"total": 1}).status_code == 401
        assert _send(url, "wrong", {"total": 1}).status_code == 401
        # An unknown task answers as a wrong key does: the answer tells nothing about which exist.
        assert _send(other, key, {"total": 1}).json() == _send(url, "x", {}).json()
        page = _send(url, key, {"total": 1}, Origin="https://example.com")
        assert page.status_code == 403
        not_json = httpx.post(url, content="{}", headers={"Authorization": f"Bearer {key}"})
        assert not_json.status_code == 415
        assert _send(url, key, "x" * 70_000).status_code == 413
        refused = _send(url, key, {"total": "next week"})
        assert refused.status_code == 400 and "Amount needs a number" in refused.json()["error"]
        assert httpx.get(url).status_code == 405

        started = _send(url, key, {"total": 12.5, "id": "inv-1"})
        assert started.status_code == 202, started.text
        run = _wait_for_run_status(client, task["trigger_id"], started.json()["run"])
        assert run["status"] == "completed", run
        assert run["source"] == "webhook" and run["inputs"] == {"amount": 12.5}
        assert run["event"] == {"item": {"total": 12.5, "id": "inv-1"}}

        [listed] = client.get("/api/scheduled-tasks").json()
        assert [m["reason"] for m in listed["webhook"]["missed"]] == [refused.json()["error"]]
        assert listed["webhook"]["last_event"]["status"] == 202
        assert "key" not in json.dumps(listed["webhook"])

        new = client.post(f"/api/scheduled-tasks/{task['trigger_id']}/webhook/key").json()["key"]
        assert new != key and _send(url, key, {"total": 1}).status_code == 401

    entries = AuditLog(_settings(tmp_path).state_dir).read_all()
    events = [e for e in entries if e.reason == "webhook_event"]
    # Only events that came with the task's key: a request without it never reached a task.
    assert [e.detail.split()[0] for e in events if e.detail] == ["413", "400", "202"]
    assert all("12.5" not in json.dumps(e.arguments) for e in events)


def test_a_sample_is_kept_without_running_and_a_paused_task_takes_no_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        task = _task(client)
        trigger_id = task["trigger_id"]
        waiting = client.post(f"/api/scheduled-tasks/{trigger_id}/webhook/sample",
                              json={"waiting": True}).json()  # fmt: skip
        assert waiting["waiting"] is True
        url, key = waiting["url"], waiting["key"]

        kept = _send(url, key, {"amount": 3, "customer": {"name": "Ada"}})
        assert kept.status_code == 200
        hook = client.get(f"/api/scheduled-tasks/{trigger_id}/webhook").json()
        assert hook["waiting"] is False and hook["sample"]["customer"] == {"name": "Ada"}
        [listed] = client.get("/api/scheduled-tasks").json()
        assert listed["runs"] == []

        client.post(f"/api/scheduled-tasks/{trigger_id}/pause")
        # The last task that takes events is paused: the listener stops.
        with pytest.raises(httpx.ConnectError):
            _send(url, key, {"amount": 1})
        client.post(f"/api/scheduled-tasks/{trigger_id}/resume")
        port = client.get(f"/api/scheduled-tasks/{trigger_id}/webhook").json()["url"]
        assert _send(port, key, {"amount": 1}).status_code == 202


def test_events_over_the_limits_get_429(tmp_path: Path) -> None:
    from datetime import datetime

    from coscribe.tools import ScheduledRun
    from coscribe.tools.bookkeeping.scheduled_tasks import create_trigger
    from coscribe.workflow_spec import parse_workflow

    store = ScheduledTriggerStore(_settings(tmp_path).state_dir)
    task = create_trigger(store, name="t", kind="webhook", at="", prompt="", workflow=_WORKFLOW,
                          watch={"per_hour": 2})  # fmt: skip
    specs = list(parse_workflow(_WORKFLOW).inputs)
    now = datetime.now().isoformat()
    runs = [ScheduledRun(run_id=f"r{n}", thread_id="t", started_at=now, source="webhook",
                         status="completed") for n in range(2)]  # fmt: skip
    over = store.webhooks.take(task.trigger_id, task.schedule, specs, runs, {"amount": 1})
    assert over.status == 429 and over.inputs is None
    going = [ScheduledRun(run_id=f"g{n}", thread_id="t", started_at="2000-01-01",
                          source="webhook", status="running") for n in range(3)]  # fmt: skip
    task.schedule.per_hour = 30
    assert store.webhooks.take(task.trigger_id, task.schedule, specs, going, {}).status == 429
    one = {"amount": 1}
    assert store.webhooks.take(task.trigger_id, task.schedule, specs, [], one).status == 202


def test_the_key_lives_in_the_keychain_and_goes_with_the_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import create_trigger

    from .helpers import _install_fake_keyring

    keychain = _install_fake_keyring(monkeypatch)
    store = ScheduledTriggerStore(_settings(tmp_path).state_dir)
    task = create_trigger(store, name="t", kind="webhook", at="", prompt="", workflow=_WORKFLOW)
    assert store.webhooks.key(task.trigger_id) is None
    store.webhooks.ensure_key(task.trigger_id)
    key = store.webhooks.key(task.trigger_id)
    assert key and store.webhooks.key(task.trigger_id) == key
    store.webhooks.ensure_key(task.trigger_id)
    assert store.webhooks.key(task.trigger_id) == key
    on_disk = (tmp_path / "state" / "task_memory" / f"{task.trigger_id}.webhook.json").read_text()
    assert key not in on_disk and list(keychain.store.values()) == [key]
    assert store.webhooks.accepts(task.trigger_id, key)
    assert not store.webhooks.accepts(task.trigger_id, key + "x")
    store.delete(task.trigger_id)
    assert keychain.store == {}


def test_only_a_task_with_steps_starts_on_events_and_the_agent_cant_switch_one(
    tmp_path: Path,
) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import (
        build_scheduled_task_tools,
        create_trigger,
    )

    store = ScheduledTriggerStore(_settings(tmp_path).state_dir)
    with pytest.raises(ValueError, match="Only a task with steps can start on an event"):
        create_trigger(store, name="t", kind="webhook", at="", prompt="p")
    task = create_trigger(store, name="t", kind="manual", at="", prompt="", workflow=_WORKFLOW)
    tools = {t.__name__: t for t in build_scheduled_task_tools(store.state_dir)}
    with pytest.raises(ValueError, match="Only the person"):
        tools["edit_scheduled_task"](task.trigger_id, kind="webhook")
