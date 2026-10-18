"""The Slides panel's changes to a deck's slides as a whole (design §7): a new slide after the
current one, a copy of one, one moved or deleted.

A deck's order is its pages' file names, so each change renames the pages to `NN-name` in their
new order (the name kept, the number new), moves their comments with them and builds the deck
again, under the same lock and refusals as a save of one slide.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...._file_locks import file_lock
from .build import MANIFEST, _read_manifest, _refuse_if_changed, build_deck, page_files
from .history import record_state
from .section_format import parse_section
from .view import NotBuiltFromPages, pages_folder
from .view_comments import move_comments

_NUMBER = re.compile(r"^\d+[-_ ]*")
_MAX_SLIDES = 200

# A new or copied slide: the name it takes (without number), its suffix and its text.
New = tuple[str, str, str]


def insert_slide(deck: Path, after: int, source: str, *, resource_root: Path) -> int:
    """Adds the section `source` as a slide after slide `after` (-1: first). Returns its index."""
    parse_section(source)
    return _arrange(
        deck, resource_root, lambda pages: _put(pages, after + 1, ("slide", ".html", source))
    )


def duplicate_slide(deck: Path, index: int, *, resource_root: Path) -> int:
    """A copy of slide `index` right after it; returns the copy's index."""

    def copy(pages: list[Path | New]) -> int:
        page = _existing(pages, index)
        text = page.read_text(encoding="utf-8")
        return _put(pages, index + 1, (f"{_stem(page)}-copy", page.suffix.lower(), text))

    return _arrange(deck, resource_root, copy)


def move_slide(deck: Path, index: int, to: int, *, resource_root: Path) -> int:
    def move(pages: list[Path | New]) -> int:
        page = _existing(pages, index)
        pages.remove(page)
        to_ = min(max(to, 0), len(pages))
        pages.insert(to_, page)
        return to_

    return _arrange(deck, resource_root, move)


def delete_slide(deck: Path, index: int, *, resource_root: Path) -> int:
    """Removes slide `index` and its comments; the last slide of a deck stays. Returns the index
    of the slide shown after it."""

    def delete(pages: list[Path | New]) -> int:
        if len(pages) == 1:
            raise ValueError("a deck keeps at least one slide")
        pages.remove(_existing(pages, index))
        return min(index, len(pages) - 1)

    return _arrange(deck, resource_root, delete)


def _arrange(deck: Path, resource_root: Path, change: Any) -> int:
    with file_lock(deck):
        folder = pages_folder(deck)
        if folder is None:
            raise NotBuiltFromPages(f"{deck.name} was not built from pages")
        _refuse_if_changed(deck, _read_manifest(folder / MANIFEST))
        before = page_files(folder, (".svg", ".html"))
        record_state(folder, before, "coscribe")
        pages: list[Path | New] = list(before)
        index = change(pages)
        if len(pages) > _MAX_SLIDES:
            raise ValueError(f"a deck holds {_MAX_SLIDES} slides at most")
        renamed = _write(folder, pages, before)
        move_comments(deck, renamed)
        build_deck(folder, deck, resource_root=resource_root, recorded_as="you")
    return int(index)


def _write(folder: Path, pages: list[Path | New], before: list[Path]) -> dict[str, str | None]:
    """Renames every page to its new number through a temporary name (two pages may swap
    numbers) and writes the new ones. Returns old slide name to new, None for one deleted."""
    width = max(2, len(str(len(pages))))
    targets: list[tuple[Path | New, Path]] = []
    for number, page in enumerate(pages, start=1):
        name, suffix = (page.stem, page.suffix) if isinstance(page, Path) else page[:2]
        stem = _NUMBER.sub("", name) or "slide"
        targets.append((page, folder / f"{number:0{width}d}-{stem}{suffix.lower()}"))
    renamed: dict[str, str | None] = {page.stem: None for page in before}
    moving = [(page, target) for page, target in targets if isinstance(page, Path)]
    staged = []
    for i, (page, target) in enumerate(moving):
        temporary = folder / f".arranging-{i}{page.suffix}"
        page.rename(temporary)
        staged.append((temporary, target))
        renamed[page.stem] = target.stem
    for page in before:
        if renamed[page.stem] is None:
            page.unlink()
    for temporary, target in staged:
        temporary.rename(target)
    for page, target in targets:
        if not isinstance(page, Path):
            target.write_text(page[2], encoding="utf-8")
    return renamed


def _put(pages: list[Path | New], at: int, new: New) -> int:
    at = min(max(at, 0), len(pages))
    pages.insert(at, new)
    return at


def _existing(pages: list[Path | New], index: int) -> Path:
    if not 0 <= index < len(pages):
        raise IndexError(f"no slide {index + 1}")
    page = pages[index]
    if not isinstance(page, Path):
        raise IndexError(f"slide {index + 1} is not written yet")
    return page


def _stem(page: Path) -> str:
    return _NUMBER.sub("", page.stem) or "slide"
