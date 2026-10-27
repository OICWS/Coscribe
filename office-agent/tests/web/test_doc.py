# ruff: noqa: E402
"""Web tests: the Doc editor's routes (decision 0025)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from .helpers import FakeToolCallingChatModel, _client_lg

CONTENT = "---\ncoscribe: doc\ntitle: Plan\n---\n\n# Plan\n\nFirst paragraph.\n\n- one\n- two\n"
URL = "/api/threads/t_one/doc/blocks"


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "plan.md").write_text(CONTENT, encoding="utf-8")
    return workspace


def test_the_blocks_are_read_and_the_changed_one_is_saved_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        read = client.get(URL, params={"path": "plan.md"}).json()
        edits = [{"op": "replace", "index": 1, "expected": "First paragraph.", "text": "Changed."}]
        body = {"path": "plan.md", "version": read["version"], "edits": edits}
        saved = client.put(URL, json=body)
        stale = client.put(URL, json=body)

    assert [b["kind"] for b in read["blocks"]] == ["heading", "paragraph", "list"]
    assert saved.status_code == 200
    assert saved.json()["blocks"][1]["text"] == "Changed."
    assert saved.json()["version"] != read["version"]
    assert (workspace / "plan.md").read_text(encoding="utf-8") == CONTENT.replace(
        "First paragraph.", "Changed."
    )
    assert stale.status_code == 409 and stale.json()["changed"] is True


def test_what_is_not_a_doc_or_cannot_be_saved_is_refused_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "notes.md").write_text("# Just notes\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("x", encoding="utf-8")
    (workspace / "broken.md").write_bytes(b"\xff\xfe\x00 not text")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        missing = client.get(URL, params={"path": "nope.md"})
        no_marker = client.get(URL, params={"path": "notes.md"})
        not_markdown = client.get(URL, params={"path": "notes.txt"})
        outside = client.get(URL, params={"path": "../secret.md"})
        broken = client.get(URL, params={"path": "broken.md"})
        read = client.get(URL, params={"path": "plan.md"}).json()
        bad = client.put(
            URL,
            json={
                "path": "plan.md",
                "version": read["version"],
                "edits": [{"op": "delete", "index": 1, "expected": "something else"}],
            },
        )
        unmarked = client.put(URL, json={"path": "notes.md", "version": "x", "edits": []})

    assert [r.status_code for r in (missing, no_marker, not_markdown, outside)] == [404] * 4
    assert unmarked.status_code == 404
    assert broken.status_code == 422 and "utf" not in broken.json()["error"].lower()
    assert bad.status_code == 400 and "Block 1 changed" in bad.json()["error"]
    assert (workspace / "plan.md").read_text(encoding="utf-8") == CONTENT


def test_a_change_made_behind_the_editor_can_be_undone_and_done_again_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        first = client.get(URL, params={"path": "plan.md"}).json()
        (workspace / "plan.md").write_text(CONTENT + "\nAdded by coscribe.\n", encoding="utf-8")
        second = client.get(URL, params={"path": "plan.md"}).json()
        restore = "/api/threads/t_one/doc/restore"
        undone = client.post(
            restore,
            json={"path": "plan.md", "version": second["version"], "to": first["version"]},
        )
        redone = client.post(
            restore,
            json={"path": "plan.md", "version": first["version"], "to": second["version"]},
        )
        stale = client.post(
            restore,
            json={"path": "plan.md", "version": first["version"], "to": second["version"]},
        )
        gone = client.post(
            restore,
            json={"path": "plan.md", "version": second["version"], "to": "deadbeef"},
        )

    assert undone.status_code == 200 and undone.json()["version"] == first["version"]
    assert redone.status_code == 200 and redone.json()["version"] == second["version"]
    assert "Added by coscribe." in (workspace / "plan.md").read_text(encoding="utf-8")
    assert stale.status_code == 409
    assert gone.status_code == 404
