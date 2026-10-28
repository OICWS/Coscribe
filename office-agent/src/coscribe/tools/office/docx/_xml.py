"""Hand-built OOXML helpers for the docx writer and the tracked-change tools."""

from __future__ import annotations

import random
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from ..._native_docx_tracks import _constants as _tracks_constants
from ..._native_docx_tracks.tracks import TracksMixin, _resolve
from ..markdown_blocks import Block, parse_inline_runs
from ..table_layout import _numeric_columns, _table_layout
from ._style import TABLE_STYLE_ID, is_total_row, set_table_look

_MC_IGNORABLE = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"

_PAGE_SIZES_EMU: dict[str, tuple[int, int]] = {
    # (width, height) in EMU, portrait orientation, at python-docx's own
    # 914400-EMU-per-inch convention -- Inches()/Mm() both just multiply
    # into this unit, using raw EMU here avoids importing docx.shared at
    # module level (kept a lazy, function-local import like every other
    # `docx` usage in this file, see the module docstring).
    "letter": (7772400, 10058400),  # 8.5in x 11in
    "legal": (7772400, 12801600),  # 8.5in x 14in
    "a4": (7560310, 10692130),  # 210mm x 297mm
    "a3": (10692130, 15120620),  # 297mm x 420mm
}


def _docx_text_width_pt(document: Any) -> float:
    section = document.sections[-1]
    if section.page_width is None or section.left_margin is None or section.right_margin is None:
        return 432.0
    return float((section.page_width - section.left_margin - section.right_margin) / 12700)


def _docx_body_font_pt(document: Any) -> float:
    from docx.oxml.ns import qn

    size = document.styles["Normal"].font.size
    if size is not None:
        return float(size.pt)
    defaults = document.styles.element.find(qn("w:docDefaults"))
    if defaults is not None:
        for element in defaults.iter(qn("w:sz")):
            value = element.get(qn("w:val"))
            if value and value.isdigit():
                return int(value) / 2
    return 11.0


def _house_table_style(document: Any) -> Any:
    for style in document.styles:
        if style.style_id == TABLE_STYLE_ID:
            return style
    return None


def _fill_docx_table(document: Any, block: Block) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.shared import Pt

    rows = block.rows
    n_cols = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=n_cols)
    house_style = _house_table_style(document)
    table.style = house_style or "Table Grid"
    body_size = _docx_body_font_pt(document)
    # 10 and 9 pt are 五号/小五, the usual sizes of a Chinese report's tables.
    sizes = [body_size] + [size for size in (10.0, 9.0) if size < body_size]
    font_size, widths = _table_layout(
        rows, _docx_text_width_pt(document), sizes, padding=12.0, header=block.header
    )
    numeric = _numeric_columns(rows, block.header)
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Pt(width)
    # table.cell(r, c) rebuilds the whole cell grid on every call, so
    # filling a table that way is quadratic: 400 rows took 36 s and 1,500
    # never finished. Build the grid once.
    cells = table._cells  # noqa: SLF001
    for row_index, row in enumerate(rows):
        is_header = block.header and row_index == 0
        for col_index in range(n_cols):
            cell_text = row[col_index] if col_index < len(row) else ""
            cell = cells[row_index * n_cols + col_index]
            # Word lays a table out from each cell's own width, LibreOffice
            # from the grid's; both are set so the two agree.
            cell.width = Pt(widths[col_index])
            paragraph = cell.paragraphs[0]
            _add_inline_runs(paragraph, cell_text)
            for run in paragraph.runs:
                if is_header:
                    run.bold = True
                if font_size != body_size:
                    run.font.size = Pt(font_size)
            if numeric[col_index]:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    first_tr = table.rows[0]._tr  # noqa: SLF001
    if house_style is not None:
        last_row = len(rows) > 2 and is_total_row(rows[-1])
        set_table_look(first_tr.getparent(), first_row=block.header, last_row=last_row)
    if block.header:
        tr_pr = first_tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:tblHeader"))


def _add_inline_runs(paragraph: Any, text: str) -> None:
    """Add ``text`` to a python-docx paragraph as one run per
    ``parse_inline_runs`` fragment, so ``**bold**``/``*italic*`` render as
    real formatting instead of literal markup characters."""
    for run_text, bold, italic in parse_inline_runs(text):
        run = paragraph.add_run(run_text)
        if bold:
            run.bold = True
        if italic:
            run.italic = True


def _clear_body(document: Any) -> None:
    """Remove every existing paragraph/table/etc. from a loaded template's
    body, keeping only ``sectPr`` (section properties: page size, margins)
    -- verified empirically that removing it too breaks the document, and
    that removing everything else and re-adding new content afterward
    round-trips cleanly through python-docx."""
    for child in list(document.element.body):
        if not child.tag.endswith("}sectPr"):
            document.element.body.remove(child)


def _mark_body_deleted(document: Any, author: str, change_ids: _ChangeIdCounter) -> None:
    """Template-editing + ``track_changes=True`` variant of ``_clear_body``:
    instead of silently discarding the template's existing paragraphs,
    wrap each one's runs in ``<w:del>``/``<w:delText>`` and mark its
    paragraph mark deleted too, so Word shows the old content as a
    reviewable tracked deletion rather than making it vanish outright.
    Keeps ``sectPr`` like ``_clear_body``. Tables in the template are still
    removed outright (documented v1 scope limit -- table-level tracked
    deletion needs cell/row markup this tool doesn't generate)."""
    for child in list(document.element.body):
        if child.tag.endswith("}sectPr"):
            continue
        if child.tag.endswith("}p"):
            _mark_paragraph_deleted(child, author, change_ids)
        else:
            document.element.body.remove(child)


_TOC_INSTRUCTION = 'TOC \\o "1-3" \\h \\z \\u'
_TOC_EMPTY_RESULT = "No table of contents entries found."


def _add_toc(document: Any) -> Any:
    """Insert a Word TOC field at the current end of the document with an
    empty result -- python-docx has no native TOC API, this is the standard
    raw-OXML field-code recipe (fldChar begin/separate/end + instrText). The
    result stays empty here because headings written after the marker are
    not known yet; ``_fill_toc`` writes it once the whole body exists."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    paragraph = document.add_paragraph()
    code_run = paragraph.add_run()._r
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = _TOC_INSTRUCTION
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    code_run.append(begin)
    code_run.append(instr)
    code_run.append(separate)

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    paragraph.add_run()._r.append(end)
    return paragraph


def _toc_levels(instruction: str) -> tuple[int, int]:
    match = re.search(r'\\o\s+"(\d)-(\d)"', instruction)
    if match is None:
        return 1, 9
    return int(match.group(1)), int(match.group(2))


def _toc_style(document: Any, level: int) -> Any:
    """The template's own ``toc N`` style, else Word's built-in definition of
    it added to the document: Word matches built-in styles by name, so its own
    field update on open keeps the same style. The id only has to be unique;
    a template may already use ``TOC1`` for a style of another name."""
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml.ns import qn
    from docx.shared import Pt, Twips

    name = f"toc {level}"
    used_ids = set()
    for style in document.styles:
        used_ids.add(style.style_id)
        if style.type != WD_STYLE_TYPE.PARAGRAPH:
            continue
        if style.name.lower() == name or (
            style.style_id == f"TOC{level}" and style.name.lower().replace(" ", "") == f"toc{level}"
        ):
            return style
    style_id = f"TOC{level}"
    suffix = 1
    while style_id in used_ids:
        suffix += 1
        style_id = f"TOC{level}_{suffix}"
    style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    # A custom style named like a built-in one is a different style to Word.
    style.element.attrib.pop(qn("w:customStyle"), None)
    style.style_id = style_id
    style.base_style = document.styles["Normal"]
    style.next_paragraph_style = document.styles["Normal"]
    style.priority = 39
    style.unhide_when_used = True
    style.paragraph_format.space_after = Pt(5)
    if level > 1:
        style.paragraph_format.left_indent = Twips(220 * (level - 1))
    return style


def _fill_toc(document: Any, toc_paragraph: Any, headings: list[tuple[int, str]]) -> list[Any]:
    """Write the result of an ``_add_toc`` field: one paragraph per heading in
    the field's ``\\o`` level range, without page numbers -- only Word can
    paginate. Not ``updateFields``: it makes Word ask, on every open, whether
    to update fields that may refer to other files. The result is shown as
    written, and Word's own Update field adds the numbers.
    Returns the paragraphs added after ``toc_paragraph``."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    p_element = toc_paragraph._p
    instruction = "".join(el.text or "" for el in p_element.iter(qn("w:instrText")))
    low, high = _toc_levels(instruction)
    entries = [
        (level, text.strip()) for level, text in headings if low <= level <= high and text.strip()
    ]

    end_run = p_element.findall(qn("w:r"))[-1]
    p_element.remove(end_run)
    if not entries:
        toc_paragraph.add_run(_TOC_EMPTY_RESULT)
        p_element.append(end_run)
        return []

    first_level, first_text = entries[0]
    toc_paragraph.style = _toc_style(document, first_level)
    toc_paragraph.add_run(first_text)
    added: list[Any] = []
    previous = p_element
    for level, text in entries[1:]:
        new_element = OxmlElement("w:p")
        previous.addnext(new_element)
        paragraph = Paragraph(new_element, toc_paragraph._parent)
        paragraph.style = _toc_style(document, level)
        paragraph.add_run(text)
        added.append(paragraph)
        previous = new_element
    previous.append(end_run)
    return added


def _toc_result_paragraphs(body: Any) -> set[Any]:
    """Every paragraph holding text of a TOC field's result. That result
    repeats each heading's text, so a lookup of a heading by its text must
    not count these copies. The set holds the elements themselves, not their
    ``id()``: lxml reuses a proxy only while something references it."""
    from docx.oxml.ns import qn

    fld_char, instr_text, paragraph_tag = qn("w:fldChar"), qn("w:instrText"), qn("w:p")
    text_tags = {qn("w:t"), qn("w:delText")}
    # One entry per open field: [is a TOC field, past its separator].
    fields: list[list[bool]] = []
    inside: set[Any] = set()
    for element in body.iter(fld_char, instr_text, *text_tags):
        if element.tag == fld_char:
            kind = element.get(qn("w:fldCharType"))
            if kind == "begin":
                fields.append([False, False])
            elif kind == "separate" and fields:
                fields[-1][1] = True
            elif kind == "end" and fields:
                fields.pop()
        elif element.tag == instr_text:
            if fields and (element.text or "").strip().upper().startswith("TOC"):
                fields[-1][0] = True
        elif any(is_toc and in_result for is_toc, in_result in fields):
            paragraph = next(element.iterancestors(paragraph_tag), None)
            if paragraph is not None:
                inside.add(paragraph)
    return inside


def _apply_page_setup(document: Any, page_size: str, orientation: str) -> None:
    """Set page width/height/orientation on every section -- python-docx
    exposes this natively (``section.page_width``/``page_height``/
    ``orientation``), it's just never been wired into ``write_docx`` before
    now. Empty ``page_size``/``orientation`` leaves that axis at whatever
    the blank document or template already has."""
    from docx.enum.section import WD_ORIENT
    from docx.shared import Emu

    if page_size:
        key = page_size.strip().lower()
        if key not in _PAGE_SIZES_EMU:
            raise ValueError(
                f"Unknown page_size {page_size!r}. Supported: {', '.join(sorted(_PAGE_SIZES_EMU))}"
            )
    if orientation:
        orientation_key = orientation.strip().lower()
        if orientation_key not in ("portrait", "landscape"):
            raise ValueError(f"Unknown orientation {orientation!r}. Use 'portrait' or 'landscape'.")
    else:
        orientation_key = ""

    for section in document.sections:
        width, height = (
            _PAGE_SIZES_EMU[page_size.strip().lower()]
            if page_size
            else (section.page_width, section.page_height)
        )
        if orientation_key == "landscape":
            width, height = max(width, height), min(width, height)
            section.orientation = WD_ORIENT.LANDSCAPE
        elif orientation_key == "portrait":
            width, height = min(width, height), max(width, height)
            section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Emu(int(width))
        section.page_height = Emu(int(height))


class _ChangeIdCounter:
    """Shared, monotonically increasing ``w:id`` source for every
    ``<w:ins>``/``<w:del>`` element a single ``write_docx`` call produces --
    Word requires these unique across the whole document."""

    def __init__(self, start: int = 0) -> None:
        self._next = start

    def next(self) -> int:
        value = self._next
        self._next += 1
        return value


def _mark_paragraph_deleted(
    paragraph_element: Any, author: str, change_ids: _ChangeIdCounter
) -> None:
    """In place: convert every run's ``<w:t>`` to ``<w:delText>``, wrap each
    run in ``<w:del>``, and mark the paragraph mark itself deleted (so
    accepting the change merges this paragraph into the next one, matching
    Word's own behavior for a fully-deleted paragraph and the docx skill's
    documented XML shape for paragraph deletions)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    p_pr = paragraph_element.find(qn("w:pPr"))
    if p_pr is None:
        p_pr = OxmlElement("w:pPr")
        paragraph_element.insert(0, p_pr)
    r_pr = p_pr.find(qn("w:rPr"))
    if r_pr is None:
        r_pr = OxmlElement("w:rPr")
        p_pr.append(r_pr)
    mark_del = OxmlElement("w:del")
    mark_del.set(qn("w:id"), str(change_ids.next()))
    mark_del.set(qn("w:author"), author)
    mark_del.set(qn("w:date"), date)
    r_pr.insert(0, mark_del)

    for run in list(paragraph_element.findall(qn("w:r"))):
        texts = run.findall(qn("w:t"))
        if not texts:
            continue
        for text_element in texts:
            text_element.tag = qn("w:delText")
            text_element.set(qn("xml:space"), "preserve")
        run_index = list(paragraph_element).index(run)
        wrapper = OxmlElement("w:del")
        wrapper.set(qn("w:id"), str(change_ids.next()))
        wrapper.set(qn("w:author"), author)
        wrapper.set(qn("w:date"), date)
        paragraph_element.remove(run)
        wrapper.append(run)
        paragraph_element.insert(run_index, wrapper)


def _mark_paragraph_inserted(
    paragraph_element: Any, author: str, change_ids: _ChangeIdCounter
) -> None:
    """In place: wrap every direct ``<w:r>`` run child in ``<w:ins>``, so
    Word shows this (newly written) paragraph's text as a tracked insertion
    a reviewer can accept/reject, instead of silently-already-final
    content. Tables are not wrapped this way (documented v1 scope limit --
    see ``write_docx``'s docstring)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for run in list(paragraph_element.findall(qn("w:r"))):
        run_index = list(paragraph_element).index(run)
        wrapper = OxmlElement("w:ins")
        wrapper.set(qn("w:id"), str(change_ids.next()))
        wrapper.set(qn("w:author"), author)
        wrapper.set(qn("w:date"), date)
        paragraph_element.remove(run)
        wrapper.append(run)
        paragraph_element.insert(run_index, wrapper)


def _new_comment_anchor(paragraph_element: Any, comment_id: str) -> None:
    """Wrap the whole paragraph in ``<w:commentRangeStart>``/
    ``<w:commentRangeEnd>`` + append the ``<w:commentReference>`` run, so
    the comment (written separately to ``comments.xml``) anchors to this
    entire paragraph/bullet/heading. No sub-paragraph anchor in this tool's
    v1 -- a comment always spans the whole block it's attached to."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    start = OxmlElement("w:commentRangeStart")
    start.set(qn("w:id"), comment_id)
    p_pr = paragraph_element.find(qn("w:pPr"))
    paragraph_element.insert(1 if p_pr is not None else 0, start)

    end = OxmlElement("w:commentRangeEnd")
    end.set(qn("w:id"), comment_id)
    paragraph_element.append(end)

    ref_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    r_style = OxmlElement("w:rStyle")
    r_style.set(qn("w:val"), "CommentReference")
    r_pr.append(r_style)
    ref_run.append(r_pr)
    comment_ref = OxmlElement("w:commentReference")
    comment_ref.set(qn("w:id"), comment_id)
    ref_run.append(comment_ref)
    paragraph_element.append(ref_run)


def _build_comments_xml(comments: list[tuple[str, str, str]]) -> bytes:
    """``comments``: list of ``(comment_id, author, text)``. Builds the
    standalone ``word/comments.xml`` part -- small and flat enough that
    plain string templating (with proper XML escaping) is simpler and just
    as safe here as a full XML-tree build."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
    ]
    for comment_id, author, text in comments:
        initials = "".join(part[0] for part in author.split()[:2]).upper() or "?"
        parts.append(
            f'<w:comment w:id="{comment_id}" w:author="{_xml_escape(author)}" '
            f'w:date="{now}" w:initials="{_xml_escape(initials)}">'
            f'<w:p><w:r><w:t xml:space="preserve">{_xml_escape(text)}</w:t></w:r></w:p>'
            f"</w:comment>"
        )
    parts.append("</w:comments>")
    return "".join(parts).encode("utf-8")


def _write_comments_part(file_path: Path, comments_xml: bytes) -> None:
    """Append ``word/comments.xml`` + its content-type override + a
    relationship to an already-saved .docx. python-docx has no public API
    for adding a part type it doesn't itself know about, so this is the
    same "unzip, patch, rezip" approach the docx skill documents for adding
    comments to an existing file -- applied here right after this tool's
    own from-scratch save. ``word/document.xml`` itself is never re-parsed
    here: python-docx already wrote the comment-range anchors correctly as
    part of the normal save, since ``_new_comment_anchor`` mutated the
    in-memory tree before ``document.save()`` was called."""
    from lxml import etree

    with zipfile.ZipFile(file_path, "r") as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}

    entries["word/comments.xml"] = comments_xml

    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    content_types = etree.fromstring(entries["[Content_Types].xml"])
    override = etree.SubElement(content_types, f"{{{ct_ns}}}Override")
    override.set("PartName", "/word/comments.xml")
    override.set(
        "ContentType",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
    )
    entries["[Content_Types].xml"] = etree.tostring(
        content_types, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    pr_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    rels_path = "word/_rels/document.xml.rels"
    rels_root = etree.fromstring(entries[rels_path])
    max_n = 0
    for rel in rels_root.findall(f"{{{pr_ns}}}Relationship"):
        rid = rel.get("Id") or ""
        if rid.startswith("rId") and rid[3:].isdigit():
            max_n = max(max_n, int(rid[3:]))
    relationship = etree.SubElement(rels_root, f"{{{pr_ns}}}Relationship")
    relationship.set("Id", f"rId{max_n + 1}")
    relationship.set(
        "Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
    )
    relationship.set("Target", "comments.xml")
    entries[rels_path] = etree.tostring(
        rels_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, payload in entries.items():
            zout.writestr(name, payload)


def _ensure_para_ids(document_element: Any) -> None:
    """Assign a ``w14:paraId`` to every ``<w:p>`` that doesn't already have
    one. ``_native_docx_tracks.tracks.TracksMixin``'s whole paragraph-lookup
    contract is keyed on this attribute -- real Word always sets it, but
    ``python-docx`` never does, so a freshly-written or freshly-edited
    document needs it backfilled before any tracked-change tool can address
    a paragraph. ``w14`` is a Word 2010+ extension namespace, not part of
    the base ``wml.xsd``, so this also adds it to the document root's
    ``mc:Ignorable`` list when missing -- the same declaration real
    Word-authored files carry, and the one ``_strip_mce_ignorable`` already
    knows how to treat as extension content rather than a schema defect."""
    existing: set[str] = set()
    missing: list[Any] = []
    for paragraph in document_element.iter(f"{_tracks_constants.W}p"):
        para_id = paragraph.get(f"{_tracks_constants.W14}paraId")
        if para_id:
            existing.add(para_id.upper())
        else:
            missing.append(paragraph)
    if not missing:
        return

    ignorable_tokens = (document_element.get(_MC_IGNORABLE) or "").split()
    if "w14" not in ignorable_tokens:
        ignorable_tokens.append("w14")
        document_element.set(_MC_IGNORABLE, " ".join(ignorable_tokens))

    for paragraph in missing:
        while True:
            candidate = f"{random.randint(1, 0x7FFFFFFF):08X}"
            if candidate not in existing:
                existing.add(candidate)
                break
        paragraph.set(f"{_tracks_constants.W14}paraId", candidate)


def _text_column_emu(document: Any) -> int:
    section = document.sections[-1]
    return int((section.page_width or 0) - (section.left_margin or 0) - (section.right_margin or 0))


def _locate_paragraph(
    document_element: Any,
    find: str,
    context_before: str,
    context_after: str,
    *,
    ignore_case: bool,
) -> str:
    """Return the ``w14:paraId`` of the single paragraph where
    ``tracks.py``'s own per-paragraph ``_resolve`` would unambiguously
    locate ``find`` (respecting ``context_before``/``context_after``) --
    tried against every paragraph in the document, since coscribe's own
    tools address text by its content, not by a paragraph id the caller has
    no way to already know. Raises ``ValueError`` if no paragraph matches,
    or if more than one does."""
    if not find:
        raise ValueError("find text is empty")
    matches: list[str] = []
    ambiguous_within: list[str] = []
    toc_entries = _toc_result_paragraphs(document_element)
    for paragraph in document_element.iter(f"{_tracks_constants.W}p"):
        if paragraph in toc_entries:
            continue
        para_id = paragraph.get(f"{_tracks_constants.W14}paraId", "")
        try:
            _resolve(
                document_element,
                paragraph,
                find,
                context_before,
                context_after,
                ignore_case=ignore_case,
            )
        except ValueError as exc:
            if "Ambiguous" in str(exc):
                ambiguous_within.append(f"paragraph {para_id}: {exc}")
            continue
        matches.append(para_id)

    if not matches:
        if ambiguous_within:
            raise ValueError(
                f"Text {find!r} is ambiguous within a paragraph; provide "
                f"context_before/context_after. " + "; ".join(ambiguous_within)
            )
        raise ValueError(f"Text {find!r} not found in the document")
    if len(matches) > 1:
        raise ValueError(
            f"Text {find!r} found in {len(matches)} different paragraphs; "
            "provide context_before or context_after to disambiguate"
        )
    return matches[0]


class _TrackedDocxHost(TracksMixin):
    """Adapts ``TracksMixin``'s small host contract to an already-open
    python-docx ``Document`` -- coscribe already has the tree in memory via
    ``Document(path)``/``document.save()``, so it doesn't need docx-mcp's
    own unzip/parse/repack lifecycle (see ``_native_docx_tracks/NOTICE.md``).
    Only ``_require`` and ``_mark`` are adapter-specific; ``_find_para``/
    ``_next_markup_id``/``_make_run`` are the same plain functions
    ``tracks.py`` itself was extracted alongside (see ``_constants.py``),
    bound here via ``staticmethod`` since ``tracks.py`` calls them as
    ``self.<name>(...)``."""

    _find_para = staticmethod(_tracks_constants._find_para)
    _next_markup_id = staticmethod(_tracks_constants._next_markup_id)
    _make_run = staticmethod(_tracks_constants._make_run)

    def __init__(self, document: Any) -> None:
        self._document_element = document.element
        _ensure_para_ids(self._document_element)

    def _require(self, rel_path: str) -> Any:
        if rel_path != "word/document.xml":
            raise RuntimeError(f"{rel_path} not supported by tracked-change edits")
        return self._document_element

    def _mark(self, rel_path: str) -> None:
        pass  # python-docx re-serializes the whole tree on save() regardless
