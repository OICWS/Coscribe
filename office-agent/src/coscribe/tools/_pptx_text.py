"""Find and replace text anywhere on a slide (placeholders, text boxes, group members, table
cells), keeping how it looks.

A paragraph's text is split into runs, each with its own font, size and colour, and a phrase can
cross runs ("399" bold, " 元" plain). The match is found in the paragraph's whole text; the
replacement goes into the run the match starts in, and the matched characters leave the others,
so every character that stays keeps its run's formatting.
"""

from __future__ import annotations

from typing import Any

from ._pptx_shapes import walk


def replace_text(prs: Any, slide: int, find: str, replace: str) -> list[dict[str, object]]:
    """Replace every `find` on slide `slide` (0: every slide); where it was, by slide and shape."""
    if not find:
        raise ValueError("find must not be empty.")
    numbers = range(1, len(prs.slides) + 1) if slide == 0 else [slide]
    found: list[dict[str, object]] = []
    for number in numbers:
        for path, shape in walk(prs.slides[number - 1].shapes):
            count = sum(
                _replace_in_paragraph(paragraph, find, replace)
                for frame in _frames(shape)
                for paragraph in frame.paragraphs
            )
            if count:
                found.append({"slide": number, "shape": path, "name": shape.name, "count": count})
    if not found:
        where = "any slide" if slide == 0 else f"slide {slide}"
        raise ValueError(
            f"{find!r} is not on {where}. read_pptx shows the text as it is (spaces, full-width "
            f"characters, a number's separators)."
        )
    return found


def _frames(shape: Any) -> list[Any]:
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        return [shape.text_frame]
    if getattr(shape, "has_table", False) and shape.has_table:
        return [cell.text_frame for row in shape.table.rows for cell in row.cells]
    return []


def _replace_in_paragraph(paragraph: Any, find: str, replace: str) -> int:
    runs = list(paragraph.runs)
    texts = [run.text for run in runs]
    text = "".join(texts)
    starts = []
    at = text.find(find)
    while at != -1:
        starts.append(at)
        at = text.find(find, at + len(find))
    if not starts:
        return 0
    owner = [index for index, part in enumerate(texts) for _ in part]
    rebuilt = [""] * len(runs)
    position, pending = 0, iter(starts)
    next_match = next(pending, None)
    while position < len(text):
        if position == next_match:
            rebuilt[owner[position]] += replace
            position += len(find)
            next_match = next(pending, None)
        else:
            rebuilt[owner[position]] += text[position]
            position += 1
    for run, new_text in zip(runs, rebuilt, strict=True):
        run.text = new_text
    return len(starts)
