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


def test_a_comment_is_added_answered_resolved_and_deleted_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _workspace(tmp_path)
    base = "/api/threads/t_one/doc/comments"
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        made = client.post(
            base, json={"path": "plan.md", "block": 1, "text": "Is this right?", "sent": True}
        ).json()
        answered = client.post(
            f"{base}/{made['id']}/replies",
            json={"path": "plan.md", "text": "Yes, checked.", "from_coscribe": True},
        )
        mine = client.post(
            f"{base}/{made['id']}/replies", json={"path": "plan.md", "text": "Thanks."}
        )
        resolved = client.post(f"{base}/{made['id']}", json={"path": "plan.md", "resolved": True})
        listed = client.get(base, params={"path": "plan.md"}).json()
        deleted = client.delete(f"{base}/{made['id']}", params={"path": "plan.md"})
        after = client.get(base, params={"path": "plan.md"}).json()

    assert made["anchor"]["text"] == "First paragraph." and made["sent"] is True
    assert answered.status_code == 200 and answered.json()["author"] == "coscribe"
    assert mine.status_code == 200 and mine.json()["author"] != "coscribe"
    assert resolved.json() == {"resolved": True, "sent": None}
    assert listed[0]["resolved"] is True and listed[0]["block"] == 1
    assert [r["text"] for r in listed[0]["replies"]] == ["Yes, checked.", "Thanks."]
    assert deleted.json() == {"deleted": made["id"]} and after == []


def test_a_picture_is_added_and_read_back_and_only_pictures_of_the_doc_are_served_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    from PIL import Image

    workspace = _workspace(tmp_path)
    (workspace / "secret.png").write_bytes(b"secret")
    picture = io.BytesIO()
    Image.new("RGB", (2, 2), "blue").save(picture, "PNG")
    base = "/api/threads/t_one/doc/asset"
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        added = client.post(
            base, data={"path": "plan.md"}, files={"file": ("dot.png", picture.getvalue())}
        )
        src = added.json()["src"]
        got = client.get(base, params={"path": "plan.md", "src": src})
        outside = client.get(base, params={"path": "plan.md", "src": "../secret.png"})
        bad = client.post(
            base, data={"path": "plan.md"}, files={"file": ("dot.png", b"not a picture")}
        )
        no_doc = client.post(
            base, data={"path": "nope.md"}, files={"file": ("dot.png", picture.getvalue())}
        )

    assert added.status_code == 200 and src == "plan.doc/assets/dot.png"
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert outside.status_code == 404
    assert bad.status_code == 400 and bad.json()["error"] == "That file is not a picture"
    assert no_doc.status_code == 404


def test_a_comment_keeps_its_quote_and_can_be_edited_and_sent_later_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _workspace(tmp_path)
    base = "/api/threads/t_one/doc/comments"
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        made = client.post(
            base, json={"path": "plan.md", "block": 1, "text": "Why?", "quote": "First"}
        ).json()
        edited = client.put(f"{base}/{made['id']}", json={"path": "plan.md", "text": "Why so?"})
        sent = client.post(f"{base}/{made['id']}", json={"path": "plan.md", "sent": True})
        blank = client.put(f"{base}/{made['id']}", json={"path": "plan.md", "text": " "})
        missing = client.put(f"{base}/nope", json={"path": "plan.md", "text": "x"})
        listed = client.get(base, params={"path": "plan.md"}).json()

    assert edited.json() == {"text": "Why so?"} and sent.status_code == 200
    assert blank.status_code == 400 and missing.status_code == 404
    assert (listed[0]["quote"], listed[0]["text"]) == ("First", "Why so?")
    assert (listed[0]["sent"], listed[0]["resolved"]) == (True, False)


def test_what_cannot_be_commented_on_is_refused_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "notes.md").write_text("# Just notes\n", encoding="utf-8")
    (workspace / "broken.md").write_bytes(b"\xff\xfe\x00 not text")
    base = "/api/threads/t_one/doc/comments"
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        no_file = client.get(base, params={"path": "nope.md"})
        no_marker = client.post(base, json={"path": "notes.md", "block": 0, "text": "x"})
        outside = client.get(base, params={"path": "../secret.md"})
        bad_block = client.post(base, json={"path": "plan.md", "block": 40, "text": "x"})
        broken = client.get(base, params={"path": "broken.md"})
        broken_add = client.post(base, json={"path": "broken.md", "block": 0, "text": "x"})
        empty = client.post(base, json={"path": "plan.md", "block": 0, "text": ""})
        unknown = client.post(f"{base}/nope", json={"path": "plan.md", "resolved": True})
        unknown_reply = client.post(f"{base}/nope/replies", json={"path": "plan.md", "text": "x"})
        unknown_delete = client.delete(f"{base}/nope", params={"path": "plan.md"})

    assert [r.status_code for r in (no_file, no_marker, outside)] == [404, 404, 404]
    assert bad_block.status_code == 400 and bad_block.json()["error"] == "There is no such block"
    # What a parser says about a file that is not text is not shown.
    assert [r.status_code for r in (broken, broken_add)] == [422, 422]
    assert all("utf" not in r.text.lower() for r in (broken, broken_add))
    assert empty.status_code == 422
    assert [r.status_code for r in (unknown, unknown_reply, unknown_delete)] == [404] * 3
