"""An edit the person makes to one element of an artboard's page from the canvas's properties panel,
written into the page's own source, and the note that tells coscribe about it at its next turn.

The element is found by the path the inspector gives (child indexes from the body,
`board_inspector.js`), counted over the source as the browser builds it for a well-formed page.
Only that element's style attribute or text is rewritten; every other byte of the file stays as
coscribe wrote it, so its formatting and its `var(--…)` references survive. A page the browser
repairs (an unclosed tag, an implied body) can count differently, so the element's tag and text
are checked before anything is written.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path

from .design_canvas import PART_SUFFIX, canvas_of_page

# A property name as CSS writes one, custom properties (`--brand`) included: nothing that could
# end the declaration or the attribute.
_PROPERTY = re.compile(r"(?:--)?-?[a-z][a-z0-9-]{0,60}")
_VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}  # fmt: skip
# What a browser keeps in the head when the page gives no head or body tags.
_HEAD = {"title", "meta", "link", "style", "script", "base", "noscript", "template"}
# A value goes into a style attribute: nothing that could end the declaration or the attribute,
# open a comment, or break out of the tag.
_VALUE = re.compile(r"(?!.*/\*)[^;{}<>\\\"]{1,200}")
_STYLE_ATTR = re.compile(r"""\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_EDITS_FOLDER = "design_edits"
_MAX_TOLD = 12


class BoardEditError(ValueError):
    """An edit that cannot be made, and why."""


class BoardElementChanged(BoardEditError):
    """The element picked in the panel is no longer where, or what, the source has."""


class _Element:
    def __init__(self, tag: str, start: int, start_end: int) -> None:
        self.tag = tag
        self.start = start
        self.start_end = start_end
        self.end: int | None = None
        self.children = 0
        self.has_element_child = False


# A comment, a doctype or processing instruction, or a tag with its attributes (quoted values may
# hold ">"). The text inside script and style is skipped whole, as the browser reads it.
_TOKEN = re.compile(
    r"<!--.*?-->|<![^>]*>|<\?[^>]*>"
    r"|<(/?)([A-Za-z][\w:-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*)>",
    re.DOTALL,
)
_RAW_TEXT = {"script", "style", "textarea", "title"}


class _Locator:
    """Walks the source's tags and keeps, for the element at `path`, where its start tag and its
    content lie."""

    def __init__(self, path: list[int], *, fragment: bool = False) -> None:
        self.want = path
        self.stack: list[tuple[_Element, list[int] | None]] = []
        self.found: _Element | None = None
        self.body_seen = fragment
        # Without a body tag the browser makes one at the first element a head cannot hold; the
        # top-level elements from there on are its children. A part's file is filled into its
        # placing element whole, so every top-level element of it, a style too, is a child.
        self.implied: _Element | None = _Element("part", 0, 0) if fragment else None

    def walk(self, source: str) -> None:
        at = 0
        while (token := _TOKEN.search(source, at)) is not None:
            at = token.end()
            if token.group(2) is None:
                continue
            tag = token.group(2).lower()
            if token.group(1):
                self._end(tag, token.start())
                continue
            self._start(tag, token.start(), token.end(), token.group(3).rstrip().endswith("/"))
            if tag in _RAW_TEXT:
                close = re.compile(rf"</{tag}\s*>", re.IGNORECASE).search(source, at)
                at = close.start() if close else len(source)

    def _start(self, tag: str, start: int, start_end: int, self_closing: bool) -> None:
        element = _Element(tag, start, start_end)
        where: list[int] | None = None
        top = not self.stack or [e.tag for e, _ in self.stack] == ["html"]
        if top and not self.body_seen and tag not in _HEAD and tag not in ("html", "head", "body"):
            self.body_seen = True
            self.implied = _Element("body", start, start)
        if tag == "body" and not self.body_seen:
            self.body_seen = True
            where = []
        elif top and self.implied is not None:
            where = [self.implied.children]
            self.implied.has_element_child = True
            self.implied.children += 1
        elif self.stack:
            parent, parent_where = self.stack[-1]
            parent.has_element_child = True
            if parent_where is not None:
                where = [*parent_where, parent.children]
            parent.children += 1
        if where == self.want and self.found is None:
            self.found = element
        if tag in _VOID or self_closing:
            element.end = element.start_end
            return
        self.stack.append((element, where))

    def _end(self, tag: str, offset: int) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0].tag == tag:
                for element, _ in self.stack[i:]:
                    element.end = offset
                del self.stack[i:]
                return


def _indexes(path: str) -> list[int]:
    try:
        return [int(part) for part in path.split(".")] if path else []
    except ValueError:
        raise BoardEditError(
            "That element's place in the page is not one the panel gives"
        ) from None


def _locate(source: str, indexes: list[int], *, fragment: bool = False) -> _Element:
    locator = _Locator(indexes, fragment=fragment)
    locator.walk(source)
    if not locator.body_seen:
        raise BoardEditError("The page has no body element, so its elements cannot be edited here")
    if locator.found is None or locator.found.end is None:
        raise BoardElementChanged("The page changed since the element was picked; pick it again")
    return locator.found


_PART_NAME = re.compile(r"""\sname\s*=\s*["']?([\w-]{1,64})""", re.IGNORECASE)


def board_edit_file(page: Path, path: str) -> tuple[Path, list[int]]:
    """The file an edit of the element at `path` goes into, and the element's place in it: the
    page itself, or the part a page places when the element is inside it (the served page fills
    the part in, `with_parts`; the page's source holds only the empty element that places it)."""
    indexes = _indexes(path)
    source = page.read_text(encoding="utf-8")
    for end in range(len(indexes), 0, -1):
        locator = _Locator(indexes[:end])
        locator.walk(source)
        if locator.found is None:
            continue
        if locator.found.tag != "coscribe-part":
            break
        name = _PART_NAME.search(source[locator.found.start : locator.found.start_end])
        if end == len(indexes) or name is None:
            raise BoardEditError("A placed part is changed through the elements inside it")
        return page.parent / f"{name.group(1)}{PART_SUFFIX}", indexes[end:]
    return page, indexes


def _collapsed(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", text)).split())


def _with_style(start_tag: str, style: dict[str, str]) -> str:
    """The start tag with these properties set in its style attribute, the others kept."""
    found = _STYLE_ATTR.search(start_tag)
    declarations: dict[str, str] = {}
    if found:
        for part in (found.group(1) or found.group(2) or "").split(";"):
            name, sep, value = part.partition(":")
            if sep and name.strip():
                declarations[name.strip().lower()] = value.strip()
    for name, value in style.items():
        if value:
            declarations[name] = value
        else:
            declarations.pop(name, None)
    written = "; ".join(f"{name}: {value}" for name, value in declarations.items())
    attribute = f' style="{written}"' if written else ""
    if found:
        return start_tag[: found.start()] + attribute + start_tag[found.end() :]
    close = len(start_tag) - (2 if start_tag.endswith("/>") else 1)
    return start_tag[:close].rstrip() + attribute + start_tag[close:]


def edit_board_element(
    page: Path,
    path: str,
    tag: str,
    *,
    style: dict[str, str] | None = None,
    text: str | None = None,
    text_before: str | None = None,
) -> str:
    """Write one element's change into the page (or the part it is in, `board_edit_file`) and say
    what changed, in a line for coscribe. An empty style value removes that property from the
    element's own style."""
    if canvas_of_page(page) is None:
        raise BoardEditError("Only an artboard's page is edited from the canvas")
    style = style or {}
    for name, value in style.items():
        if not _PROPERTY.fullmatch(name):
            raise BoardEditError(f"{name!r} is not a CSS property name")
        if value and not _VALUE.fullmatch(value.strip()):
            raise BoardEditError(f"{value!r} is not a value the panel writes")
    file, indexes = board_edit_file(page, path)
    try:
        source = file.read_text(encoding="utf-8")
    except OSError:
        raise BoardElementChanged(
            "The page changed since the element was picked; pick it again"
        ) from None
    element = _locate(source, indexes, fragment=file is not page)
    if element.tag != tag.lower():
        raise BoardElementChanged("The page changed since the element was picked; pick it again")
    inner = source[element.start_end : element.end]
    said = []
    if style:
        start_tag = _with_style(
            source[element.start : element.start_end], {k: v.strip() for k, v in style.items()}
        )
        source = source[: element.start] + start_tag + source[element.start_end :]
        shift = len(start_tag) - (element.start_end - element.start)
        element.start_end += shift
        assert element.end is not None
        element.end += shift
        said.append(", ".join(f"{k} {v.strip() or '(removed)'}" for k, v in style.items()))
    if text is not None:
        if element.has_element_child:
            raise BoardEditError("Only an element that holds text alone has its text edited here")
        if text_before is not None and _collapsed(inner) != " ".join(text_before.split()):
            raise BoardElementChanged(
                "The page changed since the element was picked; pick it again"
            )
        source = (
            source[: element.start_end] + html.escape(text, quote=False) + source[element.end :]
        )
        said.append(f"text to {text[:60]!r}")
    file.write_text(source, encoding="utf-8")
    return f"<{tag}> {_collapsed(inner)[:40]!r}: {'; '.join(said)}"


def _record(canvas: Path, state_dir: Path) -> Path:
    key = hashlib.sha1(os.path.normcase(str(canvas.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _EDITS_FOLDER / f"{key}.json"


def remember_board_edit(page: Path, said: str, state_dir: Path) -> None:
    """Keep the edit for the next turn's note, under the page's canvas."""
    canvas = canvas_of_page(page)
    if canvas is None:
        return
    record = _record(canvas, state_dir)
    try:
        edits = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        edits = []
    edits.append({"page": page.name, "edit": said})
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(edits, ensure_ascii=False), encoding="utf-8")


def note_board_undo(page: Path, said: str, state_dir: Path, *, redone: bool = False) -> None:
    """An edit undone (or, `redone`, an undo taken back) that coscribe has not been told of cancels
    out of the note; one it was told of is reported, since its page has changed again."""
    canvas = canvas_of_page(page)
    if canvas is None:
        return
    record = _record(canvas, state_dir)
    try:
        edits = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        edits = []
    undone, done = {"page": page.name, "edit": f"undid {said}"}, {"page": page.name, "edit": said}
    cancels, adds = (undone, done) if redone else (done, undone)
    if edits and edits[-1] == cancels:
        edits.pop()
    else:
        edits.append(adds)
    if edits:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(edits, ensure_ascii=False), encoding="utf-8")
    else:
        record.unlink(missing_ok=True)


def board_edits_since_told(canvas: Path, state_dir: Path) -> list[dict[str, str]]:
    """The edits made to this canvas's pages since coscribe was last told; telling forgets them."""
    record = _record(canvas, state_dir)
    try:
        edits = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    record.unlink(missing_ok=True)
    return edits if isinstance(edits, list) else []


def board_edits_line(canvas_path: str, edits: list[dict[str, str]]) -> str:
    shown = [f"{e['page']} {e['edit']}" for e in edits[-_MAX_TOLD:]]
    more = f" and {len(edits) - _MAX_TOLD} earlier" if len(edits) > _MAX_TOLD else ""
    return (
        f"[The user edited the design {canvas_path} in the app since your last turn: "
        f"{'; '.join(shown)}{more}. Read those pages before you change them, and do not write them "
        "again from an older copy.]"
    )
