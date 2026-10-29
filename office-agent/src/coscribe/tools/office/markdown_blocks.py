"""The markdown subset the Word, PDF, PowerPoint and Excel writers share."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")


def _split_table_row(line: str) -> list[str] | None:
    if not (line.startswith("|") and line.endswith("|") and len(line) >= 2):
        return None
    return [cell.strip() for cell in line[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(_SEPARATOR_CELL_RE.match(cell) for cell in cells)


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_NUMBER_RE = re.compile(r"^\d+\.\s+(.*)$")
_TOC_LINE_RE = re.compile(r"^\[TOC\]$", re.IGNORECASE)
_PAGE_BREAK_RE = re.compile(r"^\[PAGE ?BREAK\]$", re.IGNORECASE)
_COMMENT_MARKER_RE = re.compile(r"\s*\{\{comment:\s*(.+?)\}\}\s*$", re.IGNORECASE)


def _extract_comment(text: str) -> tuple[str, str | None]:
    """Split a trailing ``{{comment: ...}}`` marker off a block's text.

    Returns ``(visible_text, comment_text_or_None)``. Only recognized on
    headings/paragraphs/bullets/numbered items -- table cells are taken
    literally, so a marker inside one is not a comment (documented v1
    scope limit, see ``write_docx``'s docstring)."""
    match = _COMMENT_MARKER_RE.search(text)
    if not match:
        return text, None
    return text[: match.start()].rstrip(), match.group(1).strip()


@dataclass
class Block:
    kind: str  # "heading" | "paragraph" | "bullet" | "number" | "table" | "toc" | "pagebreak"
    text: str = ""
    level: int = 1
    ordinal: int = 1
    rows: list[list[str]] = field(default_factory=list)
    header: bool = False
    comment: str | None = None
    new_page: bool = False


def parse_blocks(content: str) -> list[Block]:
    """Parse the shared markdown subset into structured blocks."""
    blocks: list[Block] = []
    paragraph_lines: list[str] = []
    table_rows: list[list[str]] = []
    table_header = False
    number_counter = 0

    def flush_paragraph() -> None:
        text = " ".join(paragraph_lines).strip()
        if text:
            text, comment = _extract_comment(text)
            blocks.append(Block(kind="paragraph", text=text, comment=comment))
        paragraph_lines.clear()

    def flush_table() -> None:
        nonlocal table_header
        if table_rows:
            blocks.append(
                Block(kind="table", rows=[list(row) for row in table_rows], header=table_header)
            )
            table_rows.clear()
        table_header = False

    for raw_line in content.splitlines():
        line = raw_line.strip()

        cells = _split_table_row(line)
        if cells is not None:
            flush_paragraph()
            if not _is_separator_row(cells):
                table_rows.append(cells)
            elif len(table_rows) == 1:
                table_header = True
            continue
        flush_table()

        if not line:
            flush_paragraph()
            number_counter = 0
            continue

        if _TOC_LINE_RE.match(line):
            flush_paragraph()
            number_counter = 0
            blocks.append(Block(kind="toc"))
            continue

        if _PAGE_BREAK_RE.match(line):
            flush_paragraph()
            number_counter = 0
            blocks.append(Block(kind="pagebreak"))
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush_paragraph()
            number_counter = 0
            level = min(len(heading_match.group(1)), 3)
            text, comment = _extract_comment(heading_match.group(2).strip())
            blocks.append(Block(kind="heading", level=level, text=text, comment=comment))
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            flush_paragraph()
            number_counter = 0
            text, comment = _extract_comment(bullet_match.group(1).strip())
            blocks.append(Block(kind="bullet", text=text, comment=comment))
            continue

        number_match = _NUMBER_RE.match(line)
        if number_match:
            flush_paragraph()
            number_counter += 1
            text, comment = _extract_comment(number_match.group(1).strip())
            blocks.append(Block(kind="number", text=text, ordinal=number_counter, comment=comment))
            continue

        number_counter = 0
        paragraph_lines.append(line)

    flush_paragraph()
    flush_table()
    return blocks


# Markers count as formatting only where Markdown says they do: touching
# text on the inside and not glued to a word on the outside, so file names
# and identifiers (sales_2025.csv, snake_case_name, 2*3*4) keep their
# underscores and asterisks. A backslash makes one literal. Chinese has no
# spaces between words, so beside an asterisk only a Latin letter or a digit
# counts as a word: 用*斜体*；is italic.
_INLINE_MARKUP_RE = re.compile(
    r"\\(?P<escaped>[*_`\\])"
    r"|`(?P<code>[^`\n]+)`"
    r"|\[(?P<link_text>[^\]\n]+)\]\((?P<link_url>[^)\s]+)\)"
    r"|\*\*(?P<bold>\S(?:.*?\S)?)\*\*"
    r"|(?<![*A-Za-z0-9\\])\*(?P<italic1>[^\s*](?:[^*]*?[^\s*])?)\*(?![*A-Za-z0-9])"
    r"|(?<![_\w\\])_(?P<italic2>[^\s_](?:[^_]*?[^\s_])?)_(?![_\w])"
)


@dataclass(frozen=True)
class InlineSpan:
    """A piece of a block's text with the one style Markdown gave it."""

    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None


def _span(match: re.Match[str]) -> InlineSpan:
    if match.group("escaped") is not None:
        return InlineSpan(match.group("escaped"))
    if match.group("code") is not None:
        return InlineSpan(match.group("code"), code=True)
    if match.group("link_text") is not None:
        return InlineSpan(match.group("link_text"), link=match.group("link_url"))
    if match.group("bold") is not None:
        return InlineSpan(match.group("bold"), bold=True)
    return InlineSpan(match.group("italic1") or match.group("italic2") or "", italic=True)


def parse_inline_spans(text: str) -> list[InlineSpan]:
    """Split ``**bold**``, ``*italic*``/``_italic_``, `` `code` `` and ``[text](url)`` out of a
    block's text, so a writer styles each piece instead of printing the markers. A lone,
    unterminated marker (a bullet reading "the file *.txt") stays plain text."""
    spans: list[InlineSpan] = []
    pos = 0
    for match in _INLINE_MARKUP_RE.finditer(text):
        if match.start() > pos:
            spans.append(InlineSpan(text[pos : match.start()]))
        spans.append(_span(match))
        pos = match.end()
    if pos < len(text):
        spans.append(InlineSpan(text[pos:]))
    merged: list[InlineSpan] = []
    for span in spans:
        if merged and replace(merged[-1], text="") == replace(span, text=""):
            merged[-1] = replace(span, text=merged[-1].text + span.text)
        else:
            merged.append(span)
    return merged or [InlineSpan(text)]


def parse_inline_runs(text: str) -> list[tuple[str, bool, bool]]:
    """``parse_inline_spans`` as ``(text, bold, italic)`` runs, for a writer that has no code
    font or links: a code span and a link's words are plain text there."""
    runs: list[tuple[str, bool, bool]] = []
    for span in parse_inline_spans(text):
        if runs and runs[-1][1:] == (span.bold, span.italic):
            runs[-1] = (runs[-1][0] + span.text, span.bold, span.italic)
        else:
            runs.append((span.text, span.bold, span.italic))
    return runs
