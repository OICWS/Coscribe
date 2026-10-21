"""What the Artifacts page shows of a file: its kind, its time and a document's opening lines."""

from pathlib import Path

from docx import Document

from coscribe.conversation import describe_artifact
from coscribe.tools import WorkspaceScope


def test_a_document_is_described_with_its_opening_lines(tmp_path: Path) -> None:
    document = Document()
    document.add_heading("Quarterly report", level=1)
    document.add_paragraph("")
    document.add_paragraph("Revenue grew in every region.")
    document.add_paragraph("Costs held steady.")
    document.save(str(tmp_path / "report.docx"))
    scope = WorkspaceScope(tmp_path)

    described = describe_artifact(scope, "report.docx")

    assert described is not None
    assert (described["name"], described["kind"], described["path"]) == (
        "report",
        "docs",
        "report.docx",
    )
    assert described["excerpt"] == {
        "heading": "Quarterly report",
        "text": "Revenue grew in every region. Costs held steady.",
    }


def test_what_is_not_an_artifact_or_not_there_is_not_described(tmp_path: Path) -> None:
    for name in ("notes.md", "~$deck.pptx", "broken.docx"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    scope = WorkspaceScope(tmp_path)

    assert describe_artifact(scope, "notes.md") is None
    assert describe_artifact(scope, "~$deck.pptx") is None
    assert describe_artifact(scope, "gone.pptx") is None
    assert describe_artifact(scope, "../outside.docx") is None
    # A document that does not open is still listed, without an excerpt.
    broken = describe_artifact(scope, "broken.docx")
    assert broken is not None and broken["excerpt"] is None
