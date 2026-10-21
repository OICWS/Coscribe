# ruff: noqa: E402
"""Web tests: the Artifacts page's list."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.web.routes import artifacts as artifact_routes

from .helpers import FakeToolCallingChatModel, _client_lg, _run_turn, _tool_call


def _made(*paths: str) -> AIMessage:
    calls = [
        _tool_call(f"c{i}", "write_file", {"path": p, "content": "x"}) for i, p in enumerate(paths)
    ]
    return AIMessage(content="", tool_calls=calls)


def test_the_artifacts_route_lists_what_the_conversations_created_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[
            # A lock file Word leaves and a plain note are not artifacts.
            _made("deck.pptx", "report.docx", "numbers.xlsx", "notes.md", "~$report.docx"),
            AIMessage(content="done"),
            _made("later.docx"),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        assert client.get("/api/artifacts").json() == []  # no conversation has run
        _run_turn(client, "t_one", "make things")
        first = client.get("/api/artifacts").json()
        _run_turn(client, "t_two", "one more")
        (tmp_path / "workspace" / "deck.pptx").unlink()
        second = client.get("/api/artifacts").json()

    assert {a["name"]: a["kind"] for a in first} == {
        "deck": "slides",
        "report": "docs",
        "numbers": "sheets",
    }
    assert all(a["id"] and a["modified_at"] and a["path"].startswith(a["name"]) for a in first)
    # The new conversation's file is listed, and the deck taken from the disk is not.
    assert {a["name"] for a in second} == {"report", "numbers", "later"}


def test_a_file_a_conversation_only_edited_is_not_an_artifact_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "theirs.docx").write_bytes(b"x")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "replace_docx_text", {"path": "theirs.docx", "old": "a"})
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "fix their file")
        assert client.get("/api/artifacts").json() == []


def test_an_artifact_outlives_its_conversation_and_opens_in_a_new_one_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[_made("report.docx", "deck.pptx"), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "make things")
        listed = {a["name"]: a["id"] for a in client.get("/api/artifacts").json()}
        alive = client.post(f"/api/artifacts/{listed['report']}/open").json()
        assert client.delete("/api/threads/t_one").status_code == 200
        gone = client.post(f"/api/artifacts/{listed['report']}/open").json()
        after = client.get("/api/artifacts").json()
        unknown = client.post("/api/artifacts/nope/open")
        no_thumb = client.get(f"/api/artifacts/{listed['report']}/thumbnail")

    assert alive == {"thread_id": "t_one", "path": "report.docx"}
    assert gone["thread_id"] not in ("t_one", "") and gone["path"] == "report.docx"
    assert {a["name"] for a in after} == {"report", "deck"}
    assert unknown.status_code == 404
    assert no_thumb.status_code == 404


def test_the_menu_renames_copies_and_deletes_an_artifact_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    sent: list[str] = []
    monkeypatch.setattr("send2trash.send2trash", lambda path: (sent.append(path), None)[1])
    fake_model = FakeToolCallingChatModel(
        responses=[_made("report.docx", "plan.docx"), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "make things")
        ids = {a["name"]: a["id"] for a in client.get("/api/artifacts").json()}
        renamed = client.post(f"/api/artifacts/{ids['report']}/rename", json={"name": "Q3 report"})
        taken = client.post(f"/api/artifacts/{ids['report']}/rename", json={"name": "plan"})
        copied = client.post(f"/api/artifacts/{ids['report']}/duplicate")
        found = client.get(
            "/api/artifacts/lookup", params={"thread_id": "t_one", "path": "Q3 report.docx"}
        )
        other = client.get(
            "/api/artifacts/lookup", params={"thread_id": "t_one", "path": "nothing.docx"}
        )
        deleted = client.delete(f"/api/artifacts/{ids['plan']}")
        names = {a["name"] for a in client.get("/api/artifacts").json()}
        missing = client.delete("/api/artifacts/nope")

    assert renamed.json()["name"] == "Q3 report" and renamed.json()["id"] == ids["report"]
    assert (tmp_path / "workspace" / "Q3 report.docx").is_file()
    assert found.json()["id"] == ids["report"] and other.status_code == 404
    assert taken.status_code == 409
    assert copied.json()["name"] == "Q3 report copy"
    assert deleted.status_code == 200 and sent == [str(tmp_path / "workspace" / "plan.docx")]
    assert names == {"Q3 report", "Q3 report copy"}
    assert missing.status_code == 404


def test_a_system_error_is_not_shown_to_the_page_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()

    def locked(*_: object) -> None:
        raise PermissionError(13, "denied", str(tmp_path / "workspace" / "report.docx"))

    monkeypatch.setattr(artifact_routes, "rename_file", locked)
    fake_model = FakeToolCallingChatModel(responses=[_made("report.docx"), AIMessage(content="d")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "make")
        artifact = client.get("/api/artifacts").json()[0]["id"]
        refused = client.post(f"/api/artifacts/{artifact}/rename", json={"name": "x"})

    assert refused.status_code == 409
    assert "report.docx" not in refused.json()["error"] and "denied" not in refused.json()["error"]
