# ruff: noqa: E402
"""Web tests: a conversation's folders and workspace."""

import json
from pathlib import Path

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


def test_workspace_query_param_resolves_workspace_on_connect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-a"
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/t_ws_qs?workspace={chosen}") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history

    assert state["workspace_root"] == str(chosen)
    assert state["workspace_explicit"] is True
    assert state["folders"] == [str(chosen)]
    sidecar = tmp_path / "state" / "t_ws_qs.workspace"
    assert json.loads(sidecar.read_text(encoding="utf-8")) == [str(chosen)]


def test_new_thread_without_workspace_falls_back_to_settings_workspace_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_ws_default") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history

    assert state["workspace_root"] == str(tmp_path / "workspace")
    assert state["workspace_explicit"] is False
    assert not (tmp_path / "state" / "t_ws_default.workspace").exists()


def test_workspace_choice_persists_across_reconnect_without_the_query_param(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-b"
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as first_process:
        with first_process.websocket_connect(f"/ws/t_ws_persist?workspace={chosen}") as ws:
            ws.receive_json()
            ws.receive_json()  # history

    # Fresh create_app_lg() -- empty in-memory sessions dict, same tmp_path
    # on disk -- so a reconnect with no ?workspace= this time can only pick
    # the choice back up from the sidecar, not in-process state.
    with _client_lg(tmp_path, monkeypatch, fake_model) as second_process:
        with second_process.websocket_connect("/ws/t_ws_persist") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history

    assert state["workspace_root"] == str(chosen)


def test_set_folders_changes_a_conversations_folders_any_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "project-first"
    second = tmp_path / "project-second"
    first.mkdir()
    second.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_ws_folders") as ws:
            ws.receive_json()  # state (falls back to settings.workspace_root)
            ws.receive_json()  # history

            ws.send_json({"type": "set_folders", "folders": [str(first)]})
            one = ws.receive_json()
            ws.send_json({"type": "set_folders", "folders": [str(first), str(second)]})
            two = ws.receive_json()
            ws.send_json({"type": "set_folders", "folders": [str(second)]})
            swapped = ws.receive_json()

    assert one["workspace_root"] == str(first)
    assert one["workspace_explicit"] is True
    assert two["folders"] == [str(first), str(second)]
    assert swapped["workspace_root"] == str(second)
    assert swapped["folders"] == [str(second)]
    sidecar = tmp_path / "state" / "t_ws_folders.workspace"
    assert json.loads(sidecar.read_text(encoding="utf-8")) == [str(second)]


def test_removing_every_folder_returns_to_the_default_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-gone"
    chosen.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/t_ws_clear?workspace={chosen}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "set_folders", "folders": []})
            cleared = ws.receive_json()

    assert cleared["folders"] == []
    assert cleared["workspace_explicit"] is False
    assert cleared["workspace_root"] == str(tmp_path / "workspace")
    assert not (tmp_path / "state" / "t_ws_clear.workspace").exists()


def test_a_folder_that_does_not_exist_is_refused_and_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kept = tmp_path / "project-kept"
    kept.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/t_ws_bad?workspace={kept}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            missing = tmp_path / "missing"
            ws.send_json({"type": "set_folders", "folders": [str(kept), str(missing)]})
            refused = ws.receive_json()

    assert refused["type"] == "error"
    assert "isn't an existing folder" in refused["message"]
    sidecar = tmp_path / "state" / "t_ws_bad.workspace"
    assert json.loads(sidecar.read_text(encoding="utf-8")) == [str(kept)]


def test_a_single_path_sidecar_from_before_multiple_folders_still_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-legacy"
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "state" / "t_ws_legacy.workspace").write_text(str(chosen), encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_ws_legacy") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history

    assert state["folders"] == [str(chosen)]


def test_the_agent_can_write_into_a_conversations_second_folder(
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
        with client.websocket_connect("/ws/t_ws_extra") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "set_folders", "folders": [str(main), str(extra)]})
            ws.receive_json()  # state
            ws.send_json({"type": "user_message", "text": "write hi into the second folder"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    assert (extra / "note.txt").read_text() == "hi"


def test_delete_thread_removes_workspace_sidecar_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "project-d"
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/t_ws_delete?workspace={chosen}") as ws:
            ws.receive_json()
            ws.receive_json()  # history
        sidecar = tmp_path / "state" / "t_ws_delete.workspace"
        assert sidecar.is_file()

        client.delete("/api/threads/t_ws_delete")

        assert not sidecar.is_file()


def test_write_file_lands_in_the_threads_own_workspace_not_the_global_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end proof that a per-thread workspace_root actually reaches
    the tool layer (coordinator.py's build_coordinator_agent -- not just
    that the WS "state" event reports the right string, which the other
    workspace tests above already cover)."""
    custom_workspace = tmp_path / "custom-project"
    custom_workspace.mkdir()
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/t_ws_write?workspace={custom_workspace}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"

            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    assert (custom_workspace / "note.txt").read_text() == "hi"
    assert not (tmp_path / "workspace" / "note.txt").exists()


def test_edit_environment_changes_the_folders_of_a_conversation_that_is_not_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        assert client.get("/api/threads/t_env_closed/folders").json() == {"folders": []}
        saved = client.put(
            "/api/threads/t_env_closed/folders",
            json={"folders": [str(first), str(second), str(first)]},
        )
        assert saved.json() == {"folders": [str(first), str(second)]}
        assert client.get("/api/threads/t_env_closed/folders").json() == saved.json()
        refused = client.put(
            "/api/threads/t_env_closed/folders", json={"folders": [str(tmp_path / "gone")]}
        )
        assert refused.status_code == 422
        with client.websocket_connect("/ws/t_env_closed") as ws:
            state = ws.receive_json()
    assert state["folders"] == [str(first), str(second)]


def test_edit_environment_changes_a_live_conversations_agent_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "live"
    chosen.mkdir()
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_env_live") as ws:
            ws.receive_json()
            ws.receive_json()  # history
        saved = client.put("/api/threads/t_env_live/folders", json={"folders": [str(chosen)]})
        assert saved.json() == {"folders": [str(chosen)]}
        refused = client.put(
            "/api/threads/t_env_live/folders", json={"folders": [str(tmp_path / "gone")]}
        )
        assert refused.status_code == 422
        assert "isn't an existing folder" in refused.json()["error"]
        with client.websocket_connect("/ws/t_env_live") as ws:
            state = ws.receive_json()
    assert state["workspace_root"] == str(chosen)
