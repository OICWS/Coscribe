# ruff: noqa: E402
"""Web tests: a conversation's environment and the folders it works in."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
)

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def _environment(client: Any, name: str, *folders: Path) -> str:
    response = client.post(
        "/api/environments", json={"name": name, "folders": [str(f) for f in folders]}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def _switch(ws: Any, env_id: str) -> dict[str, Any]:
    ws.send_json({"type": "set_environment", "environment": env_id})
    return dict(ws.receive_json())


def _environments(client: Any) -> dict[str, dict[str, Any]]:
    return {e["name"]: e for e in client.get("/api/environments").json()["environments"]}


def _environment_of(client: Any, thread_id: str) -> str:
    with client.websocket_connect(f"/ws/{thread_id}") as ws:
        return str(ws.receive_json()["environment"])


def test_a_new_conversation_uses_default_and_the_default_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_ws_default") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history
        listed = _environments(client)

    assert state["environment"] == "default"
    assert state["workspace_root"] == str(tmp_path / "workspace")
    assert state["workspace_explicit"] is False
    assert list(listed) == ["Default"]


def test_choosing_an_environment_moves_the_conversation_into_its_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "project-first", tmp_path / "project-second"
    first.mkdir()
    second.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        both = _environment(client, "Both", first, second)
        with client.websocket_connect("/ws/t_ws_folders") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            moved = _switch(ws, both)
            back = _switch(ws, "default")
            refused = _switch(ws, "env_gone")

    assert moved["environment"] == both
    assert moved["workspace_root"] == str(first)
    assert moved["folders"] == [str(first), str(second)]
    assert back["environment"] == "default"
    assert back["folders"] == [] and back["workspace_explicit"] is False
    assert refused["type"] == "error"


def test_the_choice_is_kept_across_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-b"
    chosen.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as first_process:
        env_id = _environment(first_process, "B", chosen)
        with first_process.websocket_connect("/ws/t_ws_persist") as ws:
            ws.receive_json()
            ws.receive_json()  # history
            _switch(ws, env_id)

    with _client_lg(tmp_path, monkeypatch, fake_model) as second_process:
        with second_process.websocket_connect("/ws/t_ws_persist") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history

    assert state["environment"] == env_id
    assert state["workspace_root"] == str(chosen)


def test_an_environment_refuses_a_missing_folder_a_taken_name_and_deleting_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        missing = client.post(
            "/api/environments", json={"name": "X", "folders": [str(tmp_path / "missing")]}
        )
        taken = client.post("/api/environments", json={"name": "default"})
        nameless = client.post("/api/environments", json={"name": "  "})
        default_gone = client.delete("/api/environments/default")

    assert missing.status_code == 422 and "isn't an existing folder" in missing.json()["error"]
    assert taken.status_code == 422 and "already" in taken.json()["error"]
    assert nameless.status_code == 422
    assert default_gone.status_code == 422


def test_settings_from_before_become_environments_on_the_first_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    shared = tmp_path / "shared"
    # A thread from before multiple folders holds one bare path.
    (state_dir / "t_a.workspace").write_text(str(shared), encoding="utf-8")
    (state_dir / "t_a.title").write_text("Quarterly report", encoding="utf-8")
    (state_dir / "t_b.workspace").write_text(json.dumps([str(shared)]), encoding="utf-8")
    (state_dir / "t_c.network.json").write_text(
        json.dumps({"mode": "none", "domains": []}), encoding="utf-8"
    )
    (state_dir / "t_d.network.json").write_text(
        json.dumps({"mode": "limited", "domains": ["*"]}), encoding="utf-8"
    )
    (state_dir / "unisolated-conversations.json").write_text(
        json.dumps({"t_c": "2026-10-01"}), encoding="utf-8"
    )
    (state_dir / "scheduled-x-r1.workspace").write_text(json.dumps([str(shared)]), "utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        listed = _environments(client)
        uses = {t: _environment_of(client, t) for t in ("t_a", "t_b", "t_c", "t_d")}

    assert sorted(listed) == ["Conversation", "Default", "Quarterly report"]
    assert listed["Quarterly report"]["folders"] == [str(shared)]
    assert listed["Quarterly report"]["used_by"] == 2
    assert listed["Conversation"]["network"]["mode"] == "none"
    assert listed["Conversation"]["unisolated"] is True
    assert uses["t_a"] == uses["t_b"] == listed["Quarterly report"]["id"]
    assert uses["t_c"] == listed["Conversation"]["id"]
    assert uses["t_d"] == "default"


def test_the_agent_can_write_into_an_environments_second_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main = tmp_path / "project-main"
    extra = tmp_path / "project-extra"
    main.mkdir()
    extra.mkdir()
    call = _tool_call("call_1", "write_file", {"path": str(extra / "note.txt"), "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        env_id = _environment(client, "Two folders", main, extra)
        with client.websocket_connect("/ws/t_ws_extra") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            _switch(ws, env_id)
            ws.send_json({"type": "user_message", "text": "write hi into the second folder"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    assert (extra / "note.txt").read_text() == "hi"


def test_write_file_lands_in_the_environments_main_folder_not_the_global_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_workspace = tmp_path / "custom-project"
    custom_workspace.mkdir()
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        env_id = _environment(client, "Custom", custom_workspace)
        with client.websocket_connect("/ws/t_ws_write") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            _switch(ws, env_id)
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    assert (custom_workspace / "note.txt").read_text() == "hi"
    assert not (tmp_path / "workspace" / "note.txt").exists()


def test_editing_an_environment_moves_its_live_conversations_but_not_mid_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before, after = tmp_path / "before", tmp_path / "after"
    before.mkdir()
    after.mkdir()
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        env_id = _environment(client, "Moving", before)
        with client.websocket_connect("/ws/t_env_live") as ws:
            ws.receive_json()
            ws.receive_json()  # history
            _switch(ws, env_id)
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            mid_turn = client.put(f"/api/environments/{env_id}", json={"folders": [str(after)]})
            switch_mid_turn = _switch(ws, "default")
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")
            between = client.put(f"/api/environments/{env_id}", json={"folders": [str(after)]})
            moved = _receive_until(ws, "state")[-1]

    assert mid_turn.status_code == 409
    assert switch_mid_turn["type"] == "error"
    assert (before / "note.txt").read_text() == "hi"
    assert between.status_code == 200
    assert moved["environment"] == env_id
    assert moved["workspace_root"] == str(after)


def test_deleting_an_environment_moves_its_conversations_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "doomed"
    chosen.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        env_id = _environment(client, "Doomed", chosen)
        with client.websocket_connect("/ws/t_env_doomed") as ws:
            ws.receive_json()
            ws.receive_json()  # history
            _switch(ws, env_id)
            deleted = client.delete(f"/api/environments/{env_id}")
            moved = _receive_until(ws, "state")[-1]

    assert deleted.json() == {"moved": 1}
    assert moved["environment"] == "default"
    assert moved["workspace_explicit"] is False


def test_a_folder_allowed_on_default_gets_the_conversation_an_environment_of_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allowed = tmp_path / "Invoices"
    allowed.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_env_add") as ws:
            ws.receive_json()
            ws.receive_json()  # history
            ws.send_json({"type": "add_folder", "folder": str(allowed)})
            _receive_until(ws, "state")  # the folders, still on Default
            added = _receive_until(ws, "state")[-1]
        listed = _environments(client)

    assert listed["Default"]["folders"] == []
    assert listed["Invoices"]["folders"] == [str(tmp_path / "workspace"), str(allowed)]
    assert added["environment"] == listed["Invoices"]["id"]
    assert added["folders"] == [str(tmp_path / "workspace"), str(allowed)]
