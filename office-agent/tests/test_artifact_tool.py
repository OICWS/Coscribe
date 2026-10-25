from __future__ import annotations

from pathlib import Path
from typing import Any

from coscribe.conversation.artifact_tools import build_artifact_tools
from coscribe.conversation.artifacts import ArtifactRegistry
from coscribe.tools import WorkspaceScope


def _tool(state: Path, scope: WorkspaceScope) -> Any:
    return build_artifact_tools(state, lambda: scope)[0]


def _made(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Two conversations' folders, each with a deck, and the registry that knows both."""
    here, there = tmp_path / "here", tmp_path / "there"
    for folder in (here, there):
        folder.mkdir()
    (here / "Q3 deck.pptx").write_bytes(b"x")
    (there / "budget.xlsx").write_bytes(b"x")
    registry = ArtifactRegistry(tmp_path / "state")
    registry.adopt([str(here / "Q3 deck.pptx")], [str(here)], "t1")
    registry.adopt([str(there / "budget.xlsx")], [str(there)], "t2")
    return here, there, tmp_path / "state"


def test_it_lists_every_artifact_and_says_which_this_conversation_can_read(tmp_path: Path) -> None:
    here, there, state = _made(tmp_path)
    listed = {a["name"]: a for a in _tool(state, WorkspaceScope(here))()}

    assert listed["Q3 deck"]["readable"] is True and listed["Q3 deck"]["path"] == "Q3 deck.pptx"
    assert listed["budget"]["readable"] is False
    assert listed["budget"]["path"] == str(there / "budget.xlsx")


def test_it_filters_by_kind_and_by_a_part_of_the_name(tmp_path: Path) -> None:
    here, _, state = _made(tmp_path)
    tool = _tool(state, WorkspaceScope(here))

    assert [a["name"] for a in tool(kind="sheets")] == ["budget"]
    assert [a["name"] for a in tool(query="q3")] == ["Q3 deck"]
    assert tool(query="nothing like it") == []


def test_a_file_that_is_gone_is_not_listed_and_the_limit_is_kept(tmp_path: Path) -> None:
    here, there, state = _made(tmp_path)
    (there / "budget.xlsx").unlink()
    tool = _tool(state, WorkspaceScope(here))

    assert [a["name"] for a in tool()] == ["Q3 deck"]
    assert len(tool(limit=0)) == 1
