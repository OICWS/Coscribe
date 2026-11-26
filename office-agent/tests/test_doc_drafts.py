"""Drafts follow streamed file arguments and never write the workspace."""

import asyncio
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessageChunk

from coscribe.conversation import doc_drafts
from coscribe.tools import WorkspaceScope


class Events:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send_json(self, value: Any) -> None:
        self.sent.append(value)


def _chunk(args: str) -> AIMessageChunk:
    return AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"id": "call", "index": 0, "name": "use_tool", "args": args},
        ],
    )


def test_doc_draft_streams_partial_writes_and_rolls_back_without_writing(tmp_path: Path) -> None:
    async def run() -> None:
        sink = Events()
        drafts = doc_drafts.DocDrafts(sink)
        scope = WorkspaceScope(tmp_path)
        prefix = (
            '{"name":"write_file","arguments":{"path":"report.md",'
            r'"content":"---\ncoscribe: doc\n---\n\n'
        )
        await drafts.update(_chunk(prefix + "# Hello"), lambda: scope)
        preview_id = sink.sent[-1]["id"]
        assert sink.sent[-1] == {
            "type": "doc_draft",
            "id": preview_id,
            "path": "report.md",
            "new": True,
            "blocks": [{"index": 0, "kind": "heading", "text": "# Hello"}],
        }
        await drafts.close()
        assert sink.sent[-1] == {
            "type": "doc_draft_finished",
            "id": preview_id,
            "path": "report.md",
            "committed": False,
        }
        assert not (tmp_path / "report.md").exists()

    asyncio.run(run())


def test_doc_draft_shows_exact_replacement_and_respects_workspace_scope(tmp_path: Path) -> None:
    async def run() -> None:
        file = tmp_path / "report.md"
        original = "---\ncoscribe: doc\n---\n\n# Report\n\nRemove this paragraph.\n\nKeep this.\n"
        file.write_text(original, encoding="utf-8")
        sink = Events()
        drafts = doc_drafts.DocDrafts(sink)
        scope = WorkspaceScope(tmp_path)
        prefix = (
            '{"name":"edit_file","arguments":{"path":"report.md",'
            '"old_text":"Remove this paragraph.","new_text":"'
        )
        await drafts.update(_chunk(prefix + "New"), lambda: scope)
        assert sink.sent[-1]["new"] is False
        assert [block["text"] for block in sink.sent[-1]["blocks"]] == [
            "# Report",
            "New",
            "Keep this.",
        ]
        assert file.read_text(encoding="utf-8") == original
        await drafts.finish("call", committed=True)
        assert sink.sent[-1]["committed"] is True

        denied = doc_drafts.DocDrafts(sink)
        before = len(sink.sent)
        await denied.update(
            _chunk(prefix.replace("report.md", "../report.md") + "Other"), lambda: scope
        )
        assert len(sink.sent) == before

    asyncio.run(run())


def test_doc_draft_sends_the_tail_the_throttle_held_back(tmp_path: Path) -> None:
    async def run() -> None:
        sink = Events()
        drafts = doc_drafts.DocDrafts(sink)
        scope = WorkspaceScope(tmp_path)
        prefix = (
            '{"name":"write_file","arguments":{"path":"report.md",'
            r'"content":"---\ncoscribe: doc\n---\n\n# Hello'
        )
        await drafts.update(_chunk(prefix), lambda: scope)
        whole = _chunk(prefix + r'\n\nLast paragraph."}}')
        await drafts.update(whole, lambda: scope)
        assert len(sink.sent) == 1
        await drafts.update(whole, lambda: scope, force=True)
        assert [block["text"] for block in sink.sent[-1]["blocks"]] == [
            "# Hello",
            "Last paragraph.",
        ]

    asyncio.run(run())


def test_a_failing_draft_does_not_reach_the_turn(tmp_path: Path) -> None:
    def broken() -> WorkspaceScope:
        raise KeyError("thread")

    async def run() -> None:
        sink = Events()
        drafts = doc_drafts.DocDrafts(sink)
        await drafts.update(
            _chunk('{"name":"write_file","arguments":{"path":"report.md","content":"x'), broken
        )
        assert sink.sent == []

    asyncio.run(run())
