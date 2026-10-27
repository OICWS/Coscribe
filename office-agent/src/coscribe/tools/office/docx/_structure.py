"""Writing markdown blocks into a python-docx document, and the structural edits of
`edit_docx_structure`: insert blocks, move a section, delete a section."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..markdown_blocks import parse_blocks
from ._xml import (
    _add_inline_runs,
    _add_toc,
    _ChangeIdCounter,
    _fill_docx_table,
    _fill_toc,
    _mark_paragraph_deleted,
    _mark_paragraph_inserted,
    _toc_result_paragraphs,
)

OPERATIONS = ("insert", "move_section", "delete_section")
_PLACES = ("after", "before", "after_section")
_HEADING_STYLE = re.compile(r"^heading ([1-9])$", re.IGNORECASE)


@dataclass
class Written:
    """What `add_blocks` appended: the new body children in order, the TOC paragraphs waiting
    to be filled, the headings written, and the comments to anchor."""

    elements: list[Any] = field(default_factory=list)
    tocs: list[Any] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)
    comments: list[tuple[Any, str]] = field(default_factory=list)


def add_blocks(
    document: Any, content: str, change_author: str | None, change_ids: _ChangeIdCounter
) -> Written:
    """Append `content` (the markdown subset) to the end of the body, as `write_docx` writes it.
    With `change_author`, every paragraph is a tracked insertion; tables never are."""
    body = document.element.body
    existing = set(body)
    written = Written()
    previous_kind = ""
    list_num: int | None = None
    for block in parse_blocks(content):
        paragraph = None
        if block.kind == "heading":
            paragraph = document.add_heading("", level=block.level)
            _add_inline_runs(paragraph, block.text)
            written.headings.append((block.level, paragraph.text))
        elif block.kind == "bullet":
            paragraph = document.add_paragraph(style="List Bullet")
            _add_inline_runs(paragraph, block.text)
        elif block.kind == "number":
            paragraph = document.add_paragraph(style="List Number")
            _add_inline_runs(paragraph, block.text)
            if previous_kind != "number":
                list_num = _restarted_numbering(document, paragraph)
            if list_num is not None:
                paragraph._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = list_num
        elif block.kind == "toc":
            written.tocs.append(_add_toc(document))
        elif block.kind == "table" and block.rows:
            if previous_kind == "table":
                # Word joins back-to-back tables into one.
                spacer = document.add_paragraph()
                if change_author is not None:
                    _mark_paragraph_inserted(spacer._p, change_author, change_ids)
            _fill_docx_table(document, block)
        else:
            paragraph = document.add_paragraph()
            _add_inline_runs(paragraph, block.text)

        previous_kind = block.kind
        if paragraph is None:
            continue
        if change_author is not None:
            _mark_paragraph_inserted(paragraph._p, change_author, change_ids)
        if block.comment:
            written.comments.append((paragraph._p, block.comment))
    written.elements = [child for child in body if child not in existing]
    return written


def _restarted_numbering(document: Any, paragraph: Any) -> int | None:
    """A new numbering instance for a numbered list, restarting at 1: every List Number
    paragraph shares the style's one instance, so a second list would go on counting from
    where the first stopped."""
    from docx.oxml.ns import qn

    num_pr = paragraph.style.element.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
    num_id = num_pr.find(qn("w:numId")) if num_pr is not None else None
    if num_id is None:
        return None
    numbering = document.part.numbering_part.element
    abstract = numbering.num_having_numId(int(num_id.get(qn("w:val")))).abstractNumId.val
    num = numbering.add_num(abstract)
    num.add_lvlOverride(ilvl=0).add_startOverride(1)
    return int(num.numId)


def finish_tocs(
    document: Any,
    toc_paragraphs: list[Any],
    headings: list[tuple[int, str]],
    change_author: str | None,
    change_ids: _ChangeIdCounter,
) -> bool:
    for toc_paragraph in toc_paragraphs:
        added = _fill_toc(document, toc_paragraph, headings)
        if change_author is not None:
            for entry in [toc_paragraph, *added]:
                _mark_paragraph_inserted(entry._p, change_author, change_ids)
    return bool(toc_paragraphs)


def _paragraphs(document: Any) -> list[tuple[Any, str, int | None]]:
    """Each top-level paragraph's element, text and heading level (None for body text). The
    level comes from the style's name: Word stores built-in style names in English whatever
    the interface language."""
    from docx.oxml.ns import qn

    names = {style.style_id: style.name or "" for style in document.styles}
    default = document.styles.default(1)
    rows: list[tuple[Any, str, int | None]] = []
    for element in document.element.body.iterchildren(qn("w:p")):
        style = element.find(f"{qn('w:pPr')}/{qn('w:pStyle')}")
        name = names.get(style.get(qn("w:val")), "") if style is not None else default.name
        match = _HEADING_STYLE.match(name or "")
        text = "".join(t.text or "" for t in element.iter(qn("w:t"))).strip()
        rows.append((element, text, int(match.group(1)) if match else None))
    return rows


def _heading_levels(document: Any) -> dict[Any, int]:
    return {element: level for element, _, level in _paragraphs(document) if level is not None}


def _find(document: Any, text: str, what: str, *, heading: bool = False) -> Any:
    """The one top-level paragraph whose text is `text` (or, failing that, contains it), not
    counting a contents list's copies of headings."""
    wanted = text.strip()
    if not wanted:
        raise ValueError(f"{what} is empty")
    skipped = _toc_result_paragraphs(document.element.body)
    candidates = [
        (element, body)
        for element, body, level in _paragraphs(document)
        if element not in skipped and (not heading or level is not None)
    ]
    matches = [e for e, body in candidates if body == wanted] or [
        e for e, body in candidates if wanted in body
    ]
    kind = "heading" if heading else "paragraph"
    if not matches:
        raise ValueError(f"{what}: no {kind} reads {text!r}")
    if len(matches) > 1:
        raise ValueError(
            f"{what}: {len(matches)} {kind}s contain {text!r}; give more of the text so it "
            "names one"
        )
    return matches[0]


def _section(document: Any, heading_text: str, what: str) -> list[Any]:
    """The heading and every body element after it up to the next heading of the same or a
    higher level (or the end of the document)."""
    heading = _find(document, heading_text, what, heading=True)
    levels = _heading_levels(document)
    level = levels[heading]
    children = [c for c in document.element.body if not c.tag.endswith("}sectPr")]
    start = children.index(heading)
    end = start + 1
    while end < len(children) and levels.get(children[end], 99) > level:
        end += 1
    section = children[start:end]
    if any(element.find(".//{*}sectPr") is not None for element in section):
        raise ValueError(
            f"{what}: the section {heading_text!r} holds a section break (a change of page "
            "layout), which this tool does not move or delete"
        )
    return section


def _place(document: Any, operation: dict[str, str], what: str, elements: list[Any]) -> None:
    given = [key for key in _PLACES if operation.get(key)]
    if len(given) != 1:
        raise ValueError(f"{what}: give exactly one of {', '.join(_PLACES)}")
    key = given[0]
    if key == "after_section":
        anchor = _section(document, operation[key], what)[-1]
    else:
        anchor = _find(document, operation[key], what)
    if anchor in elements:
        raise ValueError(f"{what}: the place named is inside what is being moved")
    if key == "before":
        for element in elements:
            anchor.addprevious(element)
        return
    for element in elements:
        anchor.addnext(element)
        anchor = element


def _match_table_style(document: Any, new_elements: list[Any]) -> None:
    """New tables take the style of the document's first existing table, so they look like
    the user's own."""
    from docx.oxml.ns import qn

    new = {e for e in new_elements if e.tag == qn("w:tbl")}
    for table in document.element.body.iter(qn("w:tbl")):
        if table in new:
            continue
        style = table.find(f"{qn('w:tblPr')}/{qn('w:tblStyle')}")
        if style is None:
            return
        for element in new:
            element.find(f"{qn('w:tblPr')}/{qn('w:tblStyle')}").set(
                qn("w:val"), style.get(qn("w:val"))
            )
            # The user's table style decides how its header row looks, as it does for theirs.
            first_row = element.find(qn("w:tr"))
            for bold in list(first_row.iter(qn("w:b"))) if first_row is not None else []:
                bold.getparent().remove(bold)
        return


def _title_tocs(document: Any, written: Written) -> None:
    """A heading written right above a contents list is its title: Word's "TOC Heading" style
    looks like a heading but stays out of the list."""
    from docx.oxml.ns import qn

    title = next((s for s in document.styles if s.name == "TOC Heading"), None)
    if title is None:
        return
    toc_elements = {e for e in written.elements if e.find(f".//{qn('w:instrText')}") is not None}
    levels = _heading_levels(document)
    for element, following in zip(written.elements, written.elements[1:], strict=False):
        if element in levels and following in toc_elements:
            element.find(f"{qn('w:pPr')}/{qn('w:pStyle')}").set(qn("w:val"), title.style_id)


def summary(document: Any) -> dict[str, object]:
    """What the edited document holds, so the caller can check the result without opening it:
    its headings in order, its tables and pictures, its header and footer, its contents list."""
    from docx.oxml.ns import qn

    body = document.element.body
    skipped = _toc_result_paragraphs(body)
    section = document.sections[0]
    return {
        "headings": [
            f"{'#' * level} {text}"
            for element, text, level in _paragraphs(document)
            if level is not None and element not in skipped
        ],
        "tables": len(list(body.iterchildren(qn("w:tbl")))),
        "pictures": len(list(body.iter(qn("w:drawing")))),
        "contents_list": any("TOC" in (t.text or "") for t in body.iter(qn("w:instrText"))),
        "header": " / ".join(p.text for p in section.header.paragraphs if p.text),
        "footer": " / ".join(p.text for p in section.footer.paragraphs if p.text),
    }


def describe(document: Any) -> str:
    """The document's structure as text: one line per top-level block in order (a paragraph's
    style and the start of its text, a table's size, style and first row, a picture's size, a
    contents list, a section break), then each section's page, header and footer. What the
    markdown view leaves out, for checking a document before and after an edit."""
    from docx.oxml.ns import qn

    def cut(text: str, length: int = 70) -> str:
        return text if len(text) <= length else text[: length - 1] + "…"

    body = document.element.body
    names = {style.style_id: style.name or "" for style in document.styles}
    default = document.styles.default(1).name
    toc_entries = _toc_result_paragraphs(body)
    lines: list[str] = []
    for child in body.iterchildren():
        if child.tag == qn("w:tbl"):
            rows = child.findall(qn("w:tr"))
            columns = max((len(r.findall(qn("w:tc"))) for r in rows), default=0)
            style = child.find(f"{qn('w:tblPr')}/{qn('w:tblStyle')}")
            name = names.get(style.get(qn("w:val")), "") if style is not None else "no style"
            first = " | ".join(
                "".join(t.text or "" for t in cell.iter(qn("w:t"))).strip()
                for cell in (rows[0].findall(qn("w:tc")) if rows else [])
            )
            lines.append(f"table {len(rows)}x{columns} [{name}]: {cut(first)}")
            continue
        if child.tag != qn("w:p"):
            continue
        # The field's first paragraph is also its first entry, so it is looked at first.
        if any("TOC" in (t.text or "") for t in child.iter(qn("w:instrText"))):
            count = sum(1 for e in toc_entries if e.getparent() is body)
            lines.append(f"contents list ({count} entries)")
            continue
        if child in toc_entries:
            continue
        style = child.find(f"{qn('w:pPr')}/{qn('w:pStyle')}")
        name = names.get(style.get(qn("w:val")), "") if style is not None else default
        text = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
        line = f"[{name}] {cut(text)}" if text else f"[{name}] (empty)"
        for extent in child.iter(
            "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent"
        ):
            width, height = (int(extent.get(k, "0")) / 360000 for k in ("cx", "cy"))
            line += f" + picture {width:.1f}x{height:.1f} cm"
        if (
            child.find(f".//{qn('w:ins')}") is not None
            or child.find(f".//{qn('w:del')}") is not None
        ):
            line += " (tracked changes)"
        if child.find(f"{qn('w:pPr')}/{qn('w:sectPr')}") is not None:
            line += " -- section break"
        lines.append(line)
    for number, section in enumerate(document.sections, start=1):
        width = (section.page_width or 0) / 360000
        height = (section.page_height or 0) / 360000
        header = " / ".join(p.text for p in section.header.paragraphs if p.text) or "(none)"
        footer = " / ".join(p.text for p in section.footer.paragraphs if p.text) or "(none)"
        lines.append(
            f"section {number}: page {width:.1f}x{height:.1f} cm; header: {header}; "
            f"footer: {footer}"
        )
    return "\n".join(lines)


def apply_operations(
    document: Any,
    operations: list[dict[str, str]],
    change_author: str | None,
    change_ids: _ChangeIdCounter,
) -> list[str]:
    """Apply `operations` in order; returns one line per operation saying what it did."""
    done: list[str] = []
    tocs: list[Any] = []
    for number, operation in enumerate(operations, start=1):
        op = operation.get("op", "")
        what = f"operation {number} ({op or 'no op'})"
        if op not in OPERATIONS:
            raise ValueError(f"{what}: op must be one of {', '.join(OPERATIONS)}")
        if op == "insert":
            content = operation.get("content", "")
            if not content.strip():
                raise ValueError(f"{what}: content is empty")
            if "{{comment:" in content:
                raise ValueError(f"{what}: comments are not supported here; use write_docx")
            written = add_blocks(document, content, change_author, change_ids)
            _match_table_style(document, written.elements)
            _title_tocs(document, written)
            _place(document, operation, what, written.elements)
            tocs += written.tocs
            done.append(f"{what}: inserted {len(written.elements)} block(s)")
        elif op == "move_section":
            if change_author is not None:
                raise ValueError(
                    f"{what}: a move can't be tracked (Word records it as moveFrom/moveTo, "
                    "which this tool doesn't write); move without track_changes"
                )
            section = _section(document, operation.get("section", ""), what)
            _place(document, operation, what, section)
            done.append(f"{what}: moved {len(section)} block(s)")
        else:
            section = _section(document, operation.get("section", ""), what)
            if change_author is None:
                for element in section:
                    element.getparent().remove(element)
            elif any(not element.tag.endswith("}p") for element in section):
                raise ValueError(
                    f"{what}: the section holds a table, which can't be deleted as a tracked "
                    "change; delete it without track_changes"
                )
            else:
                for element in section:
                    _mark_paragraph_deleted(element, change_author, change_ids)
            done.append(f"{what}: deleted {len(section)} block(s)")
    if tocs:
        skipped = _toc_result_paragraphs(document.element.body)
        headings = [
            (level, body)
            for element, body, level in _paragraphs(document)
            if level is not None and element not in skipped
        ]
        finish_tocs(document, tocs, headings, change_author, change_ids)
    return done
