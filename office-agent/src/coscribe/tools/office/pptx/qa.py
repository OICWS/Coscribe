"""Checks on a finished deck: text past the page edge in a LibreOffice render, leftover placeholder
text, overlapping text boxes, slides with no visual, sparse or cramped layouts, low contrast."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

OVERFLOW_TOLERANCE_PT = 1.0

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType


def check_overflow(pdf_path: Path) -> list[dict[str, object]]:
    """Flag any word whose bounding box crosses the rendered page's edge --
    the LibreOffice-rendered PDF's page size mirrors the pptx slide size, so
    this is a genuine "this text overflows its slide" signal. Pure
    vector/text analysis via pdfplumber (already a dependency); no
    pixel rasterization needed."""
    import pdfplumber

    warnings: list[dict[str, object]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            for word in page.extract_words():
                if (
                    word["x1"] > page.width + OVERFLOW_TOLERANCE_PT
                    or word["bottom"] > page.height + OVERFLOW_TOLERANCE_PT
                ):
                    warnings.append({"slide": index, "text": word["text"]})
    return warnings


# Leftover template/placeholder text write_pptx's own model-written content
# or fill_pptx_template's untouched template shapes (see that tool's own
# "Template slots != source items" docstring paragraph) can leave behind --
# the same class of defect Anthropic's own pptx skill's QA step greps
# `markitdown` output for (`\bx{3,}\b|lorem|ipsum|\bTODO|\[insert`). Kept
# deliberately narrow: real deck content legitimately says "sample" or
# "insert" sometimes (a training deck about "how to insert a chart"), so
# this flags specific, low-false-positive patterns -- literal repeated x's,
# "lorem ipsum", a TODO marker, an unfilled "[insert ...]" bracket, and the
# literal words "placeholder"/"sample text" -- not a broad content-quality
# heuristic.
_PLACEHOLDER_LEFTOVER_RE = re.compile(
    r"\bx{3,}\b|lorem\s+ipsum|\bTODO\b|\[insert|\bplaceholder\b|\bsample\s+text\b",
    re.IGNORECASE,
)


def leftover_placeholder_warnings(prs: PresentationType) -> list[dict[str, object]]:
    """Flag every shape whose text still matches `_PLACEHOLDER_LEFTOVER_RE`.
    Scans every shape on every slide, not just title/body placeholders --
    fill_pptx_template only ever writes into those two, so a template's
    own other, undesigned-for text (a decorative caption, a leftover
    sample stat) never gets touched by that tool at all, and this is the
    QA net that catches it reaching the user's file regardless."""
    warnings: list[dict[str, object]] = []
    for index, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            match = _PLACEHOLDER_LEFTOVER_RE.search(shape.text_frame.text)
            if match:
                warnings.append({"slide": index, "text": match.group(0)})
    return warnings


def shape_bbox(shape: Any) -> tuple[int, int, int, int] | None:
    if shape.left is None or shape.top is None or shape.width is None or shape.height is None:
        return None
    return shape.left, shape.top, shape.width, shape.height


def _bbox_overlap_fraction(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    overlap_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    overlap_h = max(0, min(ay + ah, by + bh) - max(ay, by))
    intersection = overlap_w * overlap_h
    if intersection == 0:
        return 0.0
    smaller_area = min(aw * ah, bw * bh)
    return intersection / smaller_area if smaller_area else 0.0


_TEXT_OVERLAP_THRESHOLD = 0.15


def check_text_overlaps(prs: Any) -> list[dict[str, object]]:
    """Flag pairs of non-empty text shapes on the same slide whose bounding
    boxes overlap significantly -- a purely geometric check that needs no
    rendering (no LibreOffice), so it runs unconditionally.
    Catches a real, reproduced bug directly: `run_node_script`-generated
    scripts sometimes place a subtitle text box at a fixed y-offset that
    overlaps the body content box on some slides but not others (depending
    on how much vertical space the title/eyebrow above it actually took).
    A slight/incidental overlap (rounding, a label brushing a border) isn't
    flagged -- only overlap covering a real fraction of the smaller shape
    is, to avoid false positives from deliberate close spacing.

    Also flags a text shape overlapping a chart or table -- a real,
    live-reproduced defect this check couldn't see before: a chart/table
    is a `GraphicFrame`, not a text-frame shape, so it was invisible to
    the text-vs-text scan above even when its own rendered content (axis
    labels, a chart title, cell text) visually collided with a nearby
    placeholder's text. `add_pptx_chart`'s own positioning now avoids
    this (see its docstring), but this check catches the general case --
    any tool or hand-edit that places a chart/table too close to text."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    warnings: list[dict[str, object]] = []
    for slide_index, slide in enumerate(prs.slides, start=1):
        text_shapes = [
            shape
            for shape in slide.shapes
            if shape.has_text_frame and shape.text_frame.text.strip() and shape_bbox(shape)
        ]
        blocking_shapes = [
            shape
            for shape in slide.shapes
            if shape.shape_type in (MSO_SHAPE_TYPE.CHART, MSO_SHAPE_TYPE.TABLE)
            and shape_bbox(shape)
        ]
        for i, shape_a in enumerate(text_shapes):
            bbox_a = shape_bbox(shape_a)
            assert bbox_a is not None  # filtered above
            for shape_b in text_shapes[i + 1 :]:
                bbox_b = shape_bbox(shape_b)
                assert bbox_b is not None  # filtered above
                if _bbox_overlap_fraction(bbox_a, bbox_b) > _TEXT_OVERLAP_THRESHOLD:
                    warnings.append(
                        {
                            "slide": slide_index,
                            "text_a": shape_a.text_frame.text.strip()[:60],
                            "text_b": shape_b.text_frame.text.strip()[:60],
                        }
                    )
            for blocker in blocking_shapes:
                blocker_bbox = shape_bbox(blocker)
                assert blocker_bbox is not None  # filtered above
                if _bbox_overlap_fraction(bbox_a, blocker_bbox) > _TEXT_OVERLAP_THRESHOLD:
                    warnings.append(
                        {
                            "slide": slide_index,
                            "text_a": shape_a.text_frame.text.strip()[:60],
                            "text_b": f"<{blocker.shape_type} shape>",
                        }
                    )
    return warnings


def _shapes_have_visual_element(shapes: Any) -> bool:
    from pptx.enum.dml import MSO_FILL_TYPE
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    visual_shape_types = {
        MSO_SHAPE_TYPE.PICTURE,
        MSO_SHAPE_TYPE.LINKED_PICTURE,
        MSO_SHAPE_TYPE.CHART,
        MSO_SHAPE_TYPE.TABLE,
        MSO_SHAPE_TYPE.GROUP,
        MSO_SHAPE_TYPE.FREEFORM,
        MSO_SHAPE_TYPE.DIAGRAM,
    }
    visual_fill_types = {
        MSO_FILL_TYPE.SOLID,
        MSO_FILL_TYPE.GRADIENT,
        MSO_FILL_TYPE.PATTERNED,
        MSO_FILL_TYPE.PICTURE,
        MSO_FILL_TYPE.TEXTURED,
    }
    for shape in shapes:
        if shape.shape_type in visual_shape_types:
            return True
        try:
            if shape.fill.type in visual_fill_types:
                return True
        except (AttributeError, TypeError, ValueError):
            continue
    return False


def _slide_has_visual_element(slide: Any) -> bool:
    """A slide "has a visual element" if it does directly, or inherits one
    from its own slide layout or that layout's slide master -- real,
    hand-authored PowerPoint templates commonly put decorative art
    (background graphics, accent bars) on the layout/master rather than
    copying it into every individual slide (that's the whole point of a
    layout/master: shared background art rendered under the slide's own
    content, never literally present in the slide's own shape tree). Only
    non-placeholder shapes count at the layout/master level -- a
    placeholder there is a text-style skeleton, not a visible graphic, so
    it can't satisfy this check on its own. Found live: coscribe's own
    bundled "velis" template (a real third-party design, not one of
    coscribe's python-pptx-built originals) draws its whole curtain-motif
    background as two GROUP shapes on the slide master, which the
    slide-only version of this check couldn't see at all -- a false
    positive, not an actual missing-visual defect."""
    if _shapes_have_visual_element(slide.shapes):
        return True
    layout = slide.slide_layout
    if _shapes_have_visual_element(shape for shape in layout.shapes if not shape.is_placeholder):
        return True
    return _shapes_have_visual_element(
        shape for shape in layout.slide_master.shapes if not shape.is_placeholder
    )


def check_missing_visual_elements(prs: Any) -> list[int]:
    """1-based slide numbers with no picture/chart/table/colored shape at
    all -- just unfilled text on whatever the slide's own background is.
    A slide-level background color doesn't count (pptxgenjs sets that as
    `slide.background`, a property of the slide itself, not a shape), so a
    plain-colored "themed" slide with only unfilled text boxes still gets
    flagged -- this matches the actual reported defect directly: a deck
    can look designed from its background/typography alone while every
    slide underneath is still just a title and a bullet list."""
    return [
        index
        for index, slide in enumerate(prs.slides, start=1)
        if not _slide_has_visual_element(slide)
    ]


# The rendered word box is about 1.2x the font size tall.
_WORD_BOX_PER_POINT = 1.2
# Below this, body text on a slide is hard to read from a screen share or a
# room; the usual floor for body text is 18pt, 12 the least anyone defends.
_MIN_BODY_POINTS = 14.0
# A content slide whose lowest content stops above this share of its height
# reads as unfinished: the bottom half is empty.
_SPARSE_BOTTOM_SHARE = 0.55


def check_rendered_layout(
    layout: list[dict[str, Any]], prs: Any
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """From the rendered pages (PDFium word boxes): slides whose body text
    is under _MIN_BODY_POINTS, and content slides (not the first) whose
    content ends in their upper half. Measured on the render, so inherited
    sizes and autofit count. Empty when nothing could be rendered."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    small: list[dict[str, object]] = []
    sparse: list[dict[str, object]] = []
    for number, (page, slide) in enumerate(zip(layout, prs.slides, strict=False), start=1):
        words = [w for w in page["words"] if w[3] > w[1]]
        if not words or page["height"] <= 0:
            continue
        tallest = max(w[3] - w[1] for w in words)
        # The title is the biggest text; everything else is body.
        body = [w for w in words if (w[3] - w[1]) < 0.85 * tallest] or words
        heights = sorted((w[3] - w[1]) / _WORD_BOX_PER_POINT for w in body)
        median = heights[len(heights) // 2]
        if len(body) >= 8 and median < _MIN_BODY_POINTS:
            small.append({"slide": number, "body_text_pt": round(median, 1)})
        if number == 1:
            continue
        bottom = max(w[3] for w in body) / page["height"]
        for shape in slide.shapes:
            box = shape_bbox(shape)
            if box is None or shape.shape_type not in (
                MSO_SHAPE_TYPE.CHART,
                MSO_SHAPE_TYPE.PICTURE,
                MSO_SHAPE_TYPE.TABLE,
            ):
                continue
            bottom = max(bottom, (box[1] + box[3]) / prs.slide_height)
        if bottom < _SPARSE_BOTTOM_SHARE:
            sparse.append({"slide": number, "content_ends_at_pct": round(bottom * 100)})
    return small, sparse


_LOW_CONTRAST_RATIO_SMALL_TEXT = 4.5
_LOW_CONTRAST_RATIO_LARGE_TEXT = 3.0
# WCAG 2.1's own definition of "large text" -- https://www.w3.org/TR/WCAG21/#dfn-large-scale
_LARGE_TEXT_MIN_PT = 18.0
_LARGE_TEXT_BOLD_MIN_PT = 14.0


def _relative_luminance(rgb: Any) -> float:
    """WCAG 2.1's relative-luminance formula -- the basis its own
    contrast-ratio formula is built on.
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance"""

    def channel(value: int) -> float:
        c = value / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def _contrast_ratio(rgb_a: Any, rgb_b: Any) -> float:
    luminance_a, luminance_b = _relative_luminance(rgb_a), _relative_luminance(rgb_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def _solid_rgb(fill: Any) -> Any | None:
    """`fill`'s own explicit solid RGB color, or None if it isn't one --
    no fill at all, a gradient/picture/pattern fill, or a theme/scheme
    color. A scheme color's actual rendered value lives in the theme XML,
    which this deliberately doesn't chase -- a shape using one is skipped
    by check_low_contrast below rather than guessed at."""
    from pptx.enum.dml import MSO_COLOR_TYPE, MSO_FILL_TYPE

    try:
        if fill.type != MSO_FILL_TYPE.SOLID:
            return None
        color = fill.fore_color
        return color.rgb if color.type == MSO_COLOR_TYPE.RGB else None
    except (AttributeError, TypeError, ValueError):
        return None


def _slide_background_rgb(slide: Any) -> Any | None:
    """The nearest explicit solid background color for `slide` -- its
    own, else its layout's, else its master's (PowerPoint's own
    inheritance order for an unset background) -- or None if none of the
    three sets one explicitly (an inherited theme color, a gradient/
    picture background, or genuinely no background set anywhere)."""
    rgb = _solid_rgb(slide.background.fill)
    if rgb is not None:
        return rgb
    layout = slide.slide_layout
    rgb = _solid_rgb(layout.background.fill)
    if rgb is not None:
        return rgb
    return _solid_rgb(layout.slide_master.background.fill)


def check_low_contrast(prs: Any) -> list[dict[str, object]]:
    """Flags text whose own color and its resolved background fall below
    WCAG 2.1's minimum contrast ratio (4.5:1 for ordinary text, 3.0:1 for
    "large" text -- WCAG's own >=18pt, or >=14pt bold, definition) -- a
    purely computed check, no rendering needed, so (like
    text_overlap_warnings/slides_missing_visual_elements above) it always
    runs. Prompted by reading a much larger third-party PPTX-generation
    skill's (github.com/hugohe3/ppt-master) own visual-review rubric,
    which flags the same defect from a rendered screenshot; coscribe
    doesn't need to render to check this, since the exact colors involved
    are already known from the object model the moment a run's own font
    color and its resolved background are both an explicit solid RGB.

    Deliberately conservative, not exhaustive -- only checks a run whose
    OWN font color is an explicit RGB (never a theme/scheme color, which
    would need the theme XML to resolve to its real rendered value)
    against a background resolved the same way (the shape's own solid
    fill, else the slide's/layout's/master's -- see _slide_background_rgb).
    A run or background that can't resolve this way -- a gradient/picture
    fill, a scheme color, text sitting on top of a photo or another shape
    purely by z-order -- is silently skipped rather than guessed at; the
    existing scrim guidance (PPTX Slides skill) plus a human/review_work
    look already cover exactly that harder, pixel-level case. A run with
    no explicit `font.size` is treated as small text (the stricter 4.5:1
    threshold) rather than assumed large, so an unset size can't hide a
    real defect."""
    from pptx.enum.dml import MSO_COLOR_TYPE

    warnings: list[dict[str, object]] = []
    for slide_index, slide in enumerate(prs.slides, start=1):
        slide_bg = _slide_background_rgb(slide)
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            bg = _solid_rgb(shape.fill) or slide_bg
            if bg is None:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    text = run.text.strip()
                    if not text:
                        continue
                    color = run.font.color
                    if color.type != MSO_COLOR_TYPE.RGB:
                        continue
                    fg = color.rgb
                    size_pt = run.font.size.pt if run.font.size is not None else None
                    bold = bool(run.font.bold)
                    is_large = size_pt is not None and (
                        size_pt >= _LARGE_TEXT_MIN_PT
                        or (bold and size_pt >= _LARGE_TEXT_BOLD_MIN_PT)
                    )
                    threshold = (
                        _LOW_CONTRAST_RATIO_LARGE_TEXT
                        if is_large
                        else _LOW_CONTRAST_RATIO_SMALL_TEXT
                    )
                    ratio = _contrast_ratio(fg, bg)
                    if ratio < threshold:
                        warnings.append(
                            {
                                "slide": slide_index,
                                "text": text[:60],
                                "text_color": str(fg),
                                "background_color": str(bg),
                                "contrast_ratio": round(ratio, 2),
                                "required_ratio": threshold,
                            }
                        )
    return warnings


def preview_deck(path: Path, state_dir: Path | None, max_slides: int) -> dict[str, object]:
    """Every slide rendered to an image, with the checks of the deck's text and layout."""
    from pptx import Presentation

    from ..._thumbnail import render_all_page_previews
    from .engine import built_from_pages

    layout: list[dict[str, Any]] = []
    names, skipped_reason = render_all_page_previews(
        path, state_dir, max_pages=max_slides, layout=layout
    )
    result: dict[str, object] = {
        "preview_paths": names,
        "preview_paths_csv": ",".join(names),
        "preview_skipped_reason": skipped_reason,
    }
    # These checks misread a page compiled from SVG (a two-line title, a figure over its caption)
    # as overlaps, and its build has already run stricter checks of its own.
    pages = built_from_pages(path)
    if pages is not None:
        return {**result, "built_from_pages": pages.name, "checks": "done by the build"}
    prs = Presentation(str(path))
    small_text, sparse = check_rendered_layout(layout, prs)
    return {
        **result,
        "text_overlap_warnings": check_text_overlaps(prs),
        "slides_missing_visual_elements": check_missing_visual_elements(prs),
        "low_contrast_warnings": check_low_contrast(prs),
        "small_text_slides": small_text,
        "sparse_slides": sparse,
    }
