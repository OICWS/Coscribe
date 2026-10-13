"""Automatic checks on one produced deck, in plain Python: no model is called here.

Each check returns a plain dict so a run can be written as JSON and two runs compared.
`check_deck` runs them all; the pure ones (facts, inventions, page count, the editability
probe) are unit-tested, the render and the layout checks need LibreOffice.
"""

from __future__ import annotations

import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tasks import Task

# A page number, a month or a day is not a claim about the world.
_SMALL_INTEGER = 31
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass
class SlideText:
    title: str
    texts: list[str] = field(default_factory=list)


@dataclass
class Deck:
    slides: list[SlideText]

    def all_text(self) -> str:
        return "\n".join(t for s in self.slides for t in [s.title, *s.texts])


def _leaf_shapes(shapes: Any) -> Any:
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _leaf_shapes(shape.shapes)
        else:
            yield shape


def _chart_texts(chart: Any) -> list[str]:
    texts: list[str] = []
    if chart.has_title:
        texts.append(chart.chart_title.text_frame.text)
    for plot in chart.plots:
        texts.extend(str(c) for c in plot.categories)
        for series in plot.series:
            texts.append(str(series.name))
            texts.extend(f"{v:g}" for v in series.values if v is not None)
    return texts


def read_deck(path: Path) -> Deck:
    """Every piece of text a person would see on each slide, groups, tables and charts included."""
    from pptx import Presentation

    slides: list[SlideText] = []
    for slide in Presentation(str(path)).slides:
        title_shape = slide.shapes.title
        title = title_shape.text_frame.text.strip() if title_shape is not None else ""
        texts: list[str] = []
        for shape in _leaf_shapes(slide.shapes):
            if title_shape is not None and shape.shape_id == title_shape.shape_id:
                continue
            if shape.has_text_frame:
                texts.extend(p.text for p in shape.text_frame.paragraphs if p.text.strip())
            if getattr(shape, "has_table", False) and shape.has_table:
                texts.extend(cell.text for row in shape.table.rows for cell in row.cells)
            if getattr(shape, "has_chart", False) and shape.has_chart:
                texts.extend(_chart_texts(shape.chart))
        slides.append(SlideText(title=title, texts=texts))
    return Deck(slides)


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", folded)


def normalise(text: str) -> str:
    """Fold full-width forms, thousands separators, spacing and case, so that `12,710`,
    `12710` and `１２，７１０` are one number and `Win + L` equals `win+l`."""
    return re.sub(r"\s+", "", _fold(text))


def check_opens(path: Path) -> dict[str, Any]:
    try:
        deck = read_deck(path)
    except Exception as exc:  # noqa: BLE001 -- any failure to open is the finding
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "slides": 0}
    return {"ok": True, "slides": len(deck.slides)}


def check_facts(deck_text: str, facts: list[list[str]], absent: list[str]) -> dict[str, Any]:
    haystack = normalise(deck_text)
    missing = [alts[0] for alts in facts if not any(normalise(a) in haystack for a in alts)]
    still_there = [a for a in absent if normalise(a) in haystack]
    return {
        "ok": not missing and not still_there,
        "found": len(facts) - len(missing),
        "total": len(facts),
        "missing": missing,
        "forbidden_present": still_there,
    }


def _numbers(text: str) -> set[str]:
    # Not `normalise`: removing line breaks would join the numbers of two lines.
    return set(_NUMBER.findall(_fold(text)))


def _is_claim(number: str) -> bool:
    return "." in number or int(number) > _SMALL_INTEGER


def check_inventions(deck: Deck, source_texts: list[str], allowed: list[str]) -> dict[str, Any]:
    """Numbers on slides that appear in no input. A derived figure (a sum, a percentage the
    model computed) is listed too: the list is for a person to read, not a failure."""
    known = _numbers("\n".join(source_texts)) | _numbers("\n".join(allowed))
    found: dict[str, list[int]] = {}
    for number_of_slide, slide in enumerate(deck.slides, start=1):
        for number in _numbers("\n".join([slide.title, *slide.texts])):
            if _is_claim(number) and number not in known:
                found.setdefault(number, []).append(number_of_slide)
    return {
        "count": len(found),
        "numbers": [{"number": n, "slides": s} for n, s in sorted(found.items())],
    }


def check_page_count(count: int, low: int, high: int) -> dict[str, Any]:
    return {"ok": low <= count <= high, "count": count, "expected": [low, high]}


def count_pictures(path: Path) -> int:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    return sum(
        1
        for slide in Presentation(str(path)).slides
        for shape in _leaf_shapes(slide.shapes)
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    )


def check_pictures(count: int, minimum: int) -> dict[str, Any]:
    return {"ok": count >= minimum, "count": count, "minimum": minimum}


def layout_names(path: Path) -> set[str]:
    from pptx import Presentation

    return {layout.name for layout in Presentation(str(path)).slide_layouts}


def check_template_kept(deck_layouts: set[str], template_layouts: set[str]) -> dict[str, Any]:
    """A deck made on the user's template carries the template's layouts; one rebuilt from
    scratch does not."""
    missing = sorted(template_layouts - deck_layouts)
    return {"ok": not missing, "missing_layouts": missing}


def check_editability(path: Path, workspace: Path) -> dict[str, Any]:
    """What coscribe's own tools can do with the deck: every slide must have a title that
    `read_pptx` shows and a shape list that `list_pptx_shapes` returns."""
    from coscribe.tools.presentations import build_presentation_tools

    tools = {t.__name__: t for t in build_presentation_tools(workspace)}
    relative = str(path.relative_to(workspace))
    result: dict[str, Any] = {"untitled_slides": [], "shape_list_errors": []}
    try:
        overview = tools["read_pptx"](path=relative)
    except Exception as exc:  # noqa: BLE001
        return {**result, "ok": False, "error": f"read_pptx: {type(exc).__name__}: {exc}"}
    pages = overview.split("\n\n---\n\n")
    for number, page in enumerate(pages, start=1):
        heading = page.split("\n", 1)[0]
        if not heading.startswith("## ") or not heading[3:].strip():
            result["untitled_slides"].append(number)
    for number in range(1, len(pages) + 1):
        try:
            tools["list_pptx_shapes"](path=relative, slide=number)
        except Exception as exc:  # noqa: BLE001 -- a crash on one slide is what is measured
            result["shape_list_errors"].append(
                {"slide": number, "error": f"{type(exc).__name__}: {exc}"}
            )
    result["ok"] = not result["untitled_slides"] and not result["shape_list_errors"]
    return result


def render_deck(path: Path, out_dir: Path) -> dict[str, Any]:
    """The deck as one PNG per page (`page-01.png`...) through LibreOffice; `pdf` is kept
    for the overflow check."""
    from coscribe.tools._thumbnail import _convert_to_pdf, _render_pdf_pages

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coscribe_eval_") as scratch:
        pdf = _convert_to_pdf(path, Path(scratch))
        if pdf is None:
            return {"ok": False, "reason": "LibreOffice did not produce a PDF", "pages": []}
        kept_pdf = out_dir / "deck.pdf"
        kept_pdf.write_bytes(pdf.read_bytes())
        for old in out_dir.glob("page-*.png"):
            old.unlink()
        try:
            rendered = _render_pdf_pages(pdf, Path(scratch), 1, 10_000)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "pages": []}
        pages = []
        for number, png in enumerate(rendered, start=1):
            target = out_dir / f"page-{number:02d}.png"
            target.write_bytes(png.read_bytes())
            pages.append(target.name)
    return {"ok": True, "pages": pages, "pdf": kept_pdf.name}


def check_layout(path: Path, pdf: Path | None) -> dict[str, Any]:
    """coscribe's own QA functions, as its tools use them after a write."""
    from pptx import Presentation

    from coscribe.tools import presentations as p

    prs = Presentation(str(path))
    overflow = p._check_overflow(pdf) if pdf is not None and pdf.is_file() else None
    overlaps = p._check_text_overlaps(prs)
    low_contrast = p._check_low_contrast(prs)
    plain = p._check_missing_visual_elements(prs)
    return {
        "overflow_words": None if overflow is None else len(overflow),
        "overflow": overflow,
        "text_overlaps": len(overlaps),
        "low_contrast": len(low_contrast),
        "slides_without_visual": plain,
    }


def check_deck(task: Task, path: Path, workspace: Path, out_dir: Path) -> dict[str, Any]:
    """All checks for one deck; a check that cannot run says why instead of failing the rest."""
    report: dict[str, Any] = {"deck": str(path.relative_to(workspace))}
    report["opens"] = check_opens(path)
    if not report["opens"]["ok"]:
        return report
    deck = read_deck(path)
    expect = task.expect
    report["facts"] = check_facts(deck.all_text(), expect.facts, expect.absent)
    report["inventions"] = check_inventions(deck, task.source_texts(), expect.allowed_numbers)
    report["pages"] = check_page_count(len(deck.slides), expect.pages_min, expect.pages_max)
    if expect.pictures_min:
        report["pictures"] = check_pictures(count_pictures(path), expect.pictures_min)
    if expect.template:
        template = next(p for p in task.inputs if p.name == expect.template)
        report["template"] = check_template_kept(layout_names(path), layout_names(template))
    report["editability"] = check_editability(path, workspace)
    report["render"] = render_deck(path, out_dir)
    pdf = out_dir / report["render"]["pdf"] if report["render"]["ok"] else None
    try:
        report["layout"] = check_layout(path, pdf)
    except Exception as exc:  # noqa: BLE001
        report["layout"] = {"error": f"{type(exc).__name__}: {exc}"}
    return report
