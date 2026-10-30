"""Deck themes: the `theme=` tokens of `write_pptx`, the colour-scheme slots they map to, and the
East-Asian font fallback applied to the theme part."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ..._ooxml_validate import assert_ooxml_valid

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType

# write_pptx's `theme` parameter: a small deck-wide color/typography
# identity, tokens named after the same bg/surface/text/accent shape
# that Style Dictionary/DTCG-style design-token systems and CSS-theme
# tools (Marp/Slidev/reveal.js) independently converge on for this exact
# problem (see PPTX_DESIGN.md's "background/theme identity" section) --
# mapped onto OOXML's own native <a:clrScheme> slots, the same mapping
# pptxgenjs's own scheme-color model (tx1/bg1/accent1-6) already uses.
_THEME_COLOR_KEYS = frozenset({"bg", "surface", "text", "accent"})
_THEME_FONT_KEYS = frozenset({"heading_font", "body_font"})
THEME_HEX_RE = re.compile(r"^[0-9A-Fa-f]{6}$")
_THEME_SCHEME_COLOR_TAGS = {
    "bg": "lt1",
    "text": "dk1",
    "surface": "lt2",
    "accent": "accent1",
}
# Every stock python-pptx theme (the default blank Presentation() and all
# 3 bundled coscribe templates fill_pptx_template draws from) ships an
# empty East-Asian typeface (<a:ea typeface=""/>) in both majorFont/
# minorFont -- confirmed by direct XML inspection (PPTX_DESIGN.md §3).
# Every Chinese-language deck this generates therefore has its CJK text
# rendered by whatever fallback font the opening machine's PowerPoint
# happens to pick, never a deliberate choice. A real, common Windows/
# Mac-available CJK typeface, applied unconditionally (not gated on the
# `theme` parameter) since this is a defect fix, not a style choice.
_CJK_FALLBACK_TYPEFACE = "Microsoft YaHei"


def parse_theme_tokens(theme: str) -> dict[str, str]:
    """Parse write_pptx's `theme` parameter: comma-separated key=value
    pairs choosing a deck-wide color/typography identity, e.g.
    "bg=0F172A,text=F8FAFC,accent=38BDF8,heading_font=Georgia". Every
    key is optional -- only the tokens given are changed, the rest keep
    python-pptx's stock theme values. Colors are 6-hex-digit, no '#',
    the same convention `layout: <id> ACCENTHEX` already uses. A plain
    key=value string, not a dict-typed parameter, for the same reason
    every other tool in this package avoids list/dict parameters (see
    this module's docstring)."""
    tokens: dict[str, str] = {}
    if not theme.strip():
        return tokens
    valid_keys = _THEME_COLOR_KEYS | _THEME_FONT_KEYS
    for pair in theme.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(
                f"Malformed theme token {pair!r} -- expected 'key=value', e.g. 'bg=0F172A'."
            )
        key, _, value = pair.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key not in valid_keys:
            raise ValueError(
                f"Unknown theme token {key!r} -- valid keys are {', '.join(sorted(valid_keys))}."
            )
        if key in _THEME_COLOR_KEYS and not THEME_HEX_RE.match(value):
            raise ValueError(
                f"theme token {key}={value!r} must be a 6-hex-digit color (no '#'), "
                f"e.g. '{key}=0F172A'."
            )
        tokens[key] = value.upper() if key in _THEME_COLOR_KEYS else value
    return tokens


def set_scheme_color(clr_scheme: Any, tag: str, hex_value: str) -> None:
    """Replace an `<a:clrScheme>` child's color definition in place --
    stock theme colors are a mix of `<a:sysClr>` (dk1/lt1) and
    `<a:srgbClr>` (dk2/lt2/accent1-6/hlink/folHlink); this always writes
    a plain `<a:srgbClr>` regardless of what was there, an explicit
    literal color rather than a system-color reference."""
    from lxml import etree
    from pptx.oxml.ns import qn

    element = clr_scheme.find(qn(f"a:{tag}"))
    if element is None:
        return
    for child in list(element):
        element.remove(child)
    etree.SubElement(element, qn("a:srgbClr")).set("val", hex_value)


def apply_cjk_font_fix(prs: PresentationType) -> None:
    """Fills in the empty East-Asian typeface every stock theme ships
    with (see `_CJK_FALLBACK_TYPEFACE`'s comment) -- applied to every
    slide master's theme part. python-pptx has no public API for editing
    `<a:fontScheme>` (its `clrScheme`/`fontScheme` support is limited to
    undocumented internals, confirmed still unimplemented as of GitHub
    issue scanny/python-pptx#917), so this edits the theme part's XML
    blob directly and writes it back -- verified empirically to
    round-trip correctly through `prs.save()` and reopening. Only fills
    an *existing* `<a:ea>` element's `typeface` attribute, never inserts
    a new one: `CT_TextFont`'s child order is schema-fixed (latin, ea,
    cs, ...) and every real Office-authored theme already declares all
    three, so this never needs to risk getting that order wrong."""
    from lxml import etree
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn

    for master in prs.slide_masters:
        theme_part = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(theme_part.blob)
        font_scheme = root.find(f".//{qn('a:fontScheme')}")
        if font_scheme is None:
            continue
        changed = False
        for role in ("majorFont", "minorFont"):
            font = font_scheme.find(qn(f"a:{role}"))
            if font is None:
                continue
            ea = font.find(qn("a:ea"))
            if ea is None:
                continue
            ea.set("typeface", _CJK_FALLBACK_TYPEFACE)
            changed = True
        if changed:
            assert_ooxml_valid(root, "apply_cjk_font_fix")
            theme_part._blob = etree.tostring(  # noqa: SLF001
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )


def apply_theme(prs: PresentationType, tokens: dict[str, str]) -> None:
    """Applies write_pptx's `theme` tokens to the deck: a solid
    slide-master background fill (`bg`) plus the underlying
    `<a:clrScheme>`/`<a:fontScheme>` XML, so shapes that reference theme
    colors/fonts (via python-pptx's public `theme_color` API, or a
    placeholder's inherited font) pick the new identity up too, not just
    the background -- same lxml-blob-replace approach as
    `apply_cjk_font_fix`, same round-trip verification. `accent` also
    sets `hlink` (hyperlink color) to the same value, since a deck with
    one accent identity shouldn't have an unrelated blue link color left
    over from the stock theme."""
    from lxml import etree
    from pptx.dml.color import RGBColor
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn

    color_tokens = {k: v for k, v in tokens.items() if k in _THEME_COLOR_KEYS}
    font_tokens = {k: v for k, v in tokens.items() if k in _THEME_FONT_KEYS}

    for master in prs.slide_masters:
        theme_part = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(theme_part.blob)
        clr_scheme = root.find(f".//{qn('a:clrScheme')}")
        if clr_scheme is not None:
            for token_key, scheme_tag in _THEME_SCHEME_COLOR_TAGS.items():
                if token_key in color_tokens:
                    set_scheme_color(clr_scheme, scheme_tag, color_tokens[token_key])
            if "accent" in color_tokens:
                set_scheme_color(clr_scheme, "hlink", color_tokens["accent"])
        font_scheme = root.find(f".//{qn('a:fontScheme')}")
        if font_scheme is not None:
            for token_key, role in (("heading_font", "majorFont"), ("body_font", "minorFont")):
                if token_key not in font_tokens:
                    continue
                font = font_scheme.find(qn(f"a:{role}"))
                if font is None:
                    continue
                latin = font.find(qn("a:latin"))
                if latin is None:
                    continue
                latin.set("typeface", font_tokens[token_key])
        assert_ooxml_valid(root, "apply_theme")
        theme_part._blob = etree.tostring(  # noqa: SLF001
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    if "bg" in color_tokens:
        for master in prs.slide_masters:
            master.background.fill.solid()
            master.background.fill.fore_color.rgb = RGBColor.from_string(  # type: ignore[no-untyped-call]
                color_tokens["bg"]
            )


# The real, full <a:clrScheme> vocabulary (all 12 slots ECMA-376 requires
# every theme to declare) -- unlike write_pptx's own `theme` parameter
# above (a simplified bg/text/surface/accent abstraction covering 4 of
# these), edit_pptx_theme_colors below exposes the real slot names
# directly: editing an *existing*, already-designed template wants
# precise control over which of its 6 accents changes, not a simplified
# identity applied uniformly.
THEME_SCHEME_SLOTS = (
    "dk1",
    "lt1",
    "dk2",
    "lt2",
    "accent1",
    "accent2",
    "accent3",
    "accent4",
    "accent5",
    "accent6",
    "hlink",
    "folHlink",
)


def parse_theme_color_slots(colors: str) -> dict[str, str]:
    """Parse edit_pptx_theme_colors's `colors` parameter: comma-separated
    key=value pairs naming real <a:clrScheme> slots directly (see
    THEME_SCHEME_SLOTS) -- the same "key=value,key=value" string
    convention as write_pptx's own `theme` parameter (see
    parse_theme_tokens), reused for consistency rather than inventing a
    second syntax, but validated against the full real slot vocabulary
    instead of that tool's 4-token abstraction."""
    tokens: dict[str, str] = {}
    if not colors.strip():
        raise ValueError("edit_pptx_theme_colors: colors must not be empty.")
    for pair in colors.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(
                f"Malformed color token {pair!r} -- expected 'key=value', e.g. 'accent1=0F6B5C'."
            )
        key, _, value = pair.partition("=")
        key = key.strip()
        value = value.strip()
        if key not in THEME_SCHEME_SLOTS:
            raise ValueError(
                f"Unknown theme color slot {key!r} -- valid slots are: "
                f"{', '.join(THEME_SCHEME_SLOTS)}."
            )
        if not THEME_HEX_RE.match(value):
            raise ValueError(
                f"color {key}={value!r} must be a 6-hex-digit color (no '#'), "
                f"e.g. '{key}=0F6B5C'."
            )
        tokens[key] = value.upper()
    return tokens


def read_scheme_color(clr_scheme: Any, tag: str) -> str | None:
    """Resolve one <a:clrScheme> slot's current hex value. Stock themes
    mix `<a:sysClr>` (dk1/lt1) and `<a:srgbClr>` (everything else, see
    set_scheme_color's own comment) -- `<a:srgbClr val="RRGGBB"/>`
    resolves directly; `<a:sysClr .../>` resolves via its own `lastClr`
    attribute, the literal fallback color every real sysClr element
    carries for exactly this purpose. None if the slot is missing
    (shouldn't happen in a real, schema-valid theme -- ECMA-376 requires
    all 12 -- but defensive rather than assumed)."""
    from pptx.oxml.ns import qn

    element = clr_scheme.find(qn(f"a:{tag}"))
    if element is None:
        return None
    srgb = element.find(qn("a:srgbClr"))
    if srgb is not None:
        val: str | None = srgb.get("val")
        return val
    sys_clr = element.find(qn("a:sysClr"))
    if sys_clr is not None:
        last_clr: str | None = sys_clr.get("lastClr")
        return last_clr
    return None
