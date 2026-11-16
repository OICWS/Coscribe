"""Settings › Capabilities: coscribe's own tools write files and make artifacts only while their
switches are on, and a tool looks the same to the model either way."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from coscribe.conversation.capability_guard import TurnedOff, hold_to_capabilities
from coscribe.runtime import Agent, get_tool_metadata
from coscribe.tools import Capabilities, WorkspaceScope, build_file_tools

DOC = "---\ncoscribe: doc\ntitle: Plan\n---\n\n# Plan\n"
DASHBOARD = '<html><head><meta name="coscribe" content="dashboard"></head><body></body></html>'


def _tools(tmp_path: Path) -> tuple[dict[str, object], Path, Path]:
    workspace, state = tmp_path / "workspace", tmp_path / "state"
    workspace.mkdir()
    plain = Agent(name="a", model="fake:model", tools=build_file_tools(workspace))
    held = hold_to_capabilities(plain, state, lambda: WorkspaceScope(workspace))
    return {tool.__name__: tool for tool in held.tools}, workspace, state


def test_a_held_tool_keeps_the_name_signature_docstring_and_metadata(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plain = build_file_tools(workspace)
    held = hold_to_capabilities(
        Agent(name="a", model="fake:model", tools=plain),
        tmp_path / "state",
        lambda: WorkspaceScope(workspace),
    ).tools
    for before, after in zip(plain, held, strict=True):
        assert after.__name__ == before.__name__
        assert after.__doc__ == before.__doc__
        assert inspect.signature(after) == inspect.signature(before)
        assert get_tool_metadata(after) == get_tool_metadata(before)
        # What the provider is sent and caches: the schema built from the function.
        assert convert_to_openai_tool(StructuredTool.from_function(after)) == (
            convert_to_openai_tool(StructuredTool.from_function(before))
        )


def test_with_both_switches_on_files_and_artifacts_are_written(tmp_path: Path) -> None:
    tools, workspace, _ = _tools(tmp_path)
    tools["write_file"](path="notes.txt", content="x")  # type: ignore[operator]
    tools["write_file"](path="plan.md", content=DOC)  # type: ignore[operator]
    assert (workspace / "notes.txt").read_text() == "x"
    assert (workspace / "plan.md").is_file()


def test_with_files_off_nothing_is_written_changed_or_deleted_and_reading_still_works(
    tmp_path: Path,
) -> None:
    tools, workspace, state = _tools(tmp_path)
    (workspace / "kept.txt").write_text("before", encoding="utf-8")
    Capabilities(state).set("files", False)

    with pytest.raises(TurnedOff, match="Settings › Capabilities"):
        tools["write_file"](path="new.txt", content="x")  # type: ignore[operator]
    with pytest.raises(TurnedOff):
        tools["edit_file"](path="kept.txt", old_text="before", new_text="after")  # type: ignore[operator]
    with pytest.raises(TurnedOff):
        tools["delete_file"](path="kept.txt")  # type: ignore[operator]

    assert not (workspace / "new.txt").exists()
    assert (workspace / "kept.txt").read_text(encoding="utf-8") == "before"
    assert "before" in str(tools["read_file"](path="kept.txt"))  # type: ignore[operator]


def test_a_switch_turned_back_on_applies_to_the_same_tools(tmp_path: Path) -> None:
    tools, workspace, state = _tools(tmp_path)
    Capabilities(state).set("files", False)
    with pytest.raises(TurnedOff):
        tools["write_file"](path="a.txt", content="x")  # type: ignore[operator]
    Capabilities(state).set("files", True)
    tools["write_file"](path="a.txt", content="x")  # type: ignore[operator]
    assert (workspace / "a.txt").is_file()


@pytest.mark.parametrize(
    ("path", "content", "kind"),
    [
        ("plan.md", DOC, "Doc"),
        ("launch.design.json", '{"boards": []}', "design"),
        ("results.html", DASHBOARD, "dashboard"),
    ],
)
def test_with_artifacts_off_a_new_doc_design_or_dashboard_is_not_made(
    tmp_path: Path, path: str, content: str, kind: str
) -> None:
    tools, workspace, state = _tools(tmp_path)
    Capabilities(state).set("artifacts", False)
    with pytest.raises(TurnedOff, match=f"this {kind} was not made"):
        tools["write_file"](path=path, content=content)  # type: ignore[operator]
    assert not (workspace / path).exists()


def test_with_artifacts_off_plain_files_are_written_and_an_existing_artifact_can_change(
    tmp_path: Path,
) -> None:
    tools, workspace, state = _tools(tmp_path)
    tools["write_file"](path="plan.md", content=DOC)  # type: ignore[operator]
    Capabilities(state).set("artifacts", False)

    tools["write_file"](path="notes.md", content="# Notes\n")  # type: ignore[operator]
    tools["write_file"](path="page.html", content="<html><body>hi</body></html>")  # type: ignore[operator]
    tools["write_file"](path="plan.md", content=DOC + "\nMore.\n")  # type: ignore[operator]

    assert (workspace / "notes.md").is_file() and (workspace / "page.html").is_file()
    assert "More." in (workspace / "plan.md").read_text(encoding="utf-8")
