"""A Doc (decision 0025) read as blocks and changed one block at a time.

A Doc is a markdown file marked `coscribe: doc` in its front matter. Each block keeps the lines it
covers, and an edit rewrites only those lines: a person's save never reformats what coscribe
wrote, and coscribe's next edit applies to text that is still there. A block that changed since the
caller read it is refused, as a Word file saved since the model last read it is (decision 0019).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

MARKER_KEY = "coscribe"
MARKER_VALUE = "doc"
CALLOUTS = ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION")

_CALLOUT = re.compile(rf"^>\s*\[!({'|'.join(CALLOUTS)})\]\s*$", re.IGNORECASE)
_KINDS = {
    "heading_open": "heading",
    "paragraph_open": "paragraph",
    "bullet_list_open": "list",
    "ordered_list_open": "list",
    "table_open": "table",
    "blockquote_open": "quote",
    "hr": "rule",
    "html_block": "html",
    "code_block": "code",
    "fence": "code",
}


class NotADoc(ValueError):
    """The file has no `coscribe: doc` marker, so it is not one of the app's documents."""


class BlocksRefused(ValueError):
    """An edit that cannot be applied; the text says why and is safe to show."""


@dataclass(frozen=True)
class Block:
    index: int
    kind: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Doc:
    meta: dict[str, Any]
    blocks: list[Block]
    body_start: int
    source: str = field(repr=False)


@dataclass(frozen=True)
class Replace:
    index: int
    expected: str
    text: str


@dataclass(frozen=True)
class Insert:
    after: int
    text: str


@dataclass(frozen=True)
class Delete:
    index: int
    expected: str


Edit = Replace | Insert | Delete


def _front_matter(lines: list[str]) -> tuple[dict[str, Any], int]:
    """The head's values and how many lines it takes; none when the file does not open with one."""
    if not lines or lines[0].strip().lstrip("﻿") != "---":
        return {}, 0
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            import yaml

            try:
                head = yaml.safe_load("".join(lines[1:end])) or {}
            except yaml.YAMLError:
                return {}, 0
            return (head if isinstance(head, dict) else {}), end + 1
    return {}, 0


def is_doc(source: str) -> bool:
    meta, _ = _front_matter(source.splitlines(keepends=True))
    return str(meta.get(MARKER_KEY, "")).lower() == MARKER_VALUE


def _block_text(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start:end]).rstrip("\r\n")


def _kind(token: Any, lines: list[str], start: int, end: int) -> str:
    kind = _KINDS[token.type]
    if kind == "quote" and _CALLOUT.match(lines[start].strip()):
        return "callout"
    if token.type == "fence" and token.info.strip().split(" ")[0].lower() == "chart":
        return "chart"
    if kind == "code" and end <= start:
        return "other"
    return kind


def _parse_blocks(lines: list[str], body_start: int) -> list[Block]:
    from markdown_it import MarkdownIt

    tokens = MarkdownIt("commonmark").enable("table").parse("".join(lines[body_start:]))
    found: list[tuple[int, int, str]] = []
    for token in tokens:
        if token.level != 0 or not token.map or token.nesting < 0 or token.type not in _KINDS:
            continue
        start, end = body_start + token.map[0], body_start + token.map[1]
        # A list's range runs on over the blank lines after it; they separate blocks, not belong.
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        found.append((start, end, _kind(token, lines, start, end)))
    covered = {n for start, end, _ in found for n in range(start, end)}
    # Lines markdown-it consumes without a token (a link reference definition) are still the
    # person's text: they become a block of their own, so no non-blank line is ever outside one.
    run: list[int] = []
    for n in range(body_start, len(lines)):
        if n not in covered and lines[n].strip():
            run.append(n)
            continue
        if run:
            found.append((run[0], run[-1] + 1, "other"))
            run = []
    if run:
        found.append((run[0], run[-1] + 1, "other"))
    found.sort()
    return [Block(i, kind, s, e, _block_text(lines, s, e)) for i, (s, e, kind) in enumerate(found)]


def read_doc(source: str, *, require_marker: bool = True) -> Doc:
    lines = source.splitlines(keepends=True)
    meta, body_start = _front_matter(lines)
    if require_marker and str(meta.get(MARKER_KEY, "")).lower() != MARKER_VALUE:
        raise NotADoc("This file is not a Doc")
    return Doc(meta, _parse_blocks(lines, body_start), body_start, source)


def _eol(source: str) -> str:
    return "\r\n" if "\r\n" in source else "\n"


def _as_lines(text: str, eol: str) -> list[str]:
    plain = text.replace("\r\n", "\n").rstrip("\n")
    return [line + eol for line in plain.split("\n")]


def _check_expected(block: Block, expected: str) -> None:
    if block.text != expected:
        raise BlocksRefused(f"Block {block.index} changed since it was read")


def _blank_run_after(lines: list[str], end: int) -> int:
    while end < len(lines) and not lines[end].strip():
        end += 1
    return end


def _ranges(doc: Doc, edits: list[Edit]) -> list[tuple[int, int, list[str]]]:
    """Each edit as the lines it replaces (start, end) and the lines that take their place."""
    lines = doc.source.splitlines(keepends=True)
    eol = _eol(doc.source)
    blocks = doc.blocks
    changed: set[int] = set()
    deleted: set[int] = set()
    ranges: list[tuple[int, int, list[str]]] = []
    for edit in edits:
        index = edit.after if isinstance(edit, Insert) else edit.index
        if not -1 <= index < len(blocks) or (index == -1 and not isinstance(edit, Insert)):
            raise BlocksRefused(f"There is no block {index}")
        if isinstance(edit, Insert):
            continue
        if index in changed:
            raise BlocksRefused(f"Block {index} is edited twice in one save")
        changed.add(index)
        _check_expected(blocks[index], edit.expected)
        block = blocks[index]
        if isinstance(edit, Replace):
            tail = lines[block.end - 1][len(lines[block.end - 1].rstrip("\r\n")) :]
            new = _as_lines(edit.text, eol)
            new[-1] = new[-1].rstrip("\r\n") + tail
            ranges.append((block.start, block.end, new))
        else:
            deleted.add(index)
            last = index == len(blocks) - 1
            start = block.start
            while last and start > 0 and not lines[start - 1].strip():
                start -= 1
            stop = block.end if last else _blank_run_after(lines, block.end)
            ranges.append((start if last and start > doc.body_start else block.start, stop, []))
    for edit in edits:
        if not isinstance(edit, Insert):
            continue
        if edit.after in deleted:
            raise BlocksRefused(f"Block {edit.after} is deleted in the same save")
        position = blocks[edit.after].end if edit.after >= 0 else doc.body_start
        new = _as_lines(edit.text, eol)
        if edit.after >= 0:
            before = [] if lines[position - 1].endswith("\n") else [eol]
            new = [*before, eol, *new]
        if position < len(lines) and lines[position].strip():
            new = [*new, eol]
        elif edit.after < 0 and position < len(lines):
            new = [*new, eol] if blocks and blocks[0].start == position else new
        ranges.append((position, position, new))
    return ranges


def apply_edits(source: str, edits: list[Edit]) -> str:
    """The source with every edit applied, or `BlocksRefused` and nothing changed.

    Every edit names the block it means by its index in the read the caller holds, and a replace
    or delete carries the text the caller read there, so an edit that arrives after the block
    changed is refused rather than written over it.
    """
    doc = read_doc(source)
    lines = doc.source.splitlines(keepends=True)
    ranges = _ranges(doc, edits)
    spans = sorted((r for r in ranges if r[0] != r[1]), key=lambda r: r[0])
    for before, after in zip(spans, spans[1:], strict=False):
        if before[1] > after[0]:
            raise BlocksRefused("Two edits touch the same lines")
    # From the bottom up, so the line numbers of the edits still to apply stay true; at one
    # position a replacement goes before the insertion that sits at its first line.
    for start, end, new in sorted(ranges, key=lambda r: (r[0], r[1] != r[0]), reverse=True):
        lines[start:end] = new
    return "".join(lines)
