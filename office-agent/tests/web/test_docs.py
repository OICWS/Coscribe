# ruff: noqa: E402
"""Web tests: the Docs editor's routes (decision 0019)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.tools.office.document_tools import build_document_tools

from .helpers import FakeToolCallingChatModel, _client_lg

CONTENT = "# Plan\n\nFirst paragraph.\n\n- one\n- two\n"


def _write(root: Path, name: str = "plan.docx") -> None:
    tools = {t.__name__: t for t in build_document_tools(root)}  # type: ignore[attr-defined]
    tools["write_docx"](path=name, content=CONTENT)


def test_the_blocks_are_read_and_the_changed_one_is_saved_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    _write(tmp_path / "workspace")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        read = client.get("/api/threads/t_one/docs/blocks", params={"path": "plan.docx"}).json()
        blocks = read["blocks"]
        assert [b["kind"] for b in blocks] == ["title", "paragraph", "bullet", "bullet"]
        blocks[1]["runs"] = [{"t": "Changed ", "b": True}, {"t": "text"}]
        saved = client.put(
            "/api/threads/t_one/docs/blocks",
            json={"path": "plan.docx", "version": read["version"], "blocks": blocks},
        )
        stale = client.put(
            "/api/threads/t_one/docs/blocks",
            json={"path": "plan.docx", "version": read["version"], "blocks": blocks},
        )

    assert saved.status_code == 200
    assert saved.json()["blocks"][1]["runs"] == [{"t": "Changed ", "b": True}, {"t": "text"}]
    assert saved.json()["version"] != read["version"]
    assert stale.status_code == 409 and stale.json()["changed"] is True


def test_what_is_not_a_word_document_or_cannot_be_saved_is_refused_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(workspace)
    (workspace / "notes.txt").write_text("x")
    (workspace / "broken.docx").write_bytes(b"not a zip")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        url = "/api/threads/t_one/docs/blocks"
        missing = client.get(url, params={"path": "nope.docx"})
        text = client.get(url, params={"path": "notes.txt"})
        broken = client.get(url, params={"path": "broken.docx"})
        outside = client.get(url, params={"path": "../secret.docx"})
        read = client.get(url, params={"path": "plan.docx"}).json()
        bad = client.put(
            url,
            json={
                "path": "plan.docx",
                "version": read["version"],
                "blocks": [{"kind": "paragraph", "runs": [{"t": "x", "link": "javascript:1"}]}],
            },
        )

    assert [missing.status_code, text.status_code, outside.status_code] == [404, 404, 404]
    assert broken.status_code == 422 and "zip" not in broken.json()["error"].lower()
    assert bad.status_code == 400 and "http" in bad.json()["error"]
