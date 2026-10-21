"""Divider and page-break paragraphs for the Docs editor: how a file says them, how one is made."""

from __future__ import annotations

from typing import Any

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
# Parts of a paragraph or run that carry no content of their own.
_PARAGRAPH_FRAME = {"pPr", "bookmarkStart", "bookmarkEnd", "proofErr"}
_RUN_FRAME = {"rPr", "lastRenderedPageBreak"}
BREAK_KINDS = ("divider", "pagebreak")


def _q(name: str) -> str:
    return f"{{{_W}}}{name}"


def _local(element: Any) -> str:
    tag = element.tag
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def break_kind(paragraph: Any) -> str | None:
    """ "divider" for a paragraph that is only a rule under it, "pagebreak" for one that is only a
    page break; None for anything else, which the editor reads as text or keeps locked."""
    properties = paragraph.find(_q("pPr"))
    if properties is not None:
        marks = properties.find(_q("rPr"))
        if properties.find(_q("sectPr")) is not None or (
            marks is not None
            and (marks.find(_q("ins")) is not None or marks.find(_q("del")) is not None)
        ):
            return None
    content = [c for c in paragraph if _local(c) not in _PARAGRAPH_FRAME]
    if not content:
        ruled = (
            properties is not None and properties.find(f"{_q('pBdr')}/{_q('bottom')}") is not None
        )
        return "divider" if ruled else None
    if len(content) == 1 and _local(content[0]) == "r":
        parts = [p for p in content[0] if _local(p) not in _RUN_FRAME]
        if len(parts) == 1 and _local(parts[0]) == "br" and parts[0].get(_q("type")) == "page":
            return "pagebreak"
    return None


def new_break_paragraph(kind: str) -> Any:
    from docx.oxml import OxmlElement

    paragraph = OxmlElement("w:p")
    if kind == "divider":
        properties = OxmlElement("w:pPr")
        border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        for name, value in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "auto")):
            bottom.set(_q(name), value)
        border.append(bottom)
        properties.append(border)
        paragraph.append(properties)
    else:
        run = OxmlElement("w:r")
        page = OxmlElement("w:br")
        page.set(_q("type"), "page")
        run.append(page)
        paragraph.append(run)
    return paragraph
