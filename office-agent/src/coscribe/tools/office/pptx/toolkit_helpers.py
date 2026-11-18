"""Module-level helpers of the pptx toolkit: validation, lookup, recolouring, delivery."""

from __future__ import annotations

import re
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ... import _office_com
from ..._pptx_shapes import find_shape
from .smartart import SMARTART_NS
from .xmlns import A14_NS, A_NS, P14_NS, P15_NS, P159_NS, P_NS, R_NS

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType

OFFICE_TIMEOUT = 60.0


# add_pptx_shape's own curated subset of python-pptx's ~180-member
# MSO_SHAPE enum (every name below verified against the real installed
# enum, not guessed) -- basic shapes, arrows, flowchart nodes, and
# callouts, the same categories hugohe3/ppt-master's own feature list
# names ("block arrows, chevrons, callouts, flowchart nodes"). Excludes
# the long tail of rarely-used/legacy AutoShapes (line-callout variants
# 1-4 with every border/accent-bar permutation, the 10/12/16/24/32-point
# star sizes, seal/ribbon banners, etc.) -- a smaller, well-named set a
# model can pick from by name alone beats exposing the full enum, the
# same reasoning add_pptx_icon's own curated Lucide subset already uses.
SHAPE_TYPES = frozenset(
    {
        # Basic
        "RECTANGLE",
        "ROUNDED_RECTANGLE",
        "OVAL",
        "ISOSCELES_TRIANGLE",
        "RIGHT_TRIANGLE",
        "DIAMOND",
        "PARALLELOGRAM",
        "TRAPEZOID",
        "PENTAGON",
        "HEXAGON",
        "OCTAGON",
        "CROSS",
        "PLAQUE",
        "CAN",
        "CUBE",
        # Arrows
        "RIGHT_ARROW",
        "LEFT_ARROW",
        "UP_ARROW",
        "DOWN_ARROW",
        "LEFT_RIGHT_ARROW",
        "UP_DOWN_ARROW",
        "BENT_ARROW",
        "CHEVRON",
        "NOTCHED_RIGHT_ARROW",
        "U_TURN_ARROW",
        # Flowchart
        "FLOWCHART_PROCESS",
        "FLOWCHART_DECISION",
        "FLOWCHART_TERMINATOR",
        "FLOWCHART_DATA",
        "FLOWCHART_DOCUMENT",
        "FLOWCHART_PREPARATION",
        "FLOWCHART_PREDEFINED_PROCESS",
        "FLOWCHART_CONNECTOR",
        # Callouts
        "ROUNDED_RECTANGULAR_CALLOUT",
        "RECTANGULAR_CALLOUT",
        "OVAL_CALLOUT",
        "CLOUD_CALLOUT",
        # Decorative
        "CLOUD",
        "HEART",
        "LIGHTNING_BOLT",
        "SUN",
        "MOON",
        "STAR_5_POINT",
        "STAR_4_POINT",
        "SMILEY_FACE",
        "DONUT",
        "NO_SYMBOL",
        "BLOCK_ARC",
        "ARC",
    }
)


# add_pptx_hyperlink's scope: external URLs via python-pptx's own public
# Hyperlink API (Shape.click_action.hyperlink/Run.hyperlink), plus
# internal "jump to another slide" links via a *different* public
# python-pptx API this file previously missed: ActionSetting.target_slide
# (Shape.click_action.target_slide, settable to a real Slide object) --
# confirmed by reading python-pptx's own source before assuming otherwise,
# not carried over from an earlier, now-stale assumption that no public
# support existed. That setter already builds the exact real relationship/
# attribute pair hugohe3/ppt-master's own `hyperlink_contract.py` names
# (`SLIDE_REL_TYPE` = the real "…/relationships/slide" type, `action =
# "ppaction://hlinksldjump"`) -- no hand-rolled XML needed at all, unlike
# set_pptx_transition/add_pptx_animation/add_pptx_audio, since python-
# pptx's own maintainers had already wired this up (its `action` property
# even already recognizes `PP_ACTION.NAMED_SLIDE` on the *read* side; only
# the write-side setter had gone unnoticed here). The `"#slide-N"` url
# syntax below borrows ppt-master's own real convention (`hyperlink_
# contract.py`'s `SLIDE_TARGET_RE`) rather than inventing a new one.
HYPERLINK_SCHEMES = ("http://", "https://", "mailto:", "ftp://")


SLIDE_TARGET_RE = re.compile(r"^#slide-([1-9][0-9]*)$")


def validate_hyperlink_url(url: str) -> None:
    if not url.strip():
        raise ValueError("add_pptx_hyperlink: url must not be empty.")
    if SLIDE_TARGET_RE.match(url):
        return
    if not url.startswith(HYPERLINK_SCHEMES):
        raise ValueError(
            f"add_pptx_hyperlink: url {url!r} must start with one of "
            f'{", ".join(HYPERLINK_SCHEMES)}, or be "#slide-N" to jump to slide N -- '
            "got a scheme-less or unsupported value."
        )


def resolve_slide_jump_target(prs: PresentationType, slide: int, url: str) -> Any | None:
    """None if `url` isn't a `"#slide-N"` target; otherwise the real
    `Slide` object N refers to, raising a helpful, real-count-naming
    error if N is out of range -- matching this file's own established
    out-of-range error convention elsewhere (e.g. `_open_slide`)."""
    match = SLIDE_TARGET_RE.match(url)
    if match is None:
        return None
    target_number = int(match.group(1))
    slide_count = len(prs.slides)
    if not 1 <= target_number <= slide_count:
        raise ValueError(
            f"add_pptx_hyperlink: slide target {url!r} on slide {slide} is out of range "
            f"-- deck has {slide_count} slides."
        )
    return prs.slides[target_number - 1]


# check_pptx_delivery's own curated cross-platform-safe font list -- real,
# hard-won knowledge (which font *names* ship pre-installed on real
# Windows/Mac machines across scripts, not guessable from first
# principles), retyped and credited from hugohe3/ppt-master's
# `svg_to_pptx/drawingml/utils.py`'s own `PPT_SAFE_FONTS` (commit
# `6e3ce9c5a3b994a0e223a14a0f7edd42fd0b9f5`) -- the same "external
# knowledge, retyped and credited" ceremony level `add_pptx_shape`'s own
# curated `MSO_SHAPE` subset and `set_pptx_transition`'s retyped registry
# already use, not vendored as a whole file (it's one flat set of
# lowercase strings, nothing to meaningfully diff against upstream).
# Lowercase, matching how it's compared (case-insensitively) below.
SAFE_FONTS = frozenset(
    {
        "microsoft yahei",
        "simhei",
        "simsun",
        "kaiti",
        "fangsong",
        "dengxian",
        "microsoft jhenghei",
        "microsoft jhenghei ui",
        "pmingliu",
        "mingliu",
        "mingliu_hkscs",
        "dfkai-sb",
        "pingfang sc",
        "heiti sc",
        "songti sc",
        "stsong",
        "pingfang tc",
        "pingfang hk",
        "heiti tc",
        "songti tc",
        "kaiti tc",
        "yu gothic",
        "yu gothic ui",
        "yu mincho",
        "meiryo",
        "meiryo ui",
        "ms gothic",
        "ms mincho",
        "ms pgothic",
        "ms pmincho",
        "ms ui gothic",
        "malgun gothic",
        "gulim",
        "dotum",
        "batang",
        "nirmala ui",
        "mangal",
        "kokila",
        "aparajita",
        "utsaah",
        "leelawadee ui",
        "leelawadee",
        "cordia new",
        "angsana new",
        "browallia new",
        "david",
        "miriam",
        "frank ruehl",
        "gisha",
        "levenim mt",
        "narkisim",
        "aharoni",
        "arial",
        "arial black",
        "calibri",
        "segoe ui",
        "verdana",
        "helvetica",
        "helvetica neue",
        "tahoma",
        "trebuchet ms",
        "times new roman",
        "times",
        "georgia",
        "cambria",
        "cambria math",
        "palatino",
        "garamond",
        "book antiqua",
        "consolas",
        "courier new",
        "menlo",
        "monaco",
        "impact",
    }
)


# 20MB -- roughly the point real email providers start rejecting or
# aggressively compressing an attachment; a round, memorable threshold
# rather than a precisely-researched one, deliberately conservative so
# the advisory fires before delivery actually fails.
DELIVERY_MEDIA_ADVISORY_BYTES = 20_000_000


def analyze_pptx_delivery(file_path: Path) -> dict[str, Any]:
    """The python-pptx-dependent half of check_pptx_delivery -- hidden
    slides, font usage, and per-slide motion (transitions/animations/
    audio) -- split out from the raw-zip-level half so a file broken
    enough that python-pptx can't fully walk it (python-pptx parses
    slide parts lazily, so this can surface anywhere in here, not only
    at `Presentation()` construction) can be caught as one unit by the
    caller and still return the zip-level findings rather than crashing
    the whole audit -- confirmed against a deliberately-corrupted test
    fixture, not assumed sufficient from wrapping only the constructor."""
    from lxml import etree
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn

    prs = Presentation(str(file_path))

    hidden_slides = [
        index + 1
        for index, slide in enumerate(prs.slides)
        if (slide.element.get("show") or "").strip().lower() in ("0", "false")
    ]

    fonts_used: set[str] = set()
    for master in prs.slide_masters:
        try:
            theme_root = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
        except (KeyError, etree.XMLSyntaxError):
            # A real, if malformed/unusual, file this read-only audit
            # must still report on rather than crash -- a missing or
            # unparsable theme part is itself worth surfacing via
            # advisories below, not a reason to abort the whole audit.
            continue
        font_scheme = theme_root.find(f".//{qn('a:fontScheme')}")
        if font_scheme is None:
            continue
        for role in ("majorFont", "minorFont"):
            latin = font_scheme.find(f"{qn(f'a:{role}')}/{qn('a:latin')}")
            typeface = latin.get("typeface") if latin is not None else None
            if typeface and typeface != "+mn-lt" and typeface != "+mj-lt":
                fonts_used.add(typeface)
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.font.name:
                        fonts_used.add(run.font.name)
    unsafe_fonts = sorted(font for font in fonts_used if font.strip().lower() not in SAFE_FONTS)

    transition_slides: list[int] = []
    animation_slides: list[int] = []
    audio_slides: list[int] = []
    for index, slide in enumerate(prs.slides, start=1):
        if slide.element.find(f"{{{P_NS}}}transition") is not None:
            transition_slides.append(index)
        timing = slide.element.find(f"{{{P_NS}}}timing")
        if timing is None:
            continue
        main_child = timing.find(f".//{{{P_NS}}}cTn[@nodeType='mainSeq']/{{{P_NS}}}childTnLst")
        if main_child is not None and len(main_child):
            animation_slides.append(index)
        if timing.find(f".//{{{P_NS}}}audio") is not None:
            audio_slides.append(index)

    return {
        "slide_count": len(prs.slides),
        "hidden_slides": hidden_slides,
        "fonts_used": sorted(fonts_used),
        "unsafe_fonts": unsafe_fonts,
        "motion": {
            "transitions": transition_slides,
            "animations": animation_slides,
            "audio": audio_slides,
        },
    }


def render_to_pdf(pptx_path: Path) -> Path | None:
    """`pptx_path` as a PDF drawn by the office program installed, for the overflow check
    below. None -- "QA skipped", not an error -- without an office program or when it fails:
    the write has already succeeded, and this check is an extra on top of it."""
    out_dir = Path(tempfile.mkdtemp(prefix="coscribe_pptx_qa_"))
    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    try:
        if _office_com.convert(pptx_path, pdf_path, "pdf", OFFICE_TIMEOUT) is None:
            return None
    except ValueError:
        return None
    return pdf_path


def resolve_xml_qname(name: str) -> str:
    """Resolve an attribute/tag name for edit_pptx_xml's `set_attributes` --
    "prefix:local" using a prefix from `GENERIC_XML_NSMAP` becomes real
    Clark notation ("{uri}local"), lxml's own internal representation, so
    `element.set(...)` writes it into the right namespace. A plain
    unprefixed name (the common case -- "modelId", "type") or a prefix
    this map doesn't know passes through unchanged -- python-pptx/lxml
    both accept a no-namespace attribute name exactly as given."""
    if ":" in name:
        prefix, _, local = name.partition(":")
        if prefix in GENERIC_XML_NSMAP:
            return f"{{{GENERIC_XML_NSMAP[prefix]}}}{local}"
    return name


def parse_set_attributes(raw: str | None) -> dict[str, str]:
    """Parse edit_pptx_xml's own `set_attributes` -- one `name=value` pair
    per line, not a `dict[str, str]` parameter -- **found the hard way**
    (see edit_file_batch's own identical note): this codebase's tool
    schemas have to stay Gemini-compatible, and aisuite's own schema
    builder (`Tools.__infer_from_signature`) has no handling at all for
    dict-typed parameters, falling back to a broken literal type string
    ("dict[str, str]") that Gemini's strict schema validation rejects
    outright -- confirmed live by `test_all_tool_schemas_are_gemini_
    compatible` failing the moment a dict-typed parameter was tried here.
    A plain `str` is the one shape guaranteed to produce a valid JSON
    Schema "string" type through that builder. Blank lines are skipped; a
    line with no "=" raises rather than silently dropping a value the
    caller thought they set."""
    if not raw:
        return {}
    attributes: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(
                f"set_attributes line {line!r} has no '=' -- each line must be "
                "'name=value' (one attribute per line)."
            )
        name, _, value = line.partition("=")
        attributes[name.strip()] = value
    return attributes


def validate_xml_part_arg(part: str) -> None:
    if part not in ("auto", "shape", "smartart_data"):
        raise ValueError(f'part must be "auto", "shape", or "smartart_data", got {part!r}.')


def get_shape_at_index(target_slide: Any, slide_number: int, shape_index: int | str) -> Any:
    return find_shape(target_slide, slide_number, shape_index)


def get_table_shape(target_slide: Any, slide_number: int, shape_index: int | str) -> Any:
    """Shared bounds-and-kind validation for edit_pptx_table_cell/
    merge_pptx_table_cells -- raises a clear, actionable error (naming
    list_pptx_shapes) rather than an opaque AttributeError if shape_index
    is out of range or doesn't point at a table."""
    shape = get_shape_at_index(target_slide, slide_number, shape_index)
    if not shape.has_table:
        raise ValueError(
            f"Shape {shape_index} on slide {slide_number} ({shape.shape_type}) isn't a "
            f"table -- call list_pptx_shapes first to find the right shape_index "
            f"(table shapes have is_table: true)."
        )
    return shape


def get_picture_shape(target_slide: Any, slide_number: int, shape_index: int | str) -> Any:
    """Shared bounds-and-kind validation for replace_pptx_image/
    recolor_pptx_icon/crop_pptx_image -- raises a clear, actionable
    error if shape_index doesn't point at a picture (a `<p:pic>` shape,
    python-pptx's `MSO_SHAPE_TYPE.PICTURE`)."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    shape = get_shape_at_index(target_slide, slide_number, shape_index)
    if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
        raise ValueError(
            f"Shape {shape_index} on slide {slide_number} ({shape.shape_type}) isn't a "
            f"picture -- call list_pptx_shapes first to find the right shape_index."
        )
    return shape


# add_pptx_icon's bundled icon set: a curated ~50-icon subset of Lucide
# (https://lucide.dev, ISC license -- see builtin_icons/lucide/LICENSE),
# rasterized to black-on-transparent PNG at build time by
# scripts/build_pptx_icons.py (not fetched or rendered at runtime -- no
# SVG-rasterization library is a runtime dependency of this package).
# `recolor_icon` below reads a bundled PNG and swaps solid black for the
# caller's requested color at call time, keeping the alpha channel (so
# anti-aliased edges stay clean) -- this is why the bundled assets are
# plain black, not pre-colored per icon.
ICONS_DIR = Path(__file__).resolve().parents[3] / "builtin_icons" / "lucide"


ICON_NAMES = frozenset(p.stem for p in ICONS_DIR.glob("*.png"))


def recolor_image(image: Any, color_hex: str) -> Any:
    """Returns a new PIL Image: every pixel of `image` recolored to
    `color_hex`, its own alpha channel preserved untouched -- works on
    any RGBA-convertible image with meaningful transparency, not just a
    bundled icon, since only the alpha channel (the silhouette shape)
    is read, never the source's existing color. This is what makes
    recolor_pptx_icon possible: an icon already placed on a slide can
    be recolored starting from its own current pixels, without needing
    to know which bundled icon name it originally was (or whether it
    came from add_pptx_icon at all)."""
    from PIL import Image

    red, green, blue = (int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    recolored = Image.new("RGBA", image.size, (red, green, blue, 255))
    recolored.putalpha(image.convert("RGBA").getchannel("A"))
    return recolored


def recolor_icon(icon_path: Path, color_hex: str) -> Any:
    """Returns a PIL Image: the bundled black-on-transparent icon PNG
    with every non-transparent pixel recolored to `color_hex`, alpha
    channel (anti-aliased edges) preserved untouched. Uses PIL's own
    `putalpha` rather than a per-pixel Python loop over all 256x256
    pixels -- verified both produce an identical result, this is just
    the fast path."""
    from PIL import Image

    return recolor_image(Image.open(icon_path), color_hex)


# Prefix -> namespace-URI map for read_pptx_xml/edit_pptx_xml's own `xpath`
# and `set_attributes` arguments -- lets the model write real, readable
# XPath ("//dgm:t[.='Plan']") instead of lxml's Clark notation
# ("//{http://schemas.../diagram}t"). Reuses this file's own existing
# namespace constants (the exact ones set_pptx_transition/add_pptx_formula
# already write) rather than re-declaring them, so there's exactly one
# source of truth for each URI.
GENERIC_XML_NSMAP = {
    "p": P_NS,
    "a": A_NS,
    "r": R_NS,
    "dgm": SMARTART_NS,
    "p14": P14_NS,
    "a14": A14_NS,
    "p15": P15_NS,
    "p159": P159_NS,
}


def leaf_shapes(shapes: Any) -> Iterator[Any]:
    """Every shape on a slide in document order, with groups opened up --
    SVG-compiled and designer-made decks keep most of their text inside
    groups."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from leaf_shapes(shape.shapes)
        else:
            yield shape
