"""Writes a parsed spec into a document (decision 0024): the head's cover, contents, header and
footer, the markdown between components through the same writer `write_docx` always used, and each
component through `components.py`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._structure import Written, add_blocks
from ._style import has_cjk
from ._xml import _add_toc, _ChangeIdCounter
from .components import (
    GREY,
    add_callout,
    add_contents_title,
    add_cover,
    add_figure,
    add_stats,
)
from .spec import Component, Spec, SpecError


def _set(target: Any, **properties: Any) -> None:
    """python-docx properties are plain attributes with setters; a name set only here is not
    one the dead-code check can see a read of."""
    for name, value in properties.items():
        setattr(target, name, value)


def _merge(into: Written, part: Written) -> None:
    into.elements += part.elements
    into.tocs += part.tocs
    into.headings += part.headings
    into.comments += part.comments


def _running_text(document: Any, head: dict[str, Any]) -> None:
    """The header line and the footer text; the page number is the house style's footer."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    cover = head.get("cover", "none") != "none"
    for section in document.sections:
        # A cover carries no running text: its own first page has an empty header and footer.
        _set(section, different_first_page_header_footer=cover)
        if cover:
            # Defined and left empty: Word shows nothing there, and so does every other viewer.
            _set(section.first_page_header, is_linked_to_previous=False)
            _set(section.first_page_footer, is_linked_to_previous=False)
        if head.get("header"):
            paragraph = section.header.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = paragraph.add_run(str(head["header"]))
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor.from_string(GREY)
        if head.get("footer"):
            footer = section.footer.paragraphs[0]
            run = footer.runs[0].element if footer.runs else None
            lead = footer.add_run(f"{head['footer']}  |  ")
            lead.font.size = Pt(9)
            lead.font.color.rgb = RGBColor.from_string(GREY)
            if run is not None:
                run.addprevious(lead.element)


def _component(document: Any, component: Component, resolve: Callable[[str], Path]) -> None:
    try:
        if component.name == "stats":
            add_stats(document, component.body)
        elif component.name == "callout":
            kind, _, rest = component.args.partition(" ")
            add_callout(document, kind or "info", component.body or rest)
        elif component.name == "figure":
            add_figure(document, component.args, component.body, resolve)
        elif component.name == "pagebreak":
            document.add_page_break()
    except ValueError as error:
        raise SpecError(str(error)) from None


def add_spec(
    document: Any,
    spec: Spec,
    resolve: Callable[[str], Path],
    change_author: str | None,
    change_ids: _ChangeIdCounter,
) -> Written:
    """Append the spec to the end of the body. Components are final content, never tracked, as
    tables are not."""
    head = spec.head
    if change_author is not None and any(isinstance(i, Component) for i in spec.items):
        raise SpecError(
            "Components cannot be tracked changes: write the document without track_changes"
        )
    cover = head.get("cover", "none")
    if cover != "none" and not head.get("title"):
        raise SpecError("A cover needs a title in the head")
    body = document.element.body
    existing = set(body)
    written = Written()
    if cover != "none":
        add_cover(document, head, cover)
    elif head.get("title"):
        document.add_paragraph(str(head["title"]), style="Title")
    if head.get("toc"):
        add_contents_title(document, has_cjk(str(head.get("title", ""))))
        written.tocs.append(_add_toc(document))
        document.add_page_break()
    for item in spec.items:
        if isinstance(item, str):
            _merge(written, add_blocks(document, item, change_author, change_ids))
        else:
            _component(document, item, resolve)
    _running_text(document, head)
    written.elements = [child for child in body if child not in existing]
    return written
