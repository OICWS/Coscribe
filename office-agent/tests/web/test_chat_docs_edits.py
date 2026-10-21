# ruff: noqa: E402
"""Web tests: the user's edits of a Word document in the app are told to coscribe in front of the
next message (decision 0019)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.tools.office.document_tools import build_document_tools

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until, _tool_call


def test_an_edit_made_in_the_editor_is_told_once_in_front_of_the_next_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = {t.__name__: t for t in build_document_tools(workspace)}  # type: ignore[attr-defined]
    tools["write_docx"](path="plan.docx", content="# Plan\n\nFirst paragraph.\n")
    read = AIMessage(content="", tool_calls=[_tool_call("c1", "read_docx", {"path": "plan.docx"})])
    model = FakeToolCallingChatModel(
        responses=[read, *(AIMessage(content=word) for word in ("one", "two", "three"))]
    )
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_docs_edits") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json({"type": "user_message", "text": "first"})
            _receive_until(ws, "tasks_changed")
            blocks = client.get(
                "/api/threads/t_docs_edits/docs/blocks", params={"path": "plan.docx"}
            ).json()
            blocks["blocks"][1]["runs"] = [{"t": "First paragraph, reworded."}]
            saved = client.put(
                "/api/threads/t_docs_edits/docs/blocks",
                json={
                    "path": "plan.docx",
                    "version": blocks["version"],
                    "blocks": blocks["blocks"],
                },
            )
            assert saved.status_code == 200
            ws.send_json({"type": "user_message", "text": "second"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "third"})
            _receive_until(ws, "tasks_changed")

    after_edit = [str(calls[-1].content) for calls in model.received]
    assert "The user edited plan.docx in the app" in after_edit[-2]
    assert "First paragraph, reworded." in after_edit[-2]
    assert after_edit[-2].rstrip().endswith("second")
    assert "The user edited plan.docx" not in after_edit[-1]
