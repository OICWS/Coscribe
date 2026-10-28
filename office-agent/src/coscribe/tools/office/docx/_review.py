"""A Word file's review: its tracked changes and comment threads, read and
acted on one by one (decision 0014). Works on the package's XML parts
directly, because python-docx knows neither comment threads
(`commentsExtended.xml`) nor single tracked changes."""

from __future__ import annotations

import io
import os
import posixpath
import re
import secrets
import tempfile
import zipfile
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lxml import etree

from ..._ooxml_validate import assert_wml_valid

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
_W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
W = f"{{{_W_NS}}}"
W14 = f"{{{_W14_NS}}}"
W15 = f"{{{_W15_NS}}}"

_DOCUMENT = "word/document.xml"
_COMMENTS = (
    "word/comments.xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
)
_COMMENTS_EX = (
    "word/commentsExtended.xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml",
    "http://schemas.microsoft.com/office/2011/relationships/commentsExtended",
)
_OTHER_CHANGES = ("moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange")
_COMMENT_MARKS = {f"{W}commentRangeStart", f"{W}commentRangeEnd"}
_TEXT_CAP = 400


class _Package:
    """The .docx zip as named parts, with the XML ones parsed on demand."""

    def __init__(self, data: bytes) -> None:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self._entries = {name: z.read(name) for name in z.namelist()}
        self._parsed: dict[str, Any] = {}
        self.document = self.xml(_DOCUMENT)
        if self.document is None:
            raise ValueError("not a Word document: word/document.xml is missing")

    def xml(self, name: str) -> Any:
        if name not in self._parsed:
            raw = self._entries.get(name)
            self._parsed[name] = None if raw is None else etree.fromstring(raw)
        return self._parsed[name]

    def part(self, spec: tuple[str, str, str], root_tag: str, nsmap: dict[str, str]) -> Any:
        """The document's part of this relationship type, created when missing."""
        default_name, content_type, rel_type = spec
        rels = self.xml("word/_rels/document.xml.rels")
        for rel in rels:
            if rel.get("Type") == rel_type and rel.get("TargetMode") != "External":
                name = posixpath.normpath(posixpath.join("word", rel.get("Target", "")))
                found = self.xml(name.lstrip("/"))
                if found is not None:
                    return found
        root = etree.Element(root_tag, nsmap=nsmap)
        self._parsed[default_name] = root
        used = {rel.get("Id") for rel in rels}
        rel_id = next(f"rId{n}" for n in range(1, len(used) + 2) if f"rId{n}" not in used)
        etree.SubElement(
            rels,
            f"{{{_REL_NS}}}Relationship",
            Id=rel_id,
            Type=rel_type,
            Target=posixpath.basename(default_name),
        )
        types = self.xml("[Content_Types].xml")
        etree.SubElement(
            types, f"{{{_CT_NS}}}Override", PartName=f"/{default_name}", ContentType=content_type
        )
        return root

    def existing(self, spec: tuple[str, str, str]) -> Any:
        rels = self.xml("word/_rels/document.xml.rels")
        for rel in rels if rels is not None else []:
            if rel.get("Type") == spec[2] and rel.get("TargetMode") != "External":
                return self.xml(posixpath.normpath(posixpath.join("word", rel.get("Target", ""))))
        return None

    def to_bytes(self) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            names = list(self._entries) + [n for n in self._parsed if n not in self._entries]
            for name in names:
                tree = self._parsed.get(name)
                blob = (
                    etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
                    if tree is not None
                    else self._entries[name]
                )
                z.writestr(name, blob)
        return out.getvalue()


def _text(element: Any, tag: str = "t") -> str:
    return "".join(t.text or "" for t in element.iter(f"{W}{tag}"))


def _cap(text: str) -> str:
    return text if len(text) <= _TEXT_CAP else text[: _TEXT_CAP - 1] + "…"


def _is_heading(paragraph: Any) -> bool:
    style = paragraph.find(f"{W}pPr/{W}pStyle")
    if style is not None and re.match(r"(heading|title)", style.get(f"{W}val", ""), re.I):
        return True
    return paragraph.find(f"{W}pPr/{W}outlineLvl") is not None


def _changes(document: Any) -> Iterator[Any]:
    """Insertions and deletions of text. Those inside `w:rPr` only mark a
    paragraph's end as inserted or deleted, and are counted as other changes."""
    for el in document.iter(f"{W}ins", f"{W}del"):
        if el.getparent().tag != f"{W}rPr":
            yield el


def _comment_threads(pkg: _Package) -> tuple[list[Any], dict[str, dict[str, str]]]:
    """The comments, and for each comment's last paragraph id its
    `commentsExtended` entry (`parent`, `done`)."""
    comments = pkg.existing(_COMMENTS)
    extended = pkg.existing(_COMMENTS_EX)
    entries: dict[str, dict[str, str]] = {}
    for ex in extended if extended is not None else []:
        if ex.tag == f"{W15}commentEx":
            entries[ex.get(f"{W15}paraId", "")] = {
                "parent": ex.get(f"{W15}paraIdParent", ""),
                "done": ex.get(f"{W15}done", "0"),
            }
    return (list(comments.iter(f"{W}comment")) if comments is not None else []), entries


def _last_para_id(comment: Any) -> str:
    paragraphs = comment.findall(f"{W}p")
    return paragraphs[-1].get(f"{W14}paraId", "") if paragraphs else ""


def read_review(data: bytes) -> dict[str, Any]:
    pkg = _Package(data)
    changes: list[dict[str, object]] = []
    anchors: dict[str, list[str]] = {}
    open_ranges: set[str] = set()
    heading = ""
    text_changes = set(_changes(pkg.document))
    for el in pkg.document.iter():
        if el.tag == f"{W}p" and _is_heading(el):
            heading = _text(el)
        elif el in text_changes:
            changes.append(
                {
                    "id": el.get(f"{W}id", ""),
                    "kind": "insert" if el.tag == f"{W}ins" else "delete",
                    "author": el.get(f"{W}author", ""),
                    "date": el.get(f"{W}date", ""),
                    "text": _cap(_text(el, "t" if el.tag == f"{W}ins" else "delText")),
                    "under": heading,
                }
            )
        elif el.tag == f"{W}commentRangeStart":
            open_ranges.add(el.get(f"{W}id", ""))
        elif el.tag == f"{W}commentRangeEnd":
            open_ranges.discard(el.get(f"{W}id", ""))
        elif el.tag == f"{W}t":
            for comment_id in open_ranges:
                anchors.setdefault(comment_id, []).append(el.text or "")
    other = sum(1 for name in _OTHER_CHANGES for _ in pkg.document.iter(f"{W}{name}"))
    other += sum(1 for el in pkg.document.iter(f"{W}ins", f"{W}del") if el not in text_changes)

    comment_elements, entries = _comment_threads(pkg)
    by_para: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    for comment in comment_elements:
        comment_id = comment.get(f"{W}id", "")
        para_id = _last_para_id(comment)
        entry = entries.get(para_id, {})
        item: dict[str, Any] = {
            "id": comment_id,
            "author": comment.get(f"{W}author", ""),
            "initials": comment.get(f"{W}initials", ""),
            "date": comment.get(f"{W}date", ""),
            "text": "\n".join(_text(p) for p in comment.findall(f"{W}p")),
            "anchor": _cap("".join(anchors.get(comment_id, []))),
            "done": entry.get("done") == "1",
            "replies": [],
        }
        parent = by_para.get(entry.get("parent", ""))
        if parent is not None:
            del item["anchor"], item["replies"]
            parent["replies"].append(item)
        else:
            items.append(item)
        if para_id:
            by_para[para_id] = parent if parent is not None else item
    return {"changes": changes, "other_changes": other, "comments": items}


def _keep_comment_marks(el: Any) -> None:
    """Comment anchors inside a change being removed stay in the document,
    or their comments would point at nothing."""
    parent = el.getparent()
    for mark in list(el.iter(*_COMMENT_MARKS, f"{W}commentReference")):
        if mark.tag == f"{W}commentReference":
            mark = mark.getparent()
            if mark.tag != f"{W}r":
                continue
        mark.getparent().remove(mark)
        parent.insert(parent.index(el), mark)


def _unwrap(el: Any) -> None:
    parent = el.getparent()
    at = parent.index(el)
    for child in list(el):
        parent.insert(at, child)
        at += 1
    parent.remove(el)


def _settle(el: Any, accept: bool) -> None:
    keep = (el.tag == f"{W}ins") == accept
    if el.getparent().tag == f"{W}rPr":
        el.getparent().remove(el)
    elif keep:
        for deleted in el.iter(f"{W}delText", f"{W}delInstrText"):
            deleted.tag = f"{W}t" if deleted.tag == f"{W}delText" else f"{W}instrText"
        _unwrap(el)
    else:
        _keep_comment_marks(el)
        el.getparent().remove(el)


def _settle_all(document: Any, accept: bool) -> int:
    found = list(document.iter(f"{W}ins", f"{W}del"))
    for el in found:
        _settle(el, accept)
    return len(found)


def _next_id(pkg: _Package, comments: Any) -> int:
    ids = [
        int(v)
        for root in (pkg.document, comments)
        for e in root.iter()
        if (v := e.get(f"{W}id", "")).isdigit()
    ]
    return max(ids, default=0) + 1


def _new_para_id(pkg: _Package, comments: Any) -> str:
    used = {e.get(f"{W14}paraId") for root in (pkg.document, comments) for e in root.iter(f"{W}p")}
    while True:
        # Word requires paragraph ids below 0x80000000.
        candidate = f"{secrets.randbelow(0x7FFFFFFF) + 1:08X}"
        if candidate not in used:
            return candidate


def _paragraph_text_runs(paragraph: Any) -> list[Any]:
    runs = []
    for run in paragraph.iter(f"{W}r"):
        # A text box's paragraphs sit inside this one's runs, and are searched on their own.
        if next(run.iterancestors(f"{W}p")) is not paragraph:
            continue
        if any(a.tag == f"{W}del" for a in run.iterancestors()):
            continue
        if run.find(f"{W}t") is not None:
            runs.append(run)
    return runs


def _split_run(run: Any, at: int) -> Any:
    """Splits a run of one `w:t` at character `at`; returns the second half."""
    second = deepcopy(run)
    first_t, second_t = run.find(f"{W}t"), second.find(f"{W}t")
    text = first_t.text or ""
    first_t.text, second_t.text = text[:at], text[at:]
    for t in (first_t, second_t):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    run.addnext(second)
    return second


def _splittable(run: Any) -> bool:
    return [c.tag for c in run if c.tag != f"{W}rPr"] == [f"{W}t"]


def _anchor_words(document: Any, words: str) -> tuple[Any, Any]:
    """The first and last run holding exactly `words`, split out of their
    runs where that can be done without losing anything."""
    found = []
    for paragraph in document.iter(f"{W}p"):
        runs = _paragraph_text_runs(paragraph)
        text = "".join(_text(r) for r in runs)
        start = text.find(words)
        while start >= 0:
            found.append((runs, start))
            start = text.find(words, start + 1)
    if len(found) != 1:
        raise ValueError(
            f"the words to comment on appear {len(found)} times in the document; "
            "give a longer passage that appears exactly once"
        )
    runs, start = found[0]
    end = start + len(words)
    first = last = None
    offset = 0
    for run in runs:
        length = len(_text(run))
        run_start, run_end = offset, offset + length
        offset = run_end
        if run_end <= start or run_start >= end:
            continue
        if first is None:
            first = run
            if run_start < start and _splittable(run):
                first = _split_run(run, start - run_start)
                run_start = start
            if first is not run:
                run = first
        last = run
        if run_end > end and _splittable(run):
            _split_run(run, end - run_start)
    return first, last


def _comment_element(comment_id: int, author: str, text: str, para_id: str) -> Any:
    initials = "".join(part[0] for part in author.split()[:2]).upper() or "?"
    comment = etree.Element(f"{W}comment")
    comment.set(f"{W}id", str(comment_id))
    comment.set(f"{W}author", author)
    comment.set(f"{W}date", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    comment.set(f"{W}initials", initials)
    for i, line in enumerate(text.split("\n")):
        p = etree.SubElement(comment, f"{W}p")
        if i == len(text.split("\n")) - 1:
            p.set(f"{W14}paraId", para_id)
        t = etree.SubElement(etree.SubElement(p, f"{W}r"), f"{W}t")
        t.text = line
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return comment


def _reference_run(comment_id: int) -> Any:
    run = etree.Element(f"{W}r")
    etree.SubElement(etree.SubElement(run, f"{W}rPr"), f"{W}rStyle").set(
        f"{W}val", "CommentReference"
    )
    etree.SubElement(run, f"{W}commentReference").set(f"{W}id", str(comment_id))
    return run


def _declaring_w14(pkg: _Package, root: Any) -> Any:
    """The comments part with `w14` declared and marked ignorable, as Word
    writes it, so paragraph ids added to it are valid. lxml cannot add a
    namespace to an existing element, so the root is rebuilt."""
    if root.nsmap.get("w14") == _W14_NS and "w14" in root.get(f"{{{_MC_NS}}}Ignorable", "").split():
        return root
    nsmap = {**root.nsmap, "w14": _W14_NS, "mc": _MC_NS}
    rebuilt = etree.Element(root.tag, nsmap=nsmap, attrib=dict(root.attrib))
    rebuilt.extend(list(root))
    ignorable = root.get(f"{{{_MC_NS}}}Ignorable", "").split()
    rebuilt.set(f"{{{_MC_NS}}}Ignorable", " ".join([*ignorable, "w14"]))
    for name, tree in pkg._parsed.items():
        if tree is root:
            pkg._parsed[name] = rebuilt
    return rebuilt


class _Review:
    """One edit: every operation applied to the parsed parts, then saved once."""

    def __init__(self, data: bytes, author: str) -> None:
        self.pkg = _Package(data)
        self.author = author.strip() or "Coscribe"
        self.comments = _declaring_w14(
            self.pkg, self.pkg.part(_COMMENTS, f"{W}comments", {"w": _W_NS})
        )
        self._extended: Any = None

    @property
    def extended(self) -> Any:
        if self._extended is None:
            self._extended = self.pkg.part(
                _COMMENTS_EX,
                f"{W15}commentsEx",
                {"w15": _W15_NS, "mc": _MC_NS},
            )
            self._extended.set(f"{{{_MC_NS}}}Ignorable", "w15")
        return self._extended

    def _change(self, change_id: str) -> list[Any]:
        found = [el for el in _changes(self.pkg.document) if el.get(f"{W}id") == change_id]
        if not found:
            raise ValueError(f"no tracked change with id {change_id}")
        return found

    def _comment(self, comment_id: str) -> Any:
        for comment in self.comments.iter(f"{W}comment"):
            if comment.get(f"{W}id") == comment_id:
                return comment
        raise ValueError(f"no comment with id {comment_id}")

    def _para_id(self, comment: Any) -> str:
        """The id of the comment's last paragraph, which threads key on."""
        paragraphs = comment.findall(f"{W}p")
        if not paragraphs:
            paragraphs = [etree.SubElement(comment, f"{W}p")]
        if not paragraphs[-1].get(f"{W14}paraId"):
            paragraphs[-1].set(f"{W14}paraId", _new_para_id(self.pkg, self.comments))
        return str(paragraphs[-1].get(f"{W14}paraId"))

    def _entry(self, para_id: str) -> Any:
        for ex in self.extended.iter(f"{W15}commentEx"):
            if ex.get(f"{W15}paraId") == para_id:
                return ex
        ex = etree.SubElement(self.extended, f"{W15}commentEx")
        ex.set(f"{W15}paraId", para_id)
        ex.set(f"{W15}done", "0")
        return ex

    def _thread(self, comment_id: str) -> list[Any]:
        """The thread's first comment and its replies."""
        comment = self._comment(comment_id)
        parent = self._entry(self._para_id(comment)).get(f"{W15}paraIdParent")
        if parent:
            comment = next(
                (c for c in self.comments.iter(f"{W}comment") if _last_para_id(c) == parent),
                comment,
            )
        root = self._para_id(comment)
        replies = [
            c
            for c in self.comments.iter(f"{W}comment")
            if c is not comment and self._entry(self._para_id(c)).get(f"{W15}paraIdParent") == root
        ]
        return [comment, *replies]

    def _add_comment(self, text: str) -> tuple[int, str]:
        if not text.strip():
            raise ValueError("a comment needs text")
        comment_id = _next_id(self.pkg, self.comments)
        para_id = _new_para_id(self.pkg, self.comments)
        self.comments.append(_comment_element(comment_id, self.author, text, para_id))
        return comment_id, para_id

    def apply(self, op: dict[str, Any]) -> str:
        kind = op.get("op")
        if kind in ("accept", "reject"):
            change_id = str(op.get("change", ""))
            for el in self._change(change_id):
                _settle(el, kind == "accept")
            return f"{kind}ed change {change_id}"
        if kind in ("accept_all", "reject_all"):
            count = _settle_all(self.pkg.document, kind == "accept_all")
            return f"{kind.replace('_all', 'ed')} {count} changes"
        if kind in ("resolve", "reopen"):
            for comment in self._thread(str(op.get("comment", ""))):
                self._entry(self._para_id(comment)).set(
                    f"{W15}done", "1" if kind == "resolve" else "0"
                )
            return f"{'resolved' if kind == 'resolve' else 'reopened'} comment {op.get('comment')}"
        if kind == "reply":
            return self._reply(str(op.get("comment", "")), str(op.get("text", "")))
        if kind == "comment":
            return self._comment_on(str(op.get("on", "")), str(op.get("text", "")))
        raise ValueError(
            f"unknown op {kind!r}: use accept, reject, accept_all, reject_all, "
            "reply, resolve, reopen or comment"
        )

    def _reply(self, parent_id: str, text: str) -> str:
        root = self._thread(parent_id)[0]
        root_id = root.get(f"{W}id")
        root_para = self._para_id(root)
        comment_id, para_id = self._add_comment(text)
        self._entry(para_id).set(f"{W15}paraIdParent", root_para)
        marks = {
            el.tag: el
            for el in self.pkg.document.iter(*_COMMENT_MARKS, f"{W}commentReference")
            if el.get(f"{W}id") == root_id
        }
        for tag in _COMMENT_MARKS:
            if tag in marks:
                mark = etree.Element(tag)
                mark.set(f"{W}id", str(comment_id))
                marks[tag].addnext(mark)
        reference = marks.get(f"{W}commentReference")
        if reference is not None and reference.getparent().tag == f"{W}r":
            reference.getparent().addnext(_reference_run(comment_id))
        return f"replied to comment {root_id} as comment {comment_id}"

    def _comment_on(self, words: str, text: str) -> str:
        if not words:
            raise ValueError('a new comment needs "on": the words it is about')
        first, last = _anchor_words(self.pkg.document, words)
        comment_id, para_id = self._add_comment(text)
        self._entry(para_id)
        start = etree.Element(f"{W}commentRangeStart")
        start.set(f"{W}id", str(comment_id))
        first.addprevious(start)
        end = etree.Element(f"{W}commentRangeEnd")
        end.set(f"{W}id", str(comment_id))
        last.addnext(end)
        end.addnext(_reference_run(comment_id))
        return f"added comment {comment_id}"

    def finish(self) -> bytes:
        assert_wml_valid(self.pkg.document, "edit_docx_review")
        assert_wml_valid(self.comments, "edit_docx_review comments")
        return self.pkg.to_bytes()


def edit_review(
    data: bytes, operations: list[dict[str, Any]], author: str
) -> tuple[bytes, list[str]]:
    """The file with every operation applied, in order; any failure raises
    before anything is returned, so nothing is half done."""
    if not operations:
        raise ValueError("operations is empty")
    review = _Review(data, author)
    done = []
    for i, op in enumerate(operations):
        try:
            done.append(review.apply(op))
        except ValueError as exc:
            raise ValueError(f"operation {i + 1}: {exc}") from exc
    return review.finish(), done


def write_atomically(path: Path, data: bytes) -> None:
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".coscribe-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
