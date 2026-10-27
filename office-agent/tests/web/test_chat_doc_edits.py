# ruff: noqa: E402
"""Web tests: the user's edits of a Doc in the app are told to coscribe in front of the next message
(decision 0025)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until, _tool_call

CONTENT = "---\ncoscribe: doc\ntitle: Plan\n---\n\n# Plan\n\nFirst paragraph.\n"


def test_an_edit_made_in_the_editor_is_told_once_in_front_of_the_next_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "plan.md").write_text(CONTENT, encoding="utf-8")
    read = AIMessage(content="", tool_calls=[_tool_call("c1", "read_file", {"path": "plan.md"})])
    model = FakeToolCallingChatModel(
        responses=[read, *(AIMessage(content=word) for word in ("one", "two", "three"))]
    )
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_doc_edits") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json({"type": "user_message", "text": "first"})
            _receive_until(ws, "tasks_changed")
            blocks = client.get(
                "/api/threads/t_doc_edits/doc/blocks", params={"path": "plan.md"}
            ).json()
            saved = client.put(
                "/api/threads/t_doc_edits/doc/blocks",
                json={
                    "path": "plan.md",
                    "version": blocks["version"],
                    "edits": [
                        {
                            "op": "replace",
                            "index": 1,
                            "expected": "First paragraph.",
                            "text": "First paragraph, reworded.",
                        }
                    ],
                },
            )
            assert saved.status_code == 200
            ws.send_json({"type": "user_message", "text": "second"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "third"})
            _receive_until(ws, "tasks_changed")

    after_edit = [str(calls[-1].content) for calls in model.received]
    assert "The user edited plan.md in the app" in after_edit[-2]
    assert "First paragraph, reworded." in after_edit[-2]
    assert after_edit[-2].rstrip().endswith("second")
    assert "The user edited plan.md" not in after_edit[-1]
