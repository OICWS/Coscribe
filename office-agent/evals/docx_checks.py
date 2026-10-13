"""Deterministic checks of a produced Word document.

Everything is read from the file's XML rather than through python-docx's `paragraph.text`,
which leaves out text inside a tracked insertion. A document is read in two views: *accepted*
(every tracked change applied: what a reader sees after "Accept all") and *rejected* (every
change undone: what "Reject all" gives back, which must equal the input for a redline).
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

from .pptx_checks import check_page_count
from .render import render_pages
from .tasks import DocxExpect, Task
from .text_checks import check_facts, contains, find_inventions, normalise

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {
    "w": W,
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
_EMU_PER_TWIP = 635
_DEFAULT_TEXT_WIDTH_TWIPS = 12240 - 2 * 1440
_FIT_TOLERANCE = 1.01


_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


@dataclass
class Paragraph:
    style: str
    accepted: str
    rejected: str
    has_image: bool
    in_table: bool


@dataclass
class Document:
    paragraphs: list[Paragraph]
    tables: list[dict[str, Any]]
    styles: set[str]
    headers: list[str]
    footers: list[str]
    inserted: int
    deleted: int
    has_toc: bool
    image_widths: list[int]
    text_width: int
    xml: dict[str, etree._Element] = field(default_factory=dict, repr=False)

    def accepted_text(self) -> str:
        return "\n".join(p.accepted for p in self.paragraphs)

    def rejected_text(self) -> str:
        return "\n".join(p.rejected for p in self.paragraphs)


def _inside(node: Any, tag: str, namespace: str = W) -> bool:
    return any(a.tag == f"{{{namespace}}}{tag}" for a in node.iterancestors())


def _text(paragraph: Any, view: str) -> str:
    parts = []
    for node in paragraph.iter(_q("t"), _q("delText"), _q("tab"), _q("br")):
        # A tab stop defined in the paragraph's properties is not a tab the reader sees.
        if _inside(node, "pPr") or (
            node.tag in (_q("tab"), _q("br")) and node.getparent().tag != _q("r")
        ):
            continue
        if node.tag == _q("delText"):
            keep = view == "rejected"
        else:
            keep = not (_inside(node, "del") if view == "accepted" else _inside(node, "ins"))
        if keep:
            is_text = node.tag in (_q("t"), _q("delText"))
            parts.append((node.text or "") if is_text else " ")
    return "".join(parts)


def _style_names(styles_root: Any) -> dict[str, str]:
    names = {}
    for style in styles_root.iter(_q("style")):
        name = style.find(_q("name"))
        if name is not None:
            names[style.get(_q("styleId"))] = name.get(_q("val")).lower()
    return names


def _parts(archive: zipfile.ZipFile, pattern: str) -> list[etree._Element]:
    return [
        etree.fromstring(archive.read(n))
        for n in sorted(archive.namelist())
        if re.fullmatch(pattern, n)
    ]


def _plain(root: Any) -> str:
    return "\n".join("".join(t.text or "" for t in p.iter(_q("t"))) for p in root.iter(_q("p")))


def _text_width(body: Any) -> int:
    sections = list(body.iter(_q("sectPr")))
    if not sections:
        return _DEFAULT_TEXT_WIDTH_TWIPS
    size, margin = sections[-1].find(_q("pgSz")), sections[-1].find(_q("pgMar"))
    if size is None or margin is None:
        return _DEFAULT_TEXT_WIDTH_TWIPS
    return (
        int(size.get(_q("w"), 12240))
        - int(margin.get(_q("left"), 1440))
        - int(margin.get(_q("right"), 1440))
    )


def read_document(path: Path) -> Document:
    with zipfile.ZipFile(path) as archive:
        body = etree.fromstring(archive.read("word/document.xml"))
        has_styles = "word/styles.xml" in archive.namelist()
        names = (
            _style_names(etree.fromstring(archive.read("word/styles.xml"))) if has_styles else {}
        )
        headers = [_plain(r) for r in _parts(archive, r"word/header\d*\.xml")]
        footers = [_plain(r) for r in _parts(archive, r"word/footer\d*\.xml")]
    paragraphs = []
    for node in body.iter(_q("p")):
        if _inside(node, "Fallback", _MC):
            continue
        style_node = node.find("w:pPr/w:pStyle", NS)
        style_id = style_node.get(_q("val")) if style_node is not None else None
        paragraphs.append(
            Paragraph(
                style=names.get(style_id, "normal") if style_id else "normal",
                accepted=_text(node, "accepted"),
                rejected=_text(node, "rejected"),
                has_image=node.find(".//w:drawing", NS) is not None,
                in_table=_inside(node, "tbl"),
            )
        )
    tables = []
    for table in body.iter(_q("tbl")):
        if _inside(table, "tbl"):
            continue
        rows = table.findall(_q("tr"))
        cells = [[_text(c, "accepted").strip() for c in r.findall(_q("tc"))] for r in rows]
        tables.append(
            {"rows": len(rows), "cols": max((len(r) for r in cells), default=0), "cells": cells}
        )
    instructions = [t.text or "" for t in body.iter(_q("instrText"))]
    instructions += [f.get(_q("instr")) or "" for f in body.iter(_q("fldSimple"))]
    gallery = [g.get(_q("val")) or "" for g in body.iter(_q("docPartGallery"))]
    return Document(
        paragraphs=paragraphs,
        tables=tables,
        styles=set(names.values()),
        headers=headers,
        footers=footers,
        inserted=sum(1 for n in body.iter(_q("ins")) if n.getparent().tag != _q("rPr")),
        deleted=sum(1 for n in body.iter(_q("del")) if n.getparent().tag != _q("rPr")),
        has_toc=any(re.match(r"\s*TOC\b", i) for i in instructions)
        or any("table of contents" in g.lower() for g in gallery),
        image_widths=[int(e.get("cx", 0)) for e in body.iterfind(".//w:drawing//wp:extent", NS)],
        text_width=_text_width(body),
    )


def check_opens(path: Path) -> dict[str, Any]:
    try:
        document = read_document(path)
    except Exception as exc:  # noqa: BLE001 -- a file that cannot be read is the finding
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "paragraphs": len(document.paragraphs)}


_HEADING = re.compile(r"heading (\d)")


def heading_level(style: str) -> int | None:
    if style == "title":
        return 0
    found = _HEADING.fullmatch(style)
    return int(found.group(1)) if found else None


def headings_of(document: Document) -> list[tuple[int, str]]:
    found = []
    for paragraph in document.paragraphs:
        level = heading_level(paragraph.style)
        if level is not None and paragraph.accepted.strip():
            found.append((level, paragraph.accepted.strip()))
    return found


def check_headings(document: Document, wanted: list[dict[str, Any]]) -> dict[str, Any]:
    """The wanted headings, in order, among the document's own heading paragraphs: bold text in
    a Normal paragraph is not a heading a reader can navigate by."""
    have = headings_of(document)
    position, missing = 0, []
    for spec in wanted:
        for index in range(position, len(have)):
            level, text = have[index]
            if level == 0 and spec.get("level") != 0:
                continue
            if contains(text, spec["text"]) and spec.get("level", level) == level:
                position = index + 1
                break
        else:
            missing.append(spec["text"])
    return {
        "ok": not missing,
        "missing_or_out_of_order": missing,
        "found": [f"{'#' * max(level, 1)} {text}" for level, text in have],
    }


def check_toc(document: Document) -> dict[str, Any]:
    return {"ok": document.has_toc}


def check_tables(document: Document, wanted: list[dict[str, Any]]) -> dict[str, Any]:
    """Each wanted table is a different real table of the document, big enough and, when asked,
    with these words in its first row."""
    free = list(range(len(document.tables)))
    missing = []
    for spec in wanted:
        for index in free:
            table = document.tables[index]
            header = " ".join(table["cells"][0]) if table["cells"] else ""
            if (
                table["rows"] >= spec["rows_min"]
                and table["cols"] >= spec["cols_min"]
                and all(contains(header, word) for word in spec.get("header", []))
            ):
                free.remove(index)
                break
        else:
            missing.append(spec)
    return {
        "ok": not missing,
        "found": [(t["rows"], t["cols"]) for t in document.tables],
        "missing": missing,
    }


def check_images(document: Document, minimum: int, fit: bool) -> dict[str, Any]:
    limit = document.text_width * _EMU_PER_TWIP * _FIT_TOLERANCE
    too_wide = [w for w in document.image_widths if w > limit] if fit else []
    return {
        "ok": len(document.image_widths) >= minimum and not too_wide,
        "count": len(document.image_widths),
        "minimum": minimum,
        "wider_than_text_cm": [round(w / 360_000, 1) for w in too_wide],
    }


def check_captions(document: Document, wanted: list[dict[str, Any]]) -> dict[str, Any]:
    missing = []
    for spec in wanted:
        style, start = str(spec["style"]).lower(), normalise(str(spec["starts_with"]))
        for index, paragraph in enumerate(document.paragraphs):
            if paragraph.style != style or not normalise(paragraph.accepted).startswith(start):
                continue
            if spec.get("below_image") and not (index and document.paragraphs[index - 1].has_image):
                continue
            break
        else:
            missing.append(spec)
    return {"ok": not missing, "missing": missing}


def check_tracked(
    document: Document, spec: dict[str, Any], original: Document | None
) -> dict[str, Any]:
    """The edit is a redline: it has tracked insertions and deletions, and undoing all of them
    leaves the input's text, so nothing was changed without a mark."""
    report: dict[str, Any] = {
        "inserted": document.inserted,
        "deleted": document.deleted,
        "ok": document.inserted >= spec.get("min_ins", 0)
        and document.deleted >= spec.get("min_del", 0),
    }
    if spec.get("rejected_equals_original"):
        if original is None:
            return {**report, "ok": False, "error": "the original could not be read"}
        got = normalise(document.rejected_text())
        want = normalise(original.accepted_text())
        report["rejected_equals_original"] = got == want
        report["ok"] = report["ok"] and got == want
    return report


def check_template(document: Document, original: Document, expect: DocxExpect) -> dict[str, Any]:
    """The user's file is still the base: its styles are defined, its header and footer text is
    there and the text is set in its styles instead of the defaults."""
    problems = []
    lacking = [s for s in expect.styles if s.lower() not in document.styles]
    if lacking:
        problems.append(f"styles no longer defined: {lacking}")
    header, footer = "\n".join(document.headers), "\n".join(document.footers)
    problems += [f"header lacks {w!r}" for w in expect.header_has if not contains(header, w)]
    problems += [f"footer lacks {w!r}" for w in expect.footer_has if not contains(footer, w)]
    used = [p.style for p in document.paragraphs if p.accepted.strip()]
    for name, count in expect.style_uses.items():
        got = used.count(name.lower())
        if got < count:
            problems.append(f"{name!r} used by {got} paragraphs, expected {count}")
    if expect.keep_styles:
        dropped = sorted({p.style for p in original.paragraphs if p.accepted.strip()} - set(used))
        if dropped:
            problems.append(f"styles of the original no longer used: {dropped}")
    return {"ok": not problems, "problems": problems}


_MARKDOWN = (
    (re.compile(r"^\s{0,3}#{1,6}\s+\S"), "heading marker"),
    (re.compile(r"^\s*[-*+]\s+\S"), "bullet marker"),
    (re.compile(r"\*\*[^*\s][^*]*\*\*"), "bold markers"),
    (re.compile(r"^\s*\|?\s*:?-{3,}:?\s*\|"), "table rule"),
    (re.compile(r"^\s*\|.+\|\s*$"), "table row as text"),
    (re.compile(r"`[^`]+`"), "code ticks"),
)


def find_markdown(document: Document) -> dict[str, Any]:
    """Markup typed into the text instead of applied as formatting: the sign of a document
    written by pasting markdown into paragraphs."""
    found = []
    for paragraph in document.paragraphs:
        for pattern, what in _MARKDOWN:
            if pattern.search(paragraph.accepted):
                found.append({"what": what, "text": paragraph.accepted[:60]})
                break
    return {"ok": not found, "found": found[:10], "count": len(found)}


def _guarded(report: dict[str, Any], key: str, check: Any) -> None:
    try:
        report[key] = check()
    except Exception as exc:  # noqa: BLE001 -- the failure is the finding
        report[key] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def check_document(task: Task, path: Path, workspace: Path, out_dir: Path) -> dict[str, Any]:
    """The checks a task's expectations ask for; one that cannot run says why and the rest go on."""
    expect = task.expect
    assert isinstance(expect, DocxExpect)
    report: dict[str, Any] = {"output": str(path.relative_to(workspace))}
    try:
        document = read_document(path)
    except Exception as exc:  # noqa: BLE001 -- a file that cannot be read is the finding
        report["opens"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return report
    report["opens"] = {"ok": True, "paragraphs": len(document.paragraphs)}
    original = None
    if expect.original:
        given = next(p for p in task.inputs if p.name == expect.original)
        try:
            original = read_document(given)
        except Exception as exc:  # noqa: BLE001
            report["original"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    report["facts"] = check_facts(document.accepted_text(), expect.facts, expect.absent)
    paragraphs = [p.accepted for p in document.paragraphs if p.accepted.strip()]
    report["inventions"] = find_inventions(
        paragraphs, task.source_texts(), expect.allowed_numbers, "paragraphs"
    )
    report["markdown"] = find_markdown(document)
    if expect.headings:
        _guarded(report, "headings", lambda: check_headings(document, expect.headings))
    if expect.toc:
        _guarded(report, "toc", lambda: check_toc(document))
    if expect.tables:
        _guarded(report, "tables", lambda: check_tables(document, expect.tables))
    if expect.images_min or expect.image_fit:
        _guarded(
            report, "images", lambda: check_images(document, expect.images_min, expect.image_fit)
        )
    if expect.captions:
        _guarded(report, "captions", lambda: check_captions(document, expect.captions))
    if expect.tracked is not None:
        tracked = expect.tracked
        _guarded(report, "tracked", lambda: check_tracked(document, tracked, original))
    if (
        expect.styles
        or expect.header_has
        or expect.footer_has
        or expect.style_uses
        or expect.keep_styles
    ):
        base = original
        if base is None:
            report["template"] = {"ok": False, "error": "the original could not be read"}
        else:
            _guarded(report, "template", lambda: check_template(document, base, expect))
    _guarded(report, "render", lambda: render_pages(path, out_dir))
    if expect.pages and report["render"].get("ok"):
        count = len(report["render"]["pages"])
        report["pages"] = check_page_count(count, expect.pages[0], expect.pages[1])
    return report
