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
            # A lock file PowerPoint leaves, a plain note, and a Word and an Excel file are not
            # artifacts.
            _made("deck.pptx", "report.docx", "numbers.xlsx", "notes.md", "~$deck2.pptx"),
            AIMessage(content="done"),
            _made("later.pptx"),
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

    assert {a["name"]: a["kind"] for a in first} == {"deck": "slides"}
    assert all(a["id"] and a["modified_at"] and a["path"].startswith(a["name"]) for a in first)
    # The new conversation's file is listed, and the deck taken from the disk is not.
    assert {a["name"] for a in second} == {"later"}


def test_a_file_a_conversation_only_edited_is_not_an_artifact_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "theirs.pptx").write_bytes(b"x")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "replace_pptx_text", {"path": "theirs.pptx", "old": "a"})
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
        responses=[_made("report.html", "deck.pptx"), AIMessage(content="done")]
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

    assert alive == {"thread_id": "t_one", "path": "report.html"}
    assert gone["thread_id"] not in ("t_one", "") and gone["path"] == "report.html"
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
        responses=[_made("report.pptx", "plan.pptx"), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "make things")
        ids = {a["name"]: a["id"] for a in client.get("/api/artifacts").json()}
        renamed = client.post(f"/api/artifacts/{ids['report']}/rename", json={"name": "Q3 report"})
        taken = client.post(f"/api/artifacts/{ids['report']}/rename", json={"name": "plan"})
        copied = client.post(f"/api/artifacts/{ids['report']}/duplicate")
        found = client.get(
            "/api/artifacts/lookup", params={"thread_id": "t_one", "path": "Q3 report.pptx"}
        )
        other = client.get(
            "/api/artifacts/lookup", params={"thread_id": "t_one", "path": "nothing.pptx"}
        )
        deleted = client.delete(f"/api/artifacts/{ids['plan']}")
        names = {a["name"] for a in client.get("/api/artifacts").json()}
        missing = client.delete("/api/artifacts/nope")

    assert renamed.json()["name"] == "Q3 report" and renamed.json()["id"] == ids["report"]
    assert (tmp_path / "workspace" / "Q3 report.pptx").is_file()
    assert found.json()["id"] == ids["report"] and other.status_code == 404
    assert taken.status_code == 409
    assert copied.json()["name"] == "Q3 report copy"
    assert deleted.status_code == 200 and sent == [str(tmp_path / "workspace" / "plan.pptx")]
    assert names == {"Q3 report", "Q3 report copy"}
    assert missing.status_code == 404


def test_a_system_error_is_not_shown_to_the_page_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()

    def locked(*_: object) -> None:
        raise PermissionError(13, "denied", str(tmp_path / "workspace" / "report.pptx"))

    monkeypatch.setattr(artifact_routes, "rename_file", locked)
    fake_model = FakeToolCallingChatModel(responses=[_made("report.pptx"), AIMessage(content="d")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_one", "make")
        artifact = client.get("/api/artifacts").json()[0]["id"]
        refused = client.post(f"/api/artifacts/{artifact}/rename", json={"name": "x"})

    assert refused.status_code == 409
    assert "report.pptx" not in refused.json()["error"] and "denied" not in refused.json()["error"]


def test_an_html_design_is_an_artifact_and_a_lone_svg_is_not_and_it_is_served_inside_a_sandbox_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[_made("icons.html", "mark.svg", "page.htm"), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_design", "design icons")
        items = {a["name"]: a for a in client.get("/api/artifacts").json()}
        assert {n: items[n]["kind"] for n in items} == {"icons": "design"}
        page = client.get(f"/api/artifacts/{items['icons']['id']}/content")
        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert page.headers["content-security-policy"].startswith("sandbox allow-scripts;")
        assert "default-src 'none'" in page.headers["content-security-policy"]
        by_path = client.get("/api/threads/t_design/design", params={"path": "icons.html"})
        assert by_path.status_code == 200
        outside = client.get("/api/threads/t_design/design", params={"path": "../x.html"})
        assert outside.status_code == 404


def test_a_page_marked_as_a_dashboard_is_one_and_is_served_with_its_data_and_d3_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "sales.dashboard" / "data").mkdir(parents=True)
    (workspace / "sales.dashboard" / "datasets.json").write_text(
        '{"datasets": {"q3": {"source": "q3.csv"}}, "figures": {}}', encoding="utf-8"
    )
    (workspace / "sales.dashboard" / "data" / "q3.json").write_text(
        '[{"region": "East", "sales": 515}]', encoding="utf-8"
    )
    page = (
        '<html><head><meta name="coscribe" content="dashboard">'
        '<script data-coscribe-lib="d3"></script></head><body></body></html>'
    )
    write = _tool_call("c0", "write_file", {"path": "sales.html", "content": page})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[write]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_dash", "make a dashboard")
        (item,) = client.get("/api/artifacts").json()
        assert (item["name"], item["kind"]) == ("sales", "dashboard")
        served = client.get(f"/api/artifacts/{item['id']}/content")
        assert served.headers["content-security-policy"].startswith("sandbox allow-scripts;")
        body = served.text
        assert '"region": "East"' in body and "d3js.org v7.9.0" in body
        assert "data-coscribe-lib" not in body
