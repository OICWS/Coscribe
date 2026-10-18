# ruff: noqa: E402
"""Web tests: the activity panel, opening files and the Word review routes."""

import io
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from docx import Document
from langchain_core.messages import (
    AIMessage,
)
from PIL import Image

from coscribe.tools.office.document_tools import DocumentToolkit
from coscribe.web.routes import threads as threads_routes

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _run_turn,
    _stub_script_env,
    _tool_call,
    _wait_for_run_status,
)


def test_thread_activity_lists_outputs_references_tools_and_progress_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_script_env(monkeypatch)
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "input.txt").write_text("data", encoding="utf-8")
    script = "open('chart.png', 'w').write('png')"
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "task_create", {"content": "Read the input"}),
                    _tool_call("c2", "read_file", {"path": "input.txt"}),
                    _tool_call("c3", "list_files", {"path": "."}),
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c4", "write_file", {"path": "report.md", "content": "# R"}),
                    _tool_call("c5", "write_file", {"path": "../outside.md", "content": "x"}),
                ],
            ),
            # Its own turn: a script's files_written is a before/after
            # snapshot of the workspace, so a write running alongside it
            # would be counted as the script's too.
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c6", "run_python_script", {"script": script, "description": "d"}),
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_activity", "make a report")
        activity = client.get("/api/threads/t_activity/activity").json()

    assert [t["content"] for t in activity["tasks"]] == ["Read the input"]
    # Newest first; the write outside the workspace failed, so it isn't one.
    assert [o["path"] for o in activity["outputs"]] == ["chart.png", "report.md"]
    assert all(o["exists"] and o["openable"] for o in activity["outputs"])
    assert [r["path"] for r in activity["references"]] == ["input.txt"]
    assert {t["name"]: t["count"] for t in activity["tools"]} == {
        "read_file": 1,
        "list_files": 1,
        "write_file": 1,
        "run_python_script": 1,
    }
    assert activity["connectors"] == [] and activity["skills"] == []


def test_thread_activity_marks_files_created_edited_and_read_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("keep", encoding="utf-8")
    (workspace / "plan.md").write_text("old line", encoding="utf-8")
    (workspace / "draft.md").write_text("old", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "read_file", {"path": "notes.txt"}),
                    _tool_call("c2", "read_file", {"path": "plan.md"}),
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call(
                        "c3", "edit_file", {"path": "plan.md", "old_text": "old", "new_text": "new"}
                    ),
                    _tool_call("c4", "write_file", {"path": "draft.md", "content": "replaced"}),
                    _tool_call("c5", "write_file", {"path": "summary.md", "content": "# S"}),
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c6", "write_file", {"path": "summary.md", "content": "# S2"})
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_activity_actions", "tidy up")
        activity = client.get("/api/threads/t_activity_actions/activity").json()

    # summary.md was made here, so it stays "created" after being rewritten;
    # draft.md existed (its old line was removed) and plan.md was read first.
    assert {o["path"]: o["action"] for o in activity["outputs"]} == {
        "summary.md": "created",
        "draft.md": "edited",
        "plan.md": "edited",
    }
    assert [(r["path"], r["action"]) for r in activity["references"]] == [("notes.txt", "read")]


def test_thread_activity_leaves_scratch_folders_out_of_the_outputs_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that checks its work leaves renders and test files behind;
    those aren't what the person asked for."""
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "write_file", {"path": "report.md", "content": "# R"}),
                    _tool_call("c2", "write_file", {"path": "qa/page-1.md", "content": "x"}),
                    _tool_call("c3", "write_file", {"path": ".cache/x.md", "content": "x"}),
                    _tool_call("c4", "write_file", {"path": "out/qa.md", "content": "x"}),
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_activity_scratch", "write")
        activity = client.get("/api/threads/t_activity_scratch/activity").json()

    assert sorted(o["path"] for o in activity["outputs"]) == ["out/qa.md", "report.md"]


def test_thread_activity_leaves_out_files_the_assistant_made_and_removed_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call("c1", "write_file", {"path": "report.md", "content": "# R"}),
                    _tool_call("c2", "write_file", {"path": "check.png", "content": "x"}),
                ],
            ),
            AIMessage(
                content="", tool_calls=[_tool_call("c3", "delete_file", {"path": "check.png"})]
            ),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        _run_turn(client, "t_activity_removed", "write")
        activity = client.get("/api/threads/t_activity_removed/activity").json()

    assert [o["path"] for o in activity["outputs"]] == ["report.md"]


def test_opening_a_thread_file_only_hands_documents_to_the_os_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        threads_routes,
        "open_in_os",
        lambda path, *, reveal: opened.append((path.name, reveal)),
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "report.xlsx").write_bytes(b"x")
    (workspace / "run.bat").write_text("echo hi", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("s", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        url = "/api/threads/t_files/files/open"
        doc = client.post(url, json={"path": "report.xlsx"})
        script = client.post(url, json={"path": "run.bat"})
        revealed = client.post(url, json={"path": "run.bat", "reveal": True})
        outside = client.post(url, json={"path": "../secret.txt"})
        download = client.get("/api/threads/t_files/files/download", params={"path": "report.xlsx"})
        missing = client.get("/api/threads/t_files/files/download", params={"path": "nope.xlsx"})

    assert doc.status_code == 200 and script.status_code == 400
    assert revealed.status_code == 200 and outside.status_code == 404
    assert opened == [("report.xlsx", False), ("run.bat", True)]
    assert download.status_code == 200 and download.content == b"x"
    assert "report.xlsx" in download.headers["content-disposition"]
    assert missing.status_code == 404


def test_the_word_review_routes_read_act_on_and_show_the_original_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(threads_routes.getpass, "getuser", lambda: "ana")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    toolkit = DocumentToolkit(workspace)
    toolkit.write_docx(path="c.docx", content="Pay 100 dollars. {{comment: Final?}}")
    toolkit.replace_docx_text(path="c.docx", find="100", replace="120")
    (workspace / "notes.txt").write_text("x", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        url = "/api/threads/t_review/docx-review"
        review = client.get(url, params={"path": "c.docx"}).json()
        comment = review["comments"][0]["id"]
        original = client.get(f"{url}/original", params={"path": "c.docx"})
        edited = client.post(
            url,
            json={
                "path": "c.docx",
                "operations": [
                    {"op": "accept", "change": review["changes"][0]["id"]},
                    {"op": "reply", "comment": comment, "text": "Yes"},
                ],
            },
        )
        failed = client.post(url, json={"path": "c.docx", "operations": [{"op": "nope"}]})
        after = client.get(url, params={"path": "c.docx"}).json()
        not_word = client.get(url, params={"path": "notes.txt"})
        missing = client.get(url, params={"path": "nope.docx"})

    assert [c["kind"] for c in review["changes"]] == ["delete", "insert"]
    assert edited.status_code == 200 and edited.json()["changes_left"] == 1
    assert failed.status_code == 400 and "unknown op" in failed.json()["error"]
    assert [c["kind"] for c in after["changes"]] == ["insert"]
    assert after["comments"][0]["replies"][0]["author"] == "ana"
    (tmp_path / "o.docx").write_bytes(original.content)
    assert Document(tmp_path / "o.docx").paragraphs[0].text == "Pay 100 dollars."
    assert not_word.status_code == 400 and missing.status_code == 404


def test_the_slides_routes_read_a_built_deck_and_draw_its_slides_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.office.pptx.engine import build_deck

    from ..test_deck_engine import COVER

    pages = tmp_path / "workspace" / "q3"
    pages.mkdir(parents=True)
    (pages / "01.svg").write_text(COVER, encoding="utf-8")
    assert build_deck(pages, pages.parent / "q3.pptx").ok
    (pages.parent / "notes.txt").write_text("x", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        url = "/api/threads/t_slides/slides"
        deck = client.get(url, params={"path": "q3.pptx"})
        svg = client.get(f"{url}/0/svg", params={"path": "q3.pptx"})
        past_end = client.get(f"{url}/1/svg", params={"path": "q3.pptx"})
        page = client.get(f"{url}/export", params={"path": "q3.pptx", "format": "html"})
        basic = client.get(f"{url}/export", params={"path": "q3.pptx", "format": "pptx-basic"})
        unknown = client.get(f"{url}/export", params={"path": "q3.pptx", "format": "key"})
        not_a_deck = client.get(url, params={"path": "notes.txt"})
        outside = client.get(url, params={"path": "../q3.pptx"})
        (pages / "01.svg").write_text("<svg", encoding="utf-8")
        broken = client.get(f"{url}/0/svg", params={"path": "q3.pptx"})

    assert deck.status_code == 200 and [s["name"] for s in deck.json()["slides"]] == ["01.svg"]
    assert svg.headers["content-type"] == "image/svg+xml"
    assert "default-src 'none'" in svg.headers["content-security-policy"]
    assert svg.text.startswith("<svg")
    assert past_end.status_code == 404
    assert page.status_code == 200 and page.text.count("data:image/svg+xml") == 1
    assert "attachment; filename*=UTF-8''q3.html" == page.headers["content-disposition"]
    assert basic.status_code == 200 and basic.content[:2] == b"PK"
    assert unknown.status_code == 400
    assert not_a_deck.status_code == 404 and outside.status_code == 404
    # The parser's own message (with the page's path) stays on the server.
    assert broken.status_code == 400 and "01.svg" not in broken.text


def test_the_slides_edit_routes_read_parts_and_save_a_section_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.office.pptx.engine import build_deck

    from ..test_deck_engine import COVER

    pages = tmp_path / "workspace" / "q3"
    pages.mkdir(parents=True)
    (pages / "01.svg").write_text(COVER, encoding="utf-8")
    assert build_deck(pages, pages.parent / "q3.pptx").ok
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        url = "/api/threads/t_edit/slides/0"
        parts = client.get(f"{url}/parts", params={"path": "q3.pptx"}).json()
        body = {"path": "q3.pptx", "source": parts["source"], "version": parts["version"]}
        saved = client.put(f"{url}/source", json=body)
        stale = client.put(f"{url}/source", json=body)
        fresh = {**body, "version": saved.json()["version"]}
        refused = client.put(f"{url}/source", json={**fresh, "source": "<section><b/></section>"})
        past_end = client.put("/api/threads/t_edit/slides/3/source", json=fresh)
        png = io.BytesIO()
        Image.new("RGB", (8, 4)).save(png, "PNG")
        assets = "/api/threads/t_edit/slides/assets"
        picture = client.post(
            assets, data={"path": "q3.pptx"}, files={"file": ("a.png", png.getvalue())}
        )
        not_one = client.post(assets, data={"path": "q3.pptx"}, files={"file": ("a.png", b"hi")})
        arrange = "/api/threads/t_edit/slides/arrange"
        copied = client.post(arrange, json={"path": "q3.pptx", "action": "duplicate", "index": 0})
        last = client.post(arrange, json={"path": "q3.pptx", "action": "delete", "index": 1})
        only = client.post(arrange, json={"path": "q3.pptx", "action": "delete", "index": 0})

    assert parts["kind"] == "page" and parts["parts"]
    assert saved.status_code == 200 and saved.json()["name"] == "01.html"
    # Renumbered by the copy and the delete below.
    assert (pages / "01-slide.html").is_file() and not (pages / "01.svg").exists()
    assert stale.status_code == 409 and stale.json()["changed"] == "slide"
    assert refused.status_code == 400 and "<b" not in refused.text
    assert past_end.status_code == 404
    assert picture.json() == {"src": "assets/a.png", "width": 8, "height": 4}
    assert not_one.status_code == 400
    assert copied.json() == {"index": 1} and last.json() == {"index": 0}
    assert only.status_code == 400


def test_the_slides_comment_routes_add_reply_resolve_and_delete_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools.office.pptx.engine import build_deck
    from coscribe.web.routes import slides as slides_routes

    from ..test_deck_engine import COVER

    monkeypatch.setattr(slides_routes.getpass, "getuser", lambda: "ana")
    pages = tmp_path / "workspace" / "q3"
    pages.mkdir(parents=True)
    (pages / "01.svg").write_text(COVER, encoding="utf-8")
    assert build_deck(pages, pages.parent / "q3.pptx").ok
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        url = "/api/threads/t_comments/slides/comments"
        new = {"path": "q3.pptx", "slide": "01", "x": 0.2, "y": 0.3, "element": "Title"}
        made = client.post(url, json={**new, "text": "Shorter title?", "sent": True}).json()
        empty = client.post(url, json={**new, "text": ""})
        reply = client.post(
            f"{url}/{made['id']}/replies",
            json={"path": "q3.pptx", "text": "Done.", "from_coscribe": True},
        )
        resolved = client.post(f"{url}/{made['id']}", json={"path": "q3.pptx", "resolved": True})
        listed = client.get(url, params={"path": "q3.pptx"}).json()
        deleted = client.delete(f"{url}/{made['id']}", params={"path": "q3.pptx"})
        gone = client.post(f"{url}/{made['id']}", json={"path": "q3.pptx", "resolved": False})
        after = client.get(url, params={"path": "q3.pptx"}).json()

    assert made["author"] == "ana" and made["sent"] is True
    assert empty.status_code == 422
    assert reply.json()["author"] == "coscribe" and resolved.json() == {"resolved": True}
    assert listed[0]["resolved"] and listed[0]["replies"][0]["text"] == "Done."
    assert deleted.status_code == 200 and gone.status_code == 404 and after == []


def test_a_saved_run_waits_for_a_folder_it_hasnt_been_allowed_then_carries_on_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    workflow = {
        "inputs": [{"name": "dest"}],
        "steps": [
            {"id": "save", "kind": "tool", "title": "Save the report", "tool": "write_file",
             "args": {"path": "{{dest}}", "content": "report"}},
        ],
    }  # fmt: skip
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        created = client.post(
            "/api/scheduled-tasks",
            json={"name": "Report", "kind": "manual", "at": "", "workflow": workflow},
        )
        task = created.json()
        target = str(elsewhere / "out.txt")
        started = client.post(
            f"/api/scheduled-tasks/{task['trigger_id']}/run", json={"inputs": {"dest": target}}
        )
        run = started.json()["run"]
        parked = _wait_for_run_status(client, task["trigger_id"], run["run_id"])
        declined_early = (elsewhere / "out.txt").exists()

        answered = client.post(
            f"/api/scheduled-tasks/{task['trigger_id']}/runs/{run['run_id']}/answer",
            json={"approved": True},
        )
        finished = _wait_for_run_status(client, task["trigger_id"], run["run_id"])
        saved = client.get("/api/scheduled-tasks").json()
        permissions = client.post(
            "/api/workflows/permissions",
            json={"workflow": workflow, "trigger_id": task["trigger_id"]},
        ).json()

    waiting = parked["steps"][-1]
    assert parked["status"] == "needs_approval"
    assert waiting["status"] == "waiting"
    assert waiting["permission"]["kind"] == "folder"
    assert waiting["permission"]["target"] == str(elsewhere)
    assert not declined_early
    assert answered.status_code == 200
    assert finished["status"] == "completed", finished
    assert (elsewhere / "out.txt").read_text(encoding="utf-8") == "report"
    granted = next(t for t in saved if t["trigger_id"] == task["trigger_id"])
    assert granted["permissions"] == {"folders": [str(elsewhere)]}
    assert permissions["permissions"]["folders"] == [str(elsewhere)]
