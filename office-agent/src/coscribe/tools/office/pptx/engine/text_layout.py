"""Where a section's text breaks into lines, and so how tall its box must be.

A section gives each text box its width and height; PowerPoint and the browser then wrap the text
inside that width. Neither can be asked here, so lines are broken the way both do it (at spaces,
between CJK characters, never before closing punctuation), with the per-character advances of the
faces PowerPoint draws in, and a box whose lines need more height than it has is reported.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from ...._native_svg.svg_to_pptx.drawingml.utils import (
    estimate_text_cluster_widths,
    is_cjk_char,
    split_project_text_clusters,
)

# Our advances are PowerPoint's within a few percent, not exactly: breaking a little short of the
# width keeps a line that just fits here from wrapping once more there and overflowing the box.
_WIDTH_MARGIN = 0.97
# Line-break rules (kinsoku) shared by Chinese and Japanese: these never start or end a line.
_NO_LINE_START = set("，。、；：？！）」』》〉】〕’”…—%‰,.;:?!)]}")
_NO_LINE_END = set("（「『《〈【〔‘“([{")


@dataclass(frozen=True)
class Font:
    family: str
    size: float  # px on the 1920-wide canvas
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Run:
    text: str  # "\n" is a line break inside the paragraph
    font: Font
    colour: str = "000000"
    underline: bool = False


@dataclass
class Paragraph:
    runs: list[Run]
    size: float  # the paragraph's own font size, which sets its line spacing
    indent: float = 0.0  # px taken by a bullet or number
    space_before: float = 0.0


@dataclass(frozen=True)
class _Unit:
    """Text that stays on one line: a word, one CJK character with the punctuation tied to it."""

    width: float
    trailing_space: float  # a space after the unit, dropped when the line ends there
    newline: bool = False


def line_count(paragraph: Paragraph, width: float) -> int:
    available = (width - paragraph.indent) * _WIDTH_MARGIN
    lines, used = 1, 0.0
    for unit in _units(paragraph.runs):
        if unit.newline:
            lines, used = lines + 1, 0.0
            continue
        if used and used + unit.width > available:
            lines, used = lines + 1, 0.0
        while unit.width > available and used == 0.0:
            # A word wider than the line: PowerPoint breaks it between letters.
            lines += 1
            unit = _Unit(unit.width - available, unit.trailing_space)
        used += unit.width + unit.trailing_space
    return lines


def text_height(paragraphs: Sequence[Paragraph], width: float, line_height: float) -> float:
    """Px the paragraphs take at `width`, with exact line spacing `line_height` times each
    paragraph's size, as the compiled text box sets it."""
    total = 0.0
    for i, paragraph in enumerate(paragraphs):
        if i:
            total += paragraph.space_before
        total += line_count(paragraph, width) * paragraph.size * line_height
    return total


def _units(runs: Sequence[Run]) -> Iterator[_Unit]:
    width, space, last = 0.0, 0.0, ""
    for run in runs:
        for cluster, advance in _clusters(run):
            if cluster == "\n":
                if width or space:
                    yield _Unit(width, 0.0)
                yield _Unit(0.0, 0.0, newline=True)
                width, space, last = 0.0, 0.0, ""
                continue
            if cluster.isspace():
                space += advance
                continue
            if (width or space) and _breaks_between(last, cluster, bool(space)):
                yield _Unit(width, space)
                width, space = 0.0, 0.0
            width += space + advance
            space, last = 0.0, cluster
    if width or space:
        yield _Unit(width, space)


def _clusters(run: Run) -> Iterator[tuple[str, float]]:
    font = run.font
    for i, part in enumerate(run.text.split("\n")):
        if i:
            yield ("\n", 0.0)
        if part:
            clusters = split_project_text_clusters(part)
            widths = estimate_text_cluster_widths(
                part,
                font.size,
                "700" if font.bold else "400",
                font_family=font.family,
                font_style="italic" if font.italic else "normal",
            )
            yield from zip(clusters, widths, strict=True)


def _breaks_between(before: str, after: str, spaced: bool) -> bool:
    if after[0] in _NO_LINE_START or (before and before[-1] in _NO_LINE_END):
        return False
    if spaced:
        return True
    return _is_cjk(before) or _is_cjk(after)


def _is_cjk(cluster: str) -> bool:
    return any(is_cjk_char(ch) for ch in cluster)
