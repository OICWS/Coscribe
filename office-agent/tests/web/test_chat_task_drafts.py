# ruff: noqa: E402
"""Web tests: the chat model drafting, testing and editing a scheduled task."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
)

from coscribe.conversation import session as conversation_session

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_the_chat_model_tests_its_draft_and_fixes_what_failed_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore

    ids = iter(["d1", "d2"])
    monkeypatch.setattr(conversation_session, "_new_draft_id", lambda: next(ids))
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "input.txt").write_text("data", encoding="utf-8")

    def reading(path: str) -> dict[str, Any]:
        return {"steps": [{"id": "read", "kind": "tool", "title": "Read it", "tool": "read_file",
                           "args": {"path": path}, "save_as": "text"}]}  # fmt: skip

    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="", tool_calls=[_tool_call("c1", "read_file", {"path": "input.txt"})]
            ),
            AIMessage(content="", tool_calls=[_tool_call("c2", "draft_workflow", {"name": ""})]),
            AIMessage(content=json.dumps({"name": "Read", "workflow": reading("inptu.txt")})),
            AIMessage(
                content="", tool_calls=[_tool_call("c3", "test_workflow", {"draft_id": "d1"})]
            ),
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call(
                        "c4",
                        "revise_workflow",
                        {"draft_id": "d1", "request": "step read failed: the file is input.txt"},
                    )
                ],
            ),
            AIMessage(
                content=json.dumps(
                    {"workflow": reading("input.txt"), "changes": ["Reads input.txt"], "notes": []}
                )
            ),
            AIMessage(
                content="", tool_calls=[_tool_call("c5", "test_workflow", {"draft_id": "d2"})]
            ),
            AIMessage(content="The test passed; review it on the card."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_test_draft") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/accept-edits"})
            _receive_until(ws, "state")
            ws.send_json({"type": "user_message", "text": "read input.txt, then make it fixed"})
            messages: list[dict[str, Any]] = []
            while not messages or messages[-1]["type"] != "tasks_changed":
                messages.append(ws.receive_json())
                if messages[-1]["type"] == "approval_required":
                    assert messages[-1]["tool_name"] == "test_workflow"
                    ws.send_json(
                        {"type": "approval_response", "id": messages[-1]["id"], "approved": True}
                    )

    first, second = [
        m["result"]
        for m in messages
        if m["type"] == "tool_result" and m["tool_name"] == "test_workflow"
    ]
    assert first["draft_id"] == "d1" and first["status"] == "failed", first
    assert first["failed_step"] == "read" and "inptu.txt" in first["error"]
    assert "revise_workflow" in first["next"]
    [revised] = [
        m["result"]
        for m in messages
        if m["type"] == "tool_result" and m["tool_name"] == "revise_workflow"
    ]
    assert revised["draft_id"] == "d2" and "trigger_id" not in revised
    assert revised["changes"] == ["Reads input.txt"]
    assert "step read failed" in str(fake_model.received[5][-1].content)
    assert second["status"] == "passed", second
    assert second["steps"][0]["status"] == "done" and second["steps"][0]["output"] == "data"
    progress = [m for m in messages if m["type"] == "workflow_test_progress"]
    assert {m["tool_call_id"] for m in progress} == {"c3", "c5"}
    assert progress[-1]["done"] == progress[-1]["total"] == 1
    assert ScheduledTriggerStore(tmp_path / "state").list_all() == []


def test_testing_an_unknown_draft_says_so_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="", tool_calls=[_tool_call("c1", "test_workflow", {"draft_id": "nope"})]
            ),
            AIMessage(content="There's no such draft."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_test_unknown") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "test it"})
            approval = _receive_until(ws, "approval_required")[-1]
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    [result] = [m["result"] for m in messages if m["type"] == "tool_result"]
    assert result == {"status": "failed", "error": "There's no draft 'nope' in this conversation."}


def test_editing_a_saved_task_asks_the_user_with_the_whole_task_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore, create_trigger

    store = ScheduledTriggerStore(tmp_path / "state")
    task = create_trigger(
        store, name="Morning digest", kind="daily", at="09:00", prompt="Summarize the news."
    )
    edit = _tool_call("c1", "edit_scheduled_task", {"trigger_id": task.trigger_id, "at": "08:00"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[edit]), AIMessage(content="Left it as is.")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_edit_task") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "run it at 8 instead"})
            draft_event = _receive_until(ws, "task_draft_required")[-1]
            ws.send_json(
                {
                    "type": "question_response",
                    "id": draft_event["id"],
                    "answer": "The user dismissed the draft without saving it.",
                }
            )
            _receive_until(ws, "tasks_changed")

    draft = draft_event["draft"]
    assert draft["trigger_id"] == task.trigger_id
    assert draft["changed"] == ["at"]
    assert (draft["name"], draft["kind"], draft["at"]) == ("Morning digest", "daily", "08:00")
    assert draft["prompt"] == "Summarize the news."
    unchanged = store.load(task.trigger_id)
    assert unchanged is not None and unchanged.schedule.at == "09:00"
