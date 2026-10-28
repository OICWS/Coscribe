"""What the Artifacts page shows of a file: its kind, its time and a document's opening lines."""

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from coscribe.conversation import describe_artifact
from coscribe.conversation.artifacts import artifact_paths
from coscribe.runtime import ToolMetadata
from coscribe.tools import WorkspaceScope

_CATALOG = {
    "read_pptx": ToolMetadata("READ"),
    "edit_pptx": ToolMetadata("WRITE_LOCAL"),
    "write_docx": ToolMetadata("WRITE_LOCAL"),
}


def _calls(*calls: tuple[str, dict[str, Any], Any]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for i, (name, args, result) in enumerate(calls):
        call = {"id": f"c{i}", "name": name, "args": args}
        messages += [
            AIMessage(content="", tool_calls=[call]),
            ToolMessage(
                content=result if isinstance(result, str) else json.dumps(result),
                tool_call_id=f"c{i}",
            ),
        ]
    return messages


def test_a_document_is_described_with_its_opening_lines(tmp_path: Path) -> None:
    (tmp_path / "report.md").write_text(
        "---\ncoscribe: doc\n---\n\n# Quarterly report\n\nRevenue grew in every region.\n\n"
        "Costs held steady.\n",
        encoding="utf-8",
    )
    scope = WorkspaceScope(tmp_path)

    described = describe_artifact(scope, "report.md")

    assert described is not None
    assert (described["name"], described["kind"], described["path"]) == (
        "report",
        "docs",
        "report.md",
    )
    assert described["excerpt"] == {
        "heading": "Quarterly report",
        "text": "Revenue grew in every region. Costs held steady.",
    }


def test_what_is_not_an_artifact_or_not_there_is_not_described(tmp_path: Path) -> None:
    for name in ("notes.md", "~$deck.pptx", "report.docx", "budget.xlsx"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    scope = WorkspaceScope(tmp_path)

    assert describe_artifact(scope, "notes.md") is None
    assert describe_artifact(scope, "~$deck.pptx") is None
    assert describe_artifact(scope, "gone.pptx") is None
    assert describe_artifact(scope, "../outside.md") is None
    # A Word or an Excel file is a file for Word or Excel, not an artifact (decision 0027).
    assert describe_artifact(scope, "report.docx") is None
    assert describe_artifact(scope, "budget.xlsx") is None


def test_a_deck_is_an_artifact_only_when_the_conversation_made_it(tmp_path: Path) -> None:
    for name in ("brought.pptx", "template.pptx", "edited.pptx", "report.docx", "made.pptx"):
        (tmp_path / name).write_bytes(b"x")
    scope = WorkspaceScope(tmp_path)
    script = {"script": "...", "description": "rewrite"}
    messages = _calls(
        ("read_pptx", {"path": "brought.pptx"}, "ok"),
        (
            "run_python_script",
            script,
            {"exit_code": 0, "files_written": ["brought.pptx", "made.pptx"]},
        ),
        ("read_pptx", {"path": "template.pptx"}, "ok"),
        ("read_pptx", {"path": "edited.pptx"}, "ok"),
        ("edit_pptx", {"path": "edited.pptx"}, {"lines_removed": 2}),
        ("read_pptx", {"path": "report.docx"}, "ok"),
        ("write_docx", {"path": "report.docx"}, {"lines_removed": 5}),
    )

    found = artifact_paths(messages, _CATALOG, scope)

    # A deck the person brought is theirs, read, changed in place or replaced whole by a script; a
    # Word file is never an artifact. A deck a script wrote that was not there is coscribe's.
    assert found == ["made.pptx"]


def test_outputs_leave_out_working_files_that_are_gone_and_underscore_scratch_folders(
    tmp_path: Path,
) -> None:
    from coscribe.conversation.activity import summarize_activity

    (tmp_path / "_qa").mkdir()
    for name in ("report.docx", "_qa/preview.pdf", "mine.docx"):
        (tmp_path / name).write_bytes(b"x")
    catalog = {
        **_CATALOG,
        "convert_office_file": ToolMetadata("WRITE_LOCAL"),
        "read_docx": ToolMetadata("READ"),
        "edit_docx": ToolMetadata("WRITE_LOCAL"),
    }
    messages = _calls(
        ("write_docx", {"path": "report.docx"}, {"lines_removed": 0}),
        # A render a conversion made, then removed again, in a folder that is not listed.
        ("convert_office_file", {"path": "cache/v3.pdf"}, {"ok": True}),
        ("convert_office_file", {"path": "_qa/preview.pdf"}, {"ok": True}),
        # The person's own file: read first, changed, then gone.
        ("read_docx", {"path": "mine.docx"}, "ok"),
        ("edit_docx", {"path": "mine.docx"}, {"lines_removed": 1}),
    )
    (tmp_path / "mine.docx").unlink()

    outputs = summarize_activity(messages, catalog, WorkspaceScope(tmp_path))["outputs"]

    assert {o["path"]: o["exists"] for o in outputs} == {"report.docx": True, "mine.docx": False}


def test_a_markdown_file_is_an_artifact_only_when_it_is_a_doc(tmp_path: Path) -> None:
    (tmp_path / "plain.md").write_text("# Notes\n\nNot a Doc.\n", encoding="utf-8")
    (tmp_path / "plan.md").write_text(
        "---\ncoscribe: doc\n---\n\n# Launch plan\n\nWe ship in May.\n\nAfter review.\n",
        encoding="utf-8",
    )
    scope = WorkspaceScope(tmp_path)

    assert describe_artifact(scope, "plain.md") is None
    doc = describe_artifact(scope, "plan.md")

    assert doc is not None and (doc["kind"], doc["name"]) == ("docs", "plan")
    assert doc["excerpt"] == {"heading": "Launch plan", "text": "We ship in May. After review."}
