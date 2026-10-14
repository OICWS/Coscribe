"""Find and replace text anywhere on a slide (placeholders, text boxes, group members, table
cells), keeping how it looks.

A paragraph's text is split into runs, each with its own font, size and colour, and a phrase can
cross runs ("399" bold, " 元" plain). The match is found in the text of the runs between two line
breaks (or fields, such as a slide number), never across one, so text never moves to another
line; the replacement goes into the run the match starts in, and the matched characters leave
the others, so every character that stays keeps its run's formatting.
"""

from __future__ import annotations

from typing import Any

from ._pptx_shapes import walk

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def replace_text(
    prs: Any, slide: int, find: str, replace: str, remove: bool = False
) -> list[dict[str, object]]:
    """Replace every `find` on slide `slide` (0: every slide); where it was, by slide and shape.
    An empty `replace` deletes only with `remove`: a forgotten argument must not wipe a phrase
    from the whole deck."""
    if not find:
        raise ValueError("find must not be empty.")
    if not replace and not remove:
        raise ValueError("replace is empty: give the new text, or remove=true to delete it.")
    if "\n" in replace or "\v" in replace:
        raise ValueError(
            "replace is one line of text; for several lines or paragraphs give the placeholder's "
            "whole new text with content= instead."
        )
    numbers = range(1, len(prs.slides) + 1) if slide == 0 else [slide]
    found: list[dict[str, object]] = []
    for number in numbers:
        for path, shape in walk(prs.slides[number - 1].shapes):
            if shape.element.tag == f"{_P}grpSp":  # its members are walked on their own
                continue
            count = sum(
                _replace_in_runs(runs, find, replace)
                for paragraph in shape.element.iter(f"{_A}p")
                for runs in _segments(paragraph)
            )
            if count:
                found.append({"slide": number, "shape": path, "name": shape.name, "count": count})
    if not found:
        where = "any slide" if slide == 0 else f"slide {slide}"
        raise ValueError(
            f"{find!r} is not on {where}. read_pptx shows the text as it is (spaces, full-width "
            f"characters, a number's separators, a line break inside the phrase)."
        )
    return found


def _segments(paragraph: Any) -> list[list[Any]]:
    """The paragraph's text runs, split at every line break and field."""
    segments: list[list[Any]] = [[]]
    for child in paragraph:
        if child.tag == f"{_A}r" and child.find(f"{_A}t") is not None:
            segments[-1].append(child.find(f"{_A}t"))
        elif child.tag in (f"{_A}br", f"{_A}fld"):
            segments.append([])
    return [segment for segment in segments if segment]


def _replace_in_runs(runs: list[Any], find: str, replace: str) -> int:
    texts = [run.text or "" for run in runs]
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
