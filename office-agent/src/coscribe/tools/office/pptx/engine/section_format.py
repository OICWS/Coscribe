"""The slide section language (decision 0015): what a section may contain, read into boxes.

A section is one `<section>` of well-formed XHTML on a 1920 x 1080 canvas. Every top-level element
is positioned by `left`, `top`, `width` and `height` in px, so one element is one PowerPoint
shape. The set of elements, attributes and styles is closed: the app draws sections in its own
page, so anything that could run code or fetch from elsewhere is refused here, before a section
is accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from .text_layout import Font, Paragraph, Run

CANVAS = (1920, 1080)
DEFAULT_FONT = "Microsoft YaHei, Arial"
TEXT_TAGS = frozenset({"h1", "h2", "h3", "p", "ul", "ol"})
OTHER_TAGS = frozenset({"x-shape", "img", "svg", "aside"})
SHAPES = ("rect", "round-rect", "ellipse", "triangle", "arrow", "line")
_INLINE = frozenset({"b", "strong", "i", "em", "u", "span", "br"})
_SIZE = {"h1": 64.0, "h2": 48.0, "h3": 36.0}
_LINE_HEIGHT = {"h1": 1.15, "h2": 1.15, "h3": 1.2}
_BOX = ("left", "top", "width", "height")
_TEXT_STYLES = {
    "font-size",
    "font-weight",
    "font-style",
    "font-family",
    "color",
    "text-align",
    "line-height",
    "vertical-align",
    "padding",
    "background",
}
_STYLES = {
    "section": {"background", "font-family", "color"},
    "text": set(_BOX) | _TEXT_STYLES,
    "x-shape": set(_BOX) | {"background", "border", "border-radius", "opacity"},
    "img": set(_BOX) | {"object-fit"},
    "svg": set(_BOX),
    "span": {"color", "font-weight", "font-style", "font-size"},
}
_ATTRIBUTES = {
    "section": {"id", "style"},
    "text": {"id", "style"},
    "x-shape": {"id", "style", "data-shape"},
    "img": {"id", "style", "src", "alt"},
    "svg": {"id", "style", "viewBox", "preserveAspectRatio"},
}
_ALIGN = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}
_ANCHOR = {"top": "t", "middle": "ctr", "bottom": "b"}
_COLOUR = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})")
_PX = re.compile(r"(-?\d+(?:\.\d+)?)(px)?")
_SAFE_PATH = re.compile(r"(?![a-zA-Z][a-zA-Z0-9+.-]*:)(?!/)(?!\\)(?!.*\.\.)[^\s]+")
# Below this a body line is hard to read on a projected 1920-wide slide.
MIN_READABLE_PX = 24.0


class SectionError(ValueError):
    """The section is outside the language; the message says where and what to write instead."""


@dataclass
class Style:
    values: dict[str, str]
    label: str

    def px(self, name: str, default: float | None = None) -> float:
        raw = self.values.get(name)
        if raw is None:
            if default is None:
                raise SectionError(f"{self.label} needs {name} in px")
            return default
        match = _PX.fullmatch(raw.strip())
        if match is None:
            raise SectionError(f"{self.label}: {name} must be a number of px, got {raw!r}")
        return float(match.group(1))

    def box(self) -> tuple[float, float, float, float]:
        x, y, w, h = (self.px(name) for name in _BOX)
        if w <= 0 or h <= 0:
            raise SectionError(f"{self.label}: width and height must be positive")
        return x, y, w, h

    def colour(self, name: str, default: str | None = None) -> str | None:
        raw = self.values.get(name)
        return default if raw is None else colour(raw, f"{self.label}: {name}")


@dataclass
class TextElement:
    tag: str
    label: str
    name: str
    box: tuple[float, float, float, float]
    paragraphs: list[Paragraph]
    bullets: str | None
    align: str
    anchor: str
    line_height: float
    padding: float
    fill: str | None


@dataclass
class Section:
    background: str | None
    font: str
    colour: str
    elements: list[tuple[ET.Element, Style]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def colour(raw: str, where: str) -> str:
    match = _COLOUR.fullmatch(raw.strip())
    if match is None:
        raise SectionError(f"{where} must be #RRGGBB, got {raw!r}")
    hex_ = match.group(1)
    return (hex_ if len(hex_) == 6 else "".join(c * 2 for c in hex_)).upper()


def local(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1] if isinstance(elem.tag, str) else ""


def label(elem: ET.Element) -> str:
    return f'<{local(elem)} id="{elem.get("id")}">' if elem.get("id") else f"<{local(elem)}>"


def parse_section(text: str) -> Section:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise SectionError(
            f"not well-formed XHTML: {e} (close every tag, write <br/> and <img .../>, write "
            "characters instead of entities such as &nbsp;)"
        ) from e
    if local(root) != "section":
        raise SectionError("the file must hold one <section> element")
    _check_attributes(root, "section")
    style = read_style(root, "section")
    section = Section(
        background=style.colour("background"),
        font=style.values.get("font-family", DEFAULT_FONT),
        colour=style.colour("color", "000000") or "000000",
    )
    for child in root:
        _read_child(section, child)
    return section


def _read_child(section: Section, child: ET.Element) -> None:
    tag = local(child)
    if tag == "aside":
        section.notes.extend(line.strip() for line in "".join(child.itertext()).splitlines())
        section.notes = [line for line in section.notes if line]
        return
    kind = "text" if tag in TEXT_TAGS else tag
    if tag not in TEXT_TAGS | OTHER_TAGS:
        allowed = ", ".join(sorted(TEXT_TAGS | OTHER_TAGS))
        raise SectionError(f"{label(child)} is not part of a section; use one of {allowed}")
    _check_attributes(child, kind)
    if tag == "svg":
        _check_svg(child)
    section.elements.append((child, read_style(child, kind)))


def read_style(elem: ET.Element, kind: str) -> Style:
    values: dict[str, str] = {}
    for declaration in (elem.get("style") or "").split(";"):
        if not declaration.strip():
            continue
        name, sep, value = declaration.partition(":")
        name = name.strip().lower()
        if not sep or name not in _STYLES[kind]:
            allowed = ", ".join(sorted(_STYLES[kind]))
            raise SectionError(f"{label(elem)}: style {name!r} is not allowed here ({allowed})")
        values[name] = value.strip()
    return Style(values, label(elem))


def _check_attributes(elem: ET.Element, kind: str) -> None:
    for name in elem.attrib:
        if name not in _ATTRIBUTES[kind]:
            raise SectionError(f"{label(elem)}: attribute {name!r} is not allowed")
    src = elem.get("src")
    if src is not None and not _SAFE_PATH.fullmatch(src):
        raise SectionError(
            f"{label(elem)}: src must be a file path inside the deck folder, got {src!r}"
        )


def _check_svg(svg: ET.Element) -> None:
    """The page language's own checks run when the drawing is compiled; this keeps out what
    would run code or load from elsewhere when the app draws the section."""
    for elem in svg.iter():
        tag = local(elem)
        if tag in {"script", "foreignObject", "style", "iframe", "a"}:
            raise SectionError(f"{label(svg)}: <{tag}> is not allowed in a drawing")
        for name, value in elem.attrib.items():
            short = name.rsplit("}", 1)[-1]
            if short.lower().startswith("on"):
                raise SectionError(f"{label(svg)}: event attribute {short!r} is not allowed")
            if short == "href" and not value.startswith("#") and not _SAFE_PATH.fullmatch(value):
                raise SectionError(f"{label(svg)}: href {value!r} must be a file in the deck")


def text_element(elem: ET.Element, style: Style, section: Section) -> TextElement:
    tag = local(elem)
    size = style.px("font-size", _SIZE.get(tag, 28.0))
    base = Font(
        family=style.values.get("font-family", section.font),
        size=size,
        bold=_bold(style.values.get("font-weight"), tag in _SIZE),
        italic=style.values.get("font-style", "normal") == "italic",
    )
    run_colour = style.colour("color", section.colour) or section.colour
    if tag in {"ul", "ol"}:
        paragraphs = [_list_item(li, base, run_colour) for li in _items(elem)]
    else:
        paragraphs = [Paragraph(_runs(elem, base, run_colour, False), size)]
    return TextElement(
        tag=tag,
        label=label(elem),
        name=elem.get("id") or "",
        box=style.box(),
        paragraphs=[p for p in paragraphs if p.runs],
        bullets={"ul": "bullet", "ol": "number"}.get(tag),
        align=_choice(style, "text-align", _ALIGN, "left"),
        anchor=_choice(style, "vertical-align", _ANCHOR, "top"),
        line_height=_line_height(style, _LINE_HEIGHT.get(tag, 1.35)),
        padding=style.px("padding", 0.0),
        fill=style.colour("background"),
    )


def _items(elem: ET.Element) -> list[ET.Element]:
    items = list(elem)
    for item in items:
        if local(item) != "li":
            raise SectionError(f"{label(elem)} holds only <li> items, found {label(item)}")
    if (elem.text or "").strip():
        raise SectionError(f"{label(elem)}: text belongs inside an <li>")
    return items


def _list_item(li: ET.Element, base: Font, run_colour: str) -> Paragraph:
    return Paragraph(
        _runs(li, base, run_colour, False),
        base.size,
        indent=round(base.size * 1.1),
        space_before=round(base.size * 0.35),
    )


def _runs(elem: ET.Element, font: Font, run_colour: str, underline: bool) -> list[Run]:
    runs: list[Run] = []
    _collect(elem, font, run_colour, underline, runs)
    return _trim(runs)


def _collect(
    elem: ET.Element, font: Font, run_colour: str, underline: bool, runs: list[Run]
) -> None:
    if elem.text:
        runs.append(Run(_spaces(elem.text), font, run_colour, underline))
    for child in elem:
        tag = local(child)
        if tag not in _INLINE:
            raise SectionError(
                f"{label(elem)}: {label(child)} cannot sit in text; use b, i, u, span or br"
            )
        if tag == "br":
            runs.append(Run("\n", font, run_colour, underline))
        else:
            inner_font, inner_colour, inner_underline = _inline(child, font, run_colour, underline)
            _collect(child, inner_font, inner_colour, inner_underline, runs)
        if child.tail:
            runs.append(Run(_spaces(child.tail), font, run_colour, underline))


def _inline(
    child: ET.Element, font: Font, run_colour: str, underline: bool
) -> tuple[Font, str, bool]:
    tag = local(child)
    if tag in {"b", "strong"}:
        return Font(font.family, font.size, True, font.italic), run_colour, underline
    if tag in {"i", "em"}:
        return Font(font.family, font.size, font.bold, True), run_colour, underline
    if tag == "u":
        return font, run_colour, True
    for name in child.attrib:
        if name != "style":
            raise SectionError(f"{label(child)}: attribute {name!r} is not allowed")
    style = read_style(child, "span")
    inner = Font(
        font.family,
        style.px("font-size", font.size),
        _bold(style.values.get("font-weight"), font.bold),
        style.values.get("font-style", "italic" if font.italic else "normal") == "italic",
    )
    return inner, style.colour("color", run_colour) or run_colour, underline


def _trim(runs: list[Run]) -> list[Run]:
    """HTML's whitespace rules: runs of spaces are one, and none at either end of a line."""
    if runs and runs[0].text.startswith(" "):
        first = runs[0]
        runs[0] = Run(first.text.lstrip(" "), first.font, first.colour, first.underline)
    if runs and runs[-1].text.endswith(" "):
        last = runs[-1]
        runs[-1] = Run(last.text.rstrip(" "), last.font, last.colour, last.underline)
    return [run for run in runs if run.text]


def _spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _bold(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    value = raw.strip().lower()
    return value == "bold" or (value.isdigit() and int(value) >= 600)


def _choice(style: Style, name: str, choices: dict[str, str], default: str) -> str:
    raw = style.values.get(name, default).strip().lower()
    if raw not in choices:
        raise SectionError(f"{style.label}: {name} is one of {', '.join(choices)}, got {raw!r}")
    return choices[raw]


def _line_height(style: Style, default: float) -> float:
    raw = style.values.get("line-height")
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise SectionError(
            f"{style.label}: line-height is a plain number (1.3), got {raw!r}"
        ) from None
    if not 1.0 <= value <= 2.5:
        raise SectionError(f"{style.label}: line-height must be between 1.0 and 2.5")
    return value
