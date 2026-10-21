"""A .docx as blocks for the Docs editor (decision 0019): read it, and write back only the blocks
the person changed.

A block is a heading, paragraph, quote or list item with its runs (bold, italic, underline, link),
or a table of such cells. What the editor does not model (images, fields, comments, tracked
changes, section breaks, merged tables) is a locked block: shown, kept as it is, and removed only
if the person deletes it. A save carries the version of the file the editor read, and is refused
over a newer one."""

from __future__ import annotations

import copy
import hashlib
import io
import re
from pathlib import Path
from typing import Any

from ..._file_locks import file_lock
from ..._ooxml_validate import assert_wml_valid
from ..markdown_blocks import Block
from ._review import write_atomically
from .block_breaks import BREAK_KINDS, break_kind, new_break_paragraph
from .block_images import decode_picture, images_of, new_picture_paragraph

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_LINK_COLOUR = "0563C1"
_LINK_SCHEMES = ("http://", "https://", "mailto:")
_MAX_LEVEL = 3
_PREVIEW = 160


class DocChanged(Exception):
    """The file is not the version the editor read."""


class BlocksRefused(ValueError):
    """A save that cannot be made; the text is safe to show the person."""


def _q(name: str) -> str:
    return f"{{{_W}}}{name}"


def _local(element: Any) -> str:
    tag = element.tag
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _on(element: Any | None) -> bool:
    """A toggle property (`w:b`, `w:i`) is on when present unless it says off."""
    return element is not None and element.get(_q("val"), "true") not in ("0", "false", "off")


def version_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


# -- Reading ---------------------------------------------------------------------------------------

_TEXT_RUN_PARTS = {"rPr", "t", "tab", "lastRenderedPageBreak"}
_TRANSPARENT = {"bookmarkStart", "bookmarkEnd", "proofErr"}
_LOCKS = {
    "drawing": "image or drawing",
    "pict": "image or drawing",
    "object": "image or drawing",
    "fldChar": "field",
    "instrText": "field",
    "fldSimple": "field",
    "commentReference": "comment",
    "commentRangeStart": "comment",
    "commentRangeEnd": "comment",
    "footnoteReference": "note",
    "endnoteReference": "note",
    "ins": "tracked change",
    "del": "tracked change",
    "moveFrom": "tracked change",
    "moveTo": "tracked change",
}


def _run_lock(run: Any) -> str | None:
    for part in run:
        name = _local(part)
        if name in _TEXT_RUN_PARTS:
            continue
        if name == "br":
            if part.get(_q("type"), "textWrapping") != "textWrapping":
                return "page break"
            continue
        return _LOCKS.get(name, "other content")
    return None


def _lock_reason(paragraph: Any) -> str | None:
    """Why the editor cannot change this paragraph, None when it can."""
    for child in paragraph:
        name = _local(child)
        reason: str | None = None
        if name == "pPr":
            marks = child.find(_q("rPr"))
            if child.find(_q("sectPr")) is not None:
                reason = "section break"
            elif marks is not None and (
                marks.find(_q("ins")) is not None or marks.find(_q("del")) is not None
            ):
                reason = "tracked change"
        elif name == "r":
            reason = _run_lock(child)
        elif name == "hyperlink":
            if child.get(f"{{{_R}}}id") is None:
                reason = "internal link"
            else:
                reason = next(
                    (r for run in child if _local(run) == "r" and (r := _run_lock(run))), None
                )
        elif name not in _TRANSPARENT:
            reason = _LOCKS.get(name, "other content")
        if reason:
            return reason
    return None


def _run_text(run: Any) -> str:
    parts = []
    for part in run:
        name = _local(part)
        if name == "t":
            parts.append(part.text or "")
        elif name == "tab":
            parts.append("\t")
        elif name == "br":
            parts.append("\n")
    return "".join(parts)


def _marks(run: Any) -> dict[str, Any]:
    props = run.find(_q("rPr"))
    if props is None:
        return {}
    marks: dict[str, Any] = {}
    if _on(props.find(_q("b"))):
        marks["b"] = True
    if _on(props.find(_q("i"))):
        marks["i"] = True
    underline = props.find(_q("u"))
    if underline is not None and underline.get(_q("val"), "single") != "none":
        marks["u"] = True
    return marks


def _merged(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adjacent runs that look the same are one; a run with no text is none."""
    merged: list[dict[str, Any]] = []
    for run in runs:
        if not run.get("t"):
            continue
        if merged and {k: v for k, v in merged[-1].items() if k != "t"} == {
            k: v for k, v in run.items() if k != "t"
        }:
            merged[-1] = {**merged[-1], "t": merged[-1]["t"] + run["t"]}
        else:
            merged.append(dict(run))
    return merged


def _read_runs(paragraph: Any, links: Any) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for child in paragraph:
        name = _local(child)
        if name == "r":
            runs.append({"t": _run_text(child), **_marks(child)})
        elif name == "hyperlink":
            relation = links.get(child.get(f"{{{_R}}}id"))
            url = getattr(relation, "target_ref", None)
            for run in child:
                if _local(run) == "r":
                    # A link is drawn underlined and coloured: its look, not a mark of the text.
                    marks = {k: v for k, v in _marks(run).items() if k != "u" or not url}
                    runs.append({"t": _run_text(run), **marks, **({"link": url} if url else {})})
    return _merged(runs)


_LIST_STYLE = re.compile(r"^List (Bullet|Number)(?: ([23]))?$")
_HEADING_STYLE = re.compile(r"^Heading ([1-3])$")


class _Context:
    def __init__(self, document: Any) -> None:
        self.document = document
        self.style_names = {s.style_id: (s.name or "") for s in document.styles}
        self.links = document.part.rels

    def style_of(self, paragraph: Any) -> str:
        style = paragraph.find(f"{_q('pPr')}/{_q('pStyle')}")
        return (
            self.style_names.get(style.get(_q("val")), "Normal") if style is not None else "Normal"
        )

    def numbered(self, paragraph: Any) -> tuple[str, int] | None:
        """(`bullet` or `number`, level) of a paragraph numbered by its own numbering."""
        num = paragraph.find(f"{_q('pPr')}/{_q('numPr')}")
        if num is None:
            return None
        level_el, id_el = num.find(_q("ilvl")), num.find(_q("numId"))
        level = int(level_el.get(_q("val"), "0")) if level_el is not None else 0
        if id_el is None or id_el.get(_q("val")) == "0":
            return None
        return self._list_kind(id_el.get(_q("val")), level), level + 1

    def _list_kind(self, num_id: str | None, level: int) -> str:
        try:
            numbering = self.document.part.numbering_part.element
            abstract = numbering.num_having_numId(int(num_id or "0")).abstractNumId.val
            for definition in numbering.findall(_q("abstractNum")):
                if definition.get(_q("abstractNumId")) == str(abstract):
                    for lvl in definition.findall(_q("lvl")):
                        if lvl.get(_q("ilvl")) == str(level):
                            fmt = lvl.find(_q("numFmt"))
                            return (
                                "bullet"
                                if fmt is not None and fmt.get(_q("val")) == "bullet"
                                else "number"
                            )
        except (KeyError, ValueError, AttributeError):
            pass
        return "number"


def _paragraph_block(paragraph: Any, context: _Context) -> dict[str, Any]:
    if (rule := break_kind(paragraph)) is not None:
        return {"kind": rule}
    reason = _lock_reason(paragraph)
    if reason is not None:
        return _locked(reason, _plain(paragraph), images_of(paragraph))
    name = context.style_of(paragraph)
    block: dict[str, Any]
    heading, listed = _HEADING_STYLE.match(name), _LIST_STYLE.match(name)
    if name == "Title":
        block = {"kind": "title"}
    elif heading:
        block = {"kind": "heading", "level": int(heading.group(1))}
    elif name == "Quote":
        block = {"kind": "quote"}
    elif listed:
        block = {"kind": listed.group(1).lower(), "level": int(listed.group(2) or 1)}
    elif (own := context.numbered(paragraph)) is not None:
        if own[1] > _MAX_LEVEL:
            return _locked("deep list", _plain(paragraph))
        block = {"kind": own[0], "level": own[1]}
    else:
        block = {"kind": "paragraph", **({"style": name} if name != "Normal" else {})}
    block["runs"] = _read_runs(paragraph, context.links)
    return block


def _plain(element: Any) -> str:
    text = "".join(t.text or "" for t in element.iter(_q("t"), _q("delText")))
    return text[:_PREVIEW]


def _locked(what: str, text: str = "", images: list[str] | None = None) -> dict[str, Any]:
    return {"kind": "locked", "what": what, "text": text, **({"images": images} if images else {})}


def _table_block(table: Any, context: _Context) -> dict[str, Any]:
    rows = table.findall(_q("tr"))
    grid: list[list[list[dict[str, Any]]]] = []
    for row in rows:
        cells = row.findall(_q("tc"))
        line = []
        for cell in cells:
            paragraphs = [c for c in cell if _local(c) not in ("tcPr",)]
            span = cell.find(f"{_q('tcPr')}/{_q('gridSpan')}")
            merged = cell.find(f"{_q('tcPr')}/{_q('vMerge')}")
            if (
                len(paragraphs) != 1
                or _local(paragraphs[0]) != "p"
                or span is not None
                or merged is not None
                or _lock_reason(paragraphs[0]) is not None
            ):
                return _locked("table", _plain(table))
            line.append(_read_runs(paragraphs[0], context.links))
        grid.append(line)
    if not grid or len({len(line) for line in grid}) != 1:
        return _locked("table", _plain(table))
    header = rows[0].find(f"{_q('trPr')}/{_q('tblHeader')}") is not None
    return {"kind": "table", "header": header, "rows": grid}


def _body_blocks(document: Any) -> list[tuple[dict[str, Any], Any]]:
    context = _Context(document)
    found = []
    index = 0
    for child in document.element.body:
        name = _local(child)
        if name == "sectPr":
            continue
        if name == "p":
            block = _paragraph_block(child, context)
        elif name == "tbl":
            block = _table_block(child, context)
        else:
            block = _locked("other content", _plain(child))
        found.append(({"id": f"b{index}", **block}, child))
        index += 1
    return found


def read_doc_blocks(path: Path) -> dict[str, Any]:
    """The document as blocks and the version the editor must send back when it saves."""
    from docx import Document

    data = path.read_bytes()
    document = Document(io.BytesIO(data))
    return {"version": version_of(data), "blocks": [block for block, _ in _body_blocks(document)]}


# -- Writing ---------------------------------------------------------------------------------------


def _clean_runs(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise BlocksRefused("A block has no text")
    runs: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("t", ""), str):
            raise BlocksRefused("A block has text that cannot be saved")
        run: dict[str, Any] = {"t": item.get("t", "")}
        for mark in ("b", "i", "u"):
            if item.get(mark):
                run[mark] = True
        link = item.get("link")
        if link:
            if not isinstance(link, str) or not link.lower().startswith(_LINK_SCHEMES):
                raise BlocksRefused("A link must start with http://, https:// or mailto:")
            run["link"] = link
        runs.append(run)
    return _merged(runs)


def _clean(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise BlocksRefused("A block cannot be saved")
    kind = block.get("kind")
    if kind in ("paragraph", "title", "quote"):
        return {"kind": kind, "runs": _clean_runs(block.get("runs"))}
    if kind in ("heading", "bullet", "number"):
        level = block.get("level", 1)
        if not isinstance(level, int) or not 1 <= level <= _MAX_LEVEL:
            raise BlocksRefused("A heading or list level is 1 to 3")
        return {"kind": kind, "level": level, "runs": _clean_runs(block.get("runs"))}
    if kind == "table":
        rows = block.get("rows")
        if (
            not isinstance(rows, list)
            or not rows
            or not all(isinstance(r, list) and r for r in rows)
        ):
            raise BlocksRefused("A table needs rows and columns")
        if len({len(r) for r in rows}) != 1:
            raise BlocksRefused("Every row of a table has the same number of cells")
        return {
            "kind": "table",
            "header": bool(block.get("header")),
            "rows": [[_clean_runs(c) for c in r] for r in rows],
        }
    if kind == "locked" or kind in BREAK_KINDS:
        return {"kind": kind}
    if kind == "image":
        try:
            return {"kind": "image", "blob": decode_picture(block.get("data"))}
        except ValueError as refused:
            raise BlocksRefused(str(refused)) from None
    raise BlocksRefused("A block of an unknown kind cannot be saved")


def _style_for(block: dict[str, Any]) -> str | None:
    kind, level = block["kind"], block.get("level", 1)
    if kind == "title":
        return "Title"
    if kind == "heading":
        return f"Heading {level}"
    if kind == "quote":
        return "Quote"
    if kind in ("bullet", "number"):
        base = "List Bullet" if kind == "bullet" else "List Number"
        return base if level == 1 else f"{base} {level}"
    return None


def _text_element(text: str) -> Any:
    from docx.oxml import OxmlElement

    element = OxmlElement("w:t")
    element.text = text
    element.set(_XML_SPACE, "preserve")
    return element


def _run_element(run: dict[str, Any], *, linked: bool = False) -> Any:
    from docx.oxml import OxmlElement

    element = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    if run.get("b"):
        props.append(OxmlElement("w:b"))
    if run.get("i"):
        props.append(OxmlElement("w:i"))
    if linked:
        colour = OxmlElement("w:color")
        colour.set(_q("val"), _LINK_COLOUR)
        props.append(colour)
    if run.get("u") or linked:
        underline = OxmlElement("w:u")
        underline.set(_q("val"), "single")
        props.append(underline)
    if len(props):
        element.append(props)
    for piece in re.split(r"(\t|\n)", run["t"]):
        if piece == "\t":
            element.append(OxmlElement("w:tab"))
        elif piece == "\n":
            element.append(OxmlElement("w:br"))
        elif piece:
            element.append(_text_element(piece))
    return element


def _run_nodes(document: Any, runs: list[dict[str, Any]]) -> list[Any]:
    from docx.opc.constants import RELATIONSHIP_TYPE
    from docx.oxml import OxmlElement

    nodes = []
    for run in runs:
        if not run.get("link"):
            nodes.append(_run_element(run))
            continue
        relation = document.part.relate_to(
            run["link"], RELATIONSHIP_TYPE.HYPERLINK, is_external=True
        )
        link = OxmlElement("w:hyperlink")
        link.set(f"{{{_R}}}id", relation)
        link.set(_q("history"), "1")
        link.append(_run_element(run, linked=True))
        nodes.append(link)
    return nodes


def _set_runs(document: Any, paragraph: Any, runs: list[dict[str, Any]]) -> None:
    """Replaces a paragraph's runs; its properties, bookmarks and the rest stay where they are."""
    modelled = [c for c in paragraph if _local(c) in ("r", "hyperlink", "proofErr")]
    position = (
        paragraph.index(modelled[0])
        if modelled
        else (1 if paragraph.find(_q("pPr")) is not None else 0)
    )
    for child in modelled:
        paragraph.remove(child)
    for offset, node in enumerate(_run_nodes(document, runs)):
        paragraph.insert(position + offset, node)


def _apply_kind(document: Any, paragraph: Any, block: dict[str, Any], after_number: bool) -> None:
    from docx.text.paragraph import Paragraph

    from ._structure import _restarted_numbering

    properties = paragraph.find(_q("pPr"))
    if properties is not None:
        for stale in properties.findall(_q("numPr")):
            properties.remove(stale)
    wrapper = Paragraph(paragraph, document.part)
    name = _style_for(block)
    try:
        wrapper.style = name if name else "Normal"
    except KeyError as error:
        raise BlocksRefused(f"This document has no {name!r} style") from error
    if block["kind"] == "number" and not after_number:
        number = _restarted_numbering(document, wrapper)
        if number is not None:
            paragraph.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = number


def _new_table(document: Any, block: dict[str, Any]) -> Any:
    from docx.oxml.table import CT_Tbl

    from ._xml import _fill_docx_table

    blank = [["" for _ in row] for row in block["rows"]]
    _fill_docx_table(document, Block(kind="table", rows=blank, header=block["header"]))
    table = next(c for c in reversed(document.element.body) if isinstance(c, CT_Tbl))
    _write_cells(document, table, block["rows"], None)
    return table


def _cell_paragraph(cell: Any) -> Any:
    return cell.find(_q("p"))


def _write_cells(
    document: Any, table: Any, rows: list[list[list[dict[str, Any]]]], old: list[list[Any]] | None
) -> None:
    for r, row in enumerate(table.findall(_q("tr"))):
        for c, cell in enumerate(row.findall(_q("tc"))):
            if old is None or r >= len(old) or c >= len(old[r]) or old[r][c] != rows[r][c]:
                _set_runs(document, _cell_paragraph(cell), rows[r][c])


def _resize_table(table: Any, rows: int, columns: int) -> None:
    trs = table.findall(_q("tr"))
    for extra in trs[rows:]:
        table.remove(extra)
    for _ in range(rows - len(trs)):
        last = table.findall(_q("tr"))[-1]
        last.addnext(copy.deepcopy(last))
    for row in table.findall(_q("tr")):
        cells = row.findall(_q("tc"))
        for extra in cells[columns:]:
            row.remove(extra)
        for _ in range(columns - len(cells)):
            last = row.findall(_q("tc"))[-1]
            last.addnext(copy.deepcopy(last))
    grid = table.find(_q("tblGrid"))
    if grid is not None:
        cols = grid.findall(_q("gridCol"))
        for extra in cols[columns:]:
            grid.remove(extra)
        for _ in range(columns - len(cols)):
            grid.append(copy.deepcopy(grid.findall(_q("gridCol"))[-1]))


def _update(
    document: Any, old: dict[str, Any], element: Any, block: dict[str, Any], after_number: bool
) -> Any:
    if old["kind"] == "locked":
        return element
    if old["kind"] in BREAK_KINDS or block["kind"] in BREAK_KINDS:
        return element if old["kind"] == block["kind"] else _create(document, block, after_number)
    if (old["kind"] == "table") != (block["kind"] == "table"):
        return _create(document, block, after_number)
    if block["kind"] == "table":
        shape = (len(old["rows"]), len(old["rows"][0]))
        if shape != (len(block["rows"]), len(block["rows"][0])):
            _resize_table(element, len(block["rows"]), len(block["rows"][0]))
            _write_cells(document, element, block["rows"], None)
        else:
            _write_cells(document, element, block["rows"], old["rows"])
        return element
    if (old["kind"], old.get("level")) != (block["kind"], block.get("level")):
        _apply_kind(document, element, block, after_number)
    if old["runs"] != block["runs"]:
        _set_runs(document, element, block["runs"])
    return element


def _create(document: Any, block: dict[str, Any], after_number: bool) -> Any:
    if block["kind"] == "image":
        return new_picture_paragraph(document, block["blob"])
    if block["kind"] in BREAK_KINDS:
        return new_break_paragraph(block["kind"])
    if block["kind"] == "table":
        return _new_table(document, block)
    from docx.oxml import OxmlElement

    paragraph = OxmlElement("w:p")
    _apply_kind(document, paragraph, block, after_number)
    _set_runs(document, paragraph, block["runs"])
    return paragraph


def save_doc_blocks(path: Path, version: str, submitted: list[Any]) -> dict[str, Any]:
    """Writes the blocks the person changed, the new ones and the deletions, in the order given;
    what it does not touch stays as it is. Refused with `DocChanged` over a newer file."""
    from docx import Document

    cleaned = [
        (block.get("id") if isinstance(block, dict) else None, _clean(block)) for block in submitted
    ]
    with file_lock(path):
        data = path.read_bytes()
        if version_of(data) != version:
            raise DocChanged
        document = Document(io.BytesIO(data))
        current = _body_blocks(document)
        by_id = {block["id"]: (block, element) for block, element in current}
        ordered: list[Any] = []
        used: set[str] = set()
        previous = ""
        for block_id, block in cleaned:
            after_number = previous == "number"
            if (
                block["kind"] != "image"
                and isinstance(block_id, str)
                and block_id in by_id
                and block_id not in used
            ):
                used.add(block_id)
                old, element = by_id[block_id]
                ordered.append(_update(document, old, element, block, after_number))
            elif block["kind"] != "locked":
                ordered.append(_create(document, block, after_number))
            else:
                continue
            previous = block["kind"]
        body = document.element.body
        for _, element in current:
            body.remove(element)
        section = body.find(_q("sectPr"))
        for element in ordered:
            if section is not None:
                section.addprevious(element)
            else:
                body.append(element)
        assert_wml_valid(document.element, "docs editor")
        out = io.BytesIO()
        document.save(out)
        write_atomically(path, out.getvalue())
    return read_doc_blocks(path)
