"""Slide transitions: the registry and the hand-built `<p:transition>` XML of
`set_pptx_transition`."""

from __future__ import annotations

from typing import Any

from .xmlns import MC_NS, P14_NS, P15_NS, P159_NS, P_NS

_TRANSITION_NAMESPACES = {"p": P_NS, "p14": P14_NS, "p15": P15_NS, "p159": P159_NS}
# The three extension prefixes a transition (and only a transition -- this
# codebase's only other p14 user, add_pptx_formula, owns a14 instead) can
# ever need mc:Ignorable for -- see set_slide_transition's own comment on
# why unmarking all three unconditionally before setting a new transition
# is correct rather than fragile.
_TRANSITION_MCE_PREFIXES = ("p14", "p15", "p159")

# PowerPoint's real native transition gallery (48 effects across its own
# Subtle/Exciting/Dynamic Content categories) plus common legacy aliases
# (8 more) -- retyped from hugohe3/ppt-master's own `pptx_transitions.py`
# (`TRANSITION_SPECS`/`TRANSITION_ALIASES`, commit `6e3ce9c5a3b994a0e223
# a14a0f7eddf42fd0b9f5`), the real element/attribute mapping for each
# effect having been reverse-engineered against actual PowerPoint-authored
# XML there -- not independently guessable, and not worth re-deriving.
# Deliberately narrower than the source in one way: each effect here is
# its own single, sensible default variant (e.g. "push" always defaults to
# `dir="r"`) with no exposed per-transition options (direction/shape/style
# overrides) -- ppt-master's own effect_options system is real, scoped-out
# extra surface for a later pass, not ported here. "prefix" absent means
# the base "p" (ECMA-376) namespace; "fallback" is only meaningful for a
# non-"p" prefix, naming which base transition an older/non-MCE-aware
# reader should see instead (this codebase's own mc:Ignorable-based
# approach doesn't use it today -- see set_slide_transition -- but it's
# kept in the data for a future AlternateContent-based upgrade).
TRANSITION_SPECS: dict[str, dict[str, Any]] = {
    "fade": {"element": "fade", "attrs": {}},
    "push": {"element": "push", "attrs": {"dir": "r"}},
    "wipe": {"element": "wipe", "attrs": {"dir": "r"}},
    "split": {"element": "split", "attrs": {"orient": "horz", "dir": "out"}},
    "cover": {"element": "cover", "attrs": {"dir": "r"}},
    "random": {"element": "random", "attrs": {}},
    "blinds": {"element": "blinds", "attrs": {"dir": "vert"}},
    "checkerboard": {"element": "checker", "attrs": {"dir": "horz"}},
    "comb": {"element": "comb", "attrs": {"dir": "horz"}},
    "cut": {"element": "cut", "attrs": {"thruBlk": "0"}},
    "dissolve": {"element": "dissolve", "attrs": {}},
    "random_bars": {"element": "randomBar", "attrs": {"dir": "vert"}},
    "zoom": {"element": "warp", "attrs": {"dir": "in"}, "prefix": "p14", "fallback": "fade"},
    "morph": {
        "element": "morph",
        "attrs": {"option": "byObject"},
        "prefix": "p159",
        "fallback": "fade",
    },
    "reveal": {"element": "reveal", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "shape": {"element": "circle", "attrs": {}},
    "uncover": {"element": "pull", "attrs": {"dir": "r"}},
    "flash": {"element": "flash", "attrs": {}, "prefix": "p14", "fallback": "fade"},
    "fall_over": {
        "element": "prstTrans",
        "attrs": {"prst": "fallOver", "invX": "1"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "drape": {
        "element": "prstTrans",
        "attrs": {"prst": "drape", "invX": "1"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "curtains": {
        "element": "prstTrans",
        "attrs": {"prst": "curtains"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "wind": {
        "element": "prstTrans",
        "attrs": {"prst": "wind"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "prestige": {
        "element": "prstTrans",
        "attrs": {"prst": "prestige"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "fracture": {
        "element": "prstTrans",
        "attrs": {"prst": "fracture"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "crush": {
        "element": "prstTrans",
        "attrs": {"prst": "crush"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "peel_off": {
        "element": "prstTrans",
        "attrs": {"prst": "peelOff", "invX": "1"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "page_curl": {
        "element": "prstTrans",
        "attrs": {"prst": "pageCurlSingle", "invX": "1"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "airplane": {
        "element": "prstTrans",
        "attrs": {"prst": "airplane"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "origami": {
        "element": "prstTrans",
        "attrs": {"prst": "origami"},
        "prefix": "p15",
        "fallback": "fade",
    },
    "clock": {"element": "wheel", "attrs": {"spokes": "1"}},
    "ripple": {"element": "ripple", "attrs": {}, "prefix": "p14", "fallback": "fade"},
    "honeycomb": {"element": "honeycomb", "attrs": {}, "prefix": "p14", "fallback": "fade"},
    "glitter": {"element": "glitter", "attrs": {}, "prefix": "p14", "fallback": "fade"},
    "vortex": {"element": "vortex", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "shred": {"element": "shred", "attrs": {"dir": "out"}, "prefix": "p14", "fallback": "fade"},
    "switch": {"element": "switch", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "flip": {"element": "flip", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "gallery": {"element": "gallery", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "cube": {"element": "prism", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "doors": {"element": "doors", "attrs": {"dir": "vert"}, "prefix": "p14", "fallback": "fade"},
    "box": {"element": "zoom", "attrs": {}},
    "pan": {"element": "pan", "attrs": {"dir": "r"}, "prefix": "p14", "fallback": "fade"},
    "ferris_wheel": {
        "element": "ferris",
        "attrs": {"dir": "r"},
        "prefix": "p14",
        "fallback": "fade",
    },
    "conveyor": {
        "element": "conveyor",
        "attrs": {"dir": "r"},
        "prefix": "p14",
        "fallback": "fade",
    },
    "rotate": {
        "element": "prism",
        "attrs": {"dir": "r", "isContent": "1"},
        "prefix": "p14",
        "fallback": "fade",
    },
    "window": {"element": "window", "attrs": {}, "prefix": "p14", "fallback": "fade"},
    "orbit": {
        "element": "prism",
        "attrs": {"dir": "r", "isContent": "1", "isInverted": "1"},
        "prefix": "p14",
        "fallback": "fade",
    },
    "fly_through": {"element": "flythrough", "attrs": {}, "prefix": "p14", "fallback": "fade"},
}

# Legacy/compatibility names mapping onto one of the 48 canonical keys
# above -- e.g. an older "strips"/"wheel" name a caller (or a round-
# tripped PPTX) might still use.
TRANSITION_ALIASES: dict[str, str] = {
    "strips": "wipe",
    "circle": "shape",
    "diamond": "shape",
    "newsflash": "flash",
    "plus": "shape",
    "pull": "uncover",
    "wedge": "clock",
    "wheel": "clock",
}

TRANSITIONS = frozenset({*TRANSITION_SPECS, *TRANSITION_ALIASES, "none"})


def _spd_for(duration: float) -> str:
    if duration <= 0.5:
        return "fast"
    if duration <= 1.5:
        return "med"
    return "slow"


def set_slide_transition(slide_element: Any, transition: str, duration: float) -> None:
    """Replace `slide_element`'s (a <p:sld>) transition, in place.

    Verified empirically (round-tripped through python-pptx with warnings
    treated as errors, and through a real LibreOffice conversion): a fresh
    slide's only children are cSld/clrMapOvr, and per the ECMA-376 schema
    order, <p:transition> belongs immediately after those and before any
    <p:timing>/<p:extLst> -- since neither of those exist yet on any slide
    this tool touches, appending at the end of `slide_element` is always
    schema-correct here. "none" means no <p:transition> element at all,
    which is how PowerPoint itself represents no transition.

    p14:dur (precise millisecond timing) is written for every effect, not
    just the 12 whose own preset element already lives in the base "p"
    namespace -- same reasoning either way: the base ECMA-376 schema only
    has the coarse `spd` (fast/med/slow) attribute, `p14:dur` is what real
    PowerPoint XML actually carries for the exact duration a caller gave.
    A non-"p"-namespaced effect (p14/p15/p159, e.g. "morph"/"vortex")
    means both the effect's own preset element *and* the p14:dur attribute
    need marking -- unmarking all three extension prefixes unconditionally
    before marking exactly the one(s) this transition actually needs is
    simpler and just as correct as tracking what the *previous* transition
    used, since transitions are this codebase's sole owner of p14/p15/p159
    (add_pptx_formula owns a14 instead, untouched here).
    """
    from lxml import etree

    existing = slide_element.find(f"{{{P_NS}}}transition")
    if existing is not None:
        slide_element.remove(existing)
    for prefix in _TRANSITION_MCE_PREFIXES:
        _unmark_mce_ignorable(slide_element, prefix)
    if transition == "none":
        return
    canonical = TRANSITION_ALIASES.get(transition, transition)
    spec = TRANSITION_SPECS[canonical]
    prefix = str(spec.get("prefix", "p"))
    namespace = _TRANSITION_NAMESPACES[prefix]

    transition_element = etree.SubElement(
        slide_element, f"{{{P_NS}}}transition", nsmap={"p14": P14_NS}
    )
    transition_element.set("spd", _spd_for(duration))
    transition_element.set(f"{{{P14_NS}}}dur", str(round(duration * 1000)))
    effect_element = etree.SubElement(
        transition_element,
        f"{{{namespace}}}{spec['element']}",
        nsmap={prefix: namespace} if prefix != "p" else None,
    )
    for key, value in spec["attrs"].items():
        effect_element.set(key, str(value))

    mark_mce_ignorable(slide_element, "p14")
    if prefix != "p":
        mark_mce_ignorable(slide_element, prefix)


def mark_mce_ignorable(root_element: Any, prefix: str) -> None:
    """Add `prefix` to `mc:Ignorable`, which lets `_ooxml_validate.py` tell a real OOXML defect
    from declared p14:/a14: extension content. Registering `mc` makes lxml spell the prefix as
    PowerPoint does instead of an `ns0` that depends on what else the root declares.

    The prefix is also declared on the root itself: markup compatibility resolves an Ignorable
    prefix where the attribute is, and PowerPoint asks to repair a slide whose Ignorable names a
    prefix only a descendant declares."""
    from lxml import etree

    etree.register_namespace("mc", MC_NS)
    existing_tokens = (root_element.get(f"{{{MC_NS}}}Ignorable") or "").split()
    if prefix not in existing_tokens:
        root_element.set(f"{{{MC_NS}}}Ignorable", " ".join([*existing_tokens, prefix]))
    uri = next((el.nsmap[prefix] for el in root_element.iter() if prefix in el.nsmap), None)
    if uri is not None and root_element.nsmap.get(prefix) != uri:
        etree.cleanup_namespaces(
            root_element,
            top_nsmap={prefix: uri},
            keep_ns_prefixes=[*root_element.nsmap, prefix],
        )


def _unmark_mce_ignorable(root_element: Any, prefix: str) -> None:
    """Inverse of `mark_mce_ignorable` -- drops `prefix` from the token
    list (and the attribute entirely once empty), keeping a slide that no
    longer has any p14:-namespaced content from still claiming it does."""
    remaining = [
        token
        for token in (root_element.get(f"{{{MC_NS}}}Ignorable") or "").split()
        if token != prefix
    ]
    if remaining:
        root_element.set(f"{{{MC_NS}}}Ignorable", " ".join(remaining))
    elif root_element.get(f"{{{MC_NS}}}Ignorable") is not None:
        del root_element.attrib[f"{{{MC_NS}}}Ignorable"]
