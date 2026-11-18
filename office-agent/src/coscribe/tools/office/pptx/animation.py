"""Animations and audio: the preset catalog and the hand-built `<p:timing>` XML of
`add_pptx_animation` and `add_pptx_audio`."""

from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from .xmlns import A_NS, P14_NS, P_NS, R_NS

# Each preset is a real PowerPoint-exported `<p:cTn>` row (203 presets across entrance, emphasis,
# exit and motion path), vendored from hugohe3/ppt-master (`_native_animation_presets/`, see its
# NOTICE.md). `_instantiate_animation_preset_row` parses one row at call time and adapts it to the
# slide (renumbers ids, retargets spid, scales duration): hand-building 203 effects is not
# realistic and a hand-built row is not guaranteed to be one PowerPoint writes.
_ANIMATION_PRESETS_PATH = (
    Path(__file__).resolve().parents[2] / "_native_animation_presets" / "animation_presets.json"
)

# The six names the tool exposed before the full catalog, kept working: each maps to the preset
# with the same presetID, subtype and category.
ANIMATION_ALIASES = {
    "fade": "entrance_fade",
    "fly-in": "entrance_fly",
    "exit-fade": "exit_fade",
    "exit-fly": "exit_fly",
    "emphasis-grow": "emphasis_grow_shrink",
    "emphasis-spin": "emphasis_spin",
}


@lru_cache(maxsize=1)
def load_animation_presets() -> dict[str, dict[str, Any]]:
    """Every vendored preset, keyed by its real preset key
    (`"entrance_fade"`, `"path_circle"`, ...) -- loaded and cached once."""
    payload = json.loads(_ANIMATION_PRESETS_PATH.read_text(encoding="utf-8"))
    return {effect["key"]: effect for effect in payload["effects"]}


ANIMATIONS = frozenset({*load_animation_presets(), *ANIMATION_ALIASES})


def resolve_animation_preset(animation: str) -> dict[str, Any]:
    key = ANIMATION_ALIASES.get(animation, animation)
    return load_animation_presets()[key]


@cache
def _animation_preset_expected_children(animation: str) -> frozenset[str]:
    """Distinct direct-child tag names of a preset's own `<p:childTnLst>`
    (e.g. `{"animEffect"}` for a fade, `{"anim"}` for a fly, `{"animMotion"}`
    for a motion path) -- the generalization of the old hand-maintained
    `_ANIMATION_CHILD_TAGS` single-tag map, now derived from the real XML
    instead of listed by hand for each of 203 presets. `"set"` (the shared
    visibility toggle every entrance/exit preset also carries) is excluded
    unless it is the *only* child, since it doesn't disambiguate one preset
    from another the way the motion/effect tag does."""
    from lxml import etree

    preset = resolve_animation_preset(animation)
    root = etree.fromstring(preset["row_xml"].encode("utf-8"))
    child_lst = root.find(f"{{{P_NS}}}childTnLst")
    tags = {etree.QName(child).localname for child in child_lst}
    return frozenset(tags - {"set"}) or frozenset({"set"})

# nodeType on the presetID-bearing <p:cTn> is the Animation Pane's "Start" mode. The manifest
# stores a placeholder value for every preset, so the row is always overwritten from the caller's
# trigger (the mapping hugohe3/ppt-master's `_TRIGGER_NODE_TYPES` uses).
_TRIGGER_NODE_TYPES = {
    "on-click": "clickEffect",
    "with-previous": "withEffect",
    "after-previous": "afterEffect",
}
TRIGGERS = frozenset(_TRIGGER_NODE_TYPES)

# add_pptx_audio's own, deliberately small format set -- the three real
# content types hugohe3/ppt-master's own narration tooling supports
# (`AUDIO_CONTENT_TYPES` in `svg_to_pptx/pptx_package/narration.py`),
# not independently guessed.
AUDIO_CONTENT_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav"}
AUDIO_TRIGGERS = frozenset({"auto", "on-click"})
# 457200 EMU = 0.5in -- the real size PowerPoint itself uses for an
# inserted-audio icon (matches hugohe3/ppt-master's own
# AUDIO_MARKER_SIZE_EMU), not independently chosen.
AUDIO_MARKER_SIZE_EMU = 457200


def register_audio_media_part_class() -> None:
    """Register `MediaPart` for every audio content type add_pptx_audio
    uses -- python-pptx's own `PartFactory.part_type_for` dict is a real,
    documented extension point ("Client code can register a subclass of
    |Part| to be used for a package blob based on its content type," per
    its own docstring), but ships with nothing registered for *any*
    media content type, audio or video. Without this, reopening a .pptx
    that already has one audio/video part loads it back as a plain
    |Part| (no `.sha1`), and `Package.get_or_add_media_part`'s own
    dedup-by-sha1 lookup crashes with `AttributeError: 'Part' object has
    no attribute 'sha1'` on every subsequent add_pptx_audio call in the
    same process -- confirmed by hitting exactly that crash on a second
    call before adding this registration, not assumed. A one-time,
    idempotent process-wide side effect, matching how the module-level
    docstring already documents this file lazily importing `pptx`/`lxml`
    inside functions rather than at module scope."""
    from pptx.opc.package import PartFactory
    from pptx.parts.media import MediaPart

    for content_type in AUDIO_CONTENT_TYPES.values():
        PartFactory.part_type_for[content_type] = MediaPart


def _ctn_numeric_delay(ctn: Any) -> int:
    """Largest direct numeric start delay on one <p:cTn>'s own
    <p:stCondLst>/<p:cond> children (0 if none/non-numeric)."""
    conditions = ctn.find(f"{{{P_NS}}}stCondLst")
    if conditions is None:
        return 0
    values = [
        int(condition.get("delay", "0"))
        for condition in conditions.findall(f"{{{P_NS}}}cond")
        if (condition.get("delay") or "").isdigit()
    ]
    return max(values, default=0)


def _row_effective_duration_ms(row: Any) -> int | None:
    """Finite end time (delay + dur) PowerPoint would expose for one
    preset row, or None if nothing in it has a finite numeric duration."""
    ends = []
    for ctn in row.iter(f"{{{P_NS}}}cTn"):
        if ctn is row:
            continue
        raw_duration = ctn.get("dur")
        if raw_duration is None or not raw_duration.isdigit():
            continue
        ends.append(_ctn_numeric_delay(ctn) + int(raw_duration))
    return max(ends) if ends else None


def _scale_preset_row_duration(row: Any, base_duration_ms: int, requested_duration_ms: int) -> None:
    """Scale every finite duration/delay in one parsed preset row so its
    overall length matches `requested_duration_ms` instead of the
    preset's own authored `base_duration_ms` -- adapted from
    hugohe3/ppt-master's `pptx_animations.py`'s
    `_scale_animation_row_duration` (commit `6e3ce9c5a3b994a0e223a14a0f7e
    dd42fd0b9f5`, see `_native_animation_presets/NOTICE.md`), ported from
    `xml.etree.ElementTree` to this file's own `lxml`. A `dur="1"` node
    (the visibility toggle every entrance/exit preset carries) is left at
    exactly 1ms regardless of ratio -- scaling it down to 0 would make the
    shape appear/disappear instantly with no fade *before* the real motion
    starts, and scaling it up would visibly delay the motion for no
    reason; real PowerPoint-authored XML never scales this node either."""
    ratio = requested_duration_ms / base_duration_ms
    for ctn in row.iter(f"{{{P_NS}}}cTn"):
        if ctn is row:
            continue
        raw_duration = ctn.get("dur")
        if raw_duration is not None and raw_duration.isdigit():
            numeric_duration = int(raw_duration)
            ctn.set(
                "dur",
                "1" if numeric_duration == 1 else str(max(1, round(numeric_duration * ratio))),
            )
        conditions = ctn.find(f"{{{P_NS}}}stCondLst")
        if conditions is None:
            continue
        for condition in conditions.findall(f"{{{P_NS}}}cond"):
            raw_delay = condition.get("delay")
            if raw_delay is not None and raw_delay.isdigit():
                condition.set("delay", str(round(int(raw_delay) * ratio)))

    actual_duration = _row_effective_duration_ms(row)
    if actual_duration is None or actual_duration == requested_duration_ms:
        return
    # Rounding several independently-scaled nodes rarely lands exactly on
    # the requested total -- nudge whichever node(s) actually determine
    # the row's end time so the row's real length matches what was asked
    # for, not just "close after rounding."
    end_nodes = [
        ctn
        for ctn in row.iter(f"{{{P_NS}}}cTn")
        if ctn is not row
        and (ctn.get("dur") or "").isdigit()
        and _ctn_numeric_delay(ctn) + int(ctn.get("dur", "0")) == actual_duration
    ]
    for ctn in end_nodes:
        delay = _ctn_numeric_delay(ctn)
        if delay >= requested_duration_ms:
            conditions = ctn.find(f"{{{P_NS}}}stCondLst")
            numeric = (
                [
                    condition
                    for condition in conditions.findall(f"{{{P_NS}}}cond")
                    if (condition.get("delay") or "").isdigit()
                ]
                if conditions is not None
                else []
            )
            if numeric:
                numeric[-1].set("delay", str(max(0, requested_duration_ms - 1)))
                delay = _ctn_numeric_delay(ctn)
        ctn.set("dur", str(max(1, requested_duration_ms - delay)))


def _instantiate_animation_preset_row(
    row_par: Any,
    effect_id: int,
    shape_id: int,
    animation: str,
    duration_ms: int,
    node_type: str,
    paragraph_index: int | None = None,
) -> int:
    """Instantiate one vendored preset as the innermost <p:cTn
    presetID=...> node (and everything under it), appended as a child of
    `row_par` (a <p:par> already created by the caller). Returns the next
    free id.

    Rather than hand-rebuilding each animation type's XML shape (the
    previous design, practical for the original 6 presets but not for the
    full 203-preset catalog), this parses the preset's own real,
    PowerPoint-authored `row_xml` and adapts it in place: renumbers every
    <p:cTn id=...> sequentially from `effect_id` (the row_xml's own ids
    always start at a fixed 5/6/7... baseline, since it was authored
    against a hypothetical single-shape slide -- they'd collide with a
    real slide's own running id counter otherwise), retargets every
    <p:spTgt spid="2"> placeholder to the real `shape_id`, and -- when the
    preset declares itself duration-scalable -- scales every finite
    duration/delay from the preset's own authored default to
    `duration_ms` via `_scale_preset_row_duration`. A handful of presets
    (instant appear/disappear toggles, discrete state changes like "change
    font") are not duration-scalable at all; for those, `duration_ms` is
    ignored and the preset's own authored timing is kept verbatim --
    real PowerPoint doesn't expose a duration control for these either."""
    from lxml import etree

    preset = resolve_animation_preset(animation)
    root = etree.fromstring(preset["row_xml"].encode("utf-8"))
    root.set("nodeType", node_type)

    next_id = effect_id
    for ctn in root.iter(f"{{{P_NS}}}cTn"):
        ctn.set("id", str(next_id))
        next_id += 1

    for sp_tgt in root.iter(f"{{{P_NS}}}spTgt"):
        sp_tgt.set("spid", str(shape_id))
        if paragraph_index is not None:
            tx_el = etree.SubElement(sp_tgt, f"{{{P_NS}}}txEl")
            etree.SubElement(
                tx_el, f"{{{P_NS}}}pRg", st=str(paragraph_index), end=str(paragraph_index)
            )

    base_duration_ms = preset["default_duration_ms"]
    if preset["duration_scalable"] and base_duration_ms is not None:
        _scale_preset_row_duration(root, base_duration_ms, duration_ms)

    row_par.append(root)
    return next_id


def _append_main_seq(root_child: Any, main_seq_id: int) -> Any:
    """Append a fresh, empty <p:seq> (mainSeq) to `root_child` (tmRoot's
    own <p:childTnLst>), returning mainSeq's own (also empty) childTnLst
    for the caller to append its first <p:par> step into -- the shared
    "add animation support to a slide" step, whether that slide has no
    timing tree at all yet (`_new_timing_tree`) or already has one
    without a mainSeq because `add_pptx_audio` created it first
    (`add_animation_step`'s own mainSeq-missing branch)."""
    from lxml import etree

    seq = etree.SubElement(root_child, f"{{{P_NS}}}seq", concurrent="1", nextAc="seek")
    main_ctn = etree.SubElement(
        seq, f"{{{P_NS}}}cTn", id=str(main_seq_id), dur="indefinite", nodeType="mainSeq"
    )
    main_child = etree.SubElement(main_ctn, f"{{{P_NS}}}childTnLst")
    prev_cond_lst = etree.SubElement(seq, f"{{{P_NS}}}prevCondLst")
    prev_cond = etree.SubElement(prev_cond_lst, f"{{{P_NS}}}cond", evt="onPrev", delay="0")
    etree.SubElement(etree.SubElement(prev_cond, f"{{{P_NS}}}tgtEl"), f"{{{P_NS}}}sldTgt")
    next_cond_lst = etree.SubElement(seq, f"{{{P_NS}}}nextCondLst")
    next_cond = etree.SubElement(next_cond_lst, f"{{{P_NS}}}cond", evt="onNext", delay="0")
    etree.SubElement(etree.SubElement(next_cond, f"{{{P_NS}}}tgtEl"), f"{{{P_NS}}}sldTgt")
    return main_child


def _new_timing_tree(slide_element: Any) -> tuple[Any, Any]:
    """Create `slide_element`'s (a <p:sld>) very first <p:timing> tree,
    including its mainSeq -- the tmRoot/seq/mainSeq skeleton every
    animation, regardless of trigger, lives under. Returns (timing,
    mainSeq's own childTnLst)."""
    from lxml import etree

    timing = etree.SubElement(slide_element, f"{{{P_NS}}}timing")
    tn_lst = etree.SubElement(timing, f"{{{P_NS}}}tnLst")
    root_par = etree.SubElement(tn_lst, f"{{{P_NS}}}par")
    root_ctn = etree.SubElement(
        root_par, f"{{{P_NS}}}cTn", id="1", dur="indefinite", restart="never", nodeType="tmRoot"
    )
    root_child = etree.SubElement(root_ctn, f"{{{P_NS}}}childTnLst")
    main_child = _append_main_seq(root_child, 2)
    return timing, main_child


def next_timing_id(timing: Any) -> int:
    existing_ids = [
        int(element.get("id"))
        for element in timing.iter(f"{{{P_NS}}}cTn")
        if element.get("id") is not None
    ]
    return max(existing_ids, default=2) + 1


def timing_root_child_list(slide_element: Any) -> Any:
    """Return-or-create the <p:timing>'s tmRoot <p:cTn>'s own
    <p:childTnLst> -- where <p:seq> (add_pptx_animation's mainSeq) and
    <p:audio>/<p:video> (auto-playing media, add_pptx_audio's own node)
    live as siblings. Creates only the minimal tmRoot/childTnLst skeleton
    if the slide has no <p:timing> yet -- deliberately *not* an empty
    mainSeq: `CT_TimeNodeList` (mainSeq's own childTnLst type) requires
    at least one child, so an empty <p:seq> is schema-invalid on its own,
    confirmed by hitting exactly that real validation error before fixing
    this. mainSeq is only ever added once an actual animation needs it
    (see add_animation_step's own mainSeq-missing branch)."""
    from lxml import etree

    timing = slide_element.find(f"{{{P_NS}}}timing")
    if timing is None:
        timing = etree.SubElement(slide_element, f"{{{P_NS}}}timing")
        tn_lst = etree.SubElement(timing, f"{{{P_NS}}}tnLst")
        root_par = etree.SubElement(tn_lst, f"{{{P_NS}}}par")
        root_ctn = etree.SubElement(
            root_par,
            f"{{{P_NS}}}cTn",
            id="1",
            dur="indefinite",
            restart="never",
            nodeType="tmRoot",
        )
        return etree.SubElement(root_ctn, f"{{{P_NS}}}childTnLst")
    return timing.find(f".//{{{P_NS}}}cTn[@nodeType='tmRoot']/{{{P_NS}}}childTnLst")


_AUDIO_EXT_URI = "{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}"


def build_audio_pic_element(
    shape_id: int,
    shape_name: str,
    audio_rid: str,
    media_rid: str,
    poster_rid: str,
    x_emu: int,
    y_emu: int,
    size_emu: int,
) -> Any:
    """<p:pic> shape carrying embedded narration/background audio --
    adapted from hugohe3/ppt-master's own `svg_to_pptx/pptx_package/
    narration.py`'s `_create_audio_pic_element` (commit
    `6e3ce9c5a3b994a0e223a14a0f7edd42fd0b9f5`): real PowerPoint audio XML
    needs BOTH a legacy `<a:audioFile r:link=...>` reference (`EG_Media`,
    the pre-2010 mechanism) and a PowerPoint-2010 `<p14:media
    r:embed=...>` extension (inside `<p:nvPr>`'s own `<p:extLst>`)
    pointing at the SAME media part via two different relationship types
    -- confirmed against python-pptx's own `add_movie`, which builds the
    video equivalent (`<a:videoFile>`) the identical way for the
    identical documented reason ("two relationships to the same part...
    for legacy support for an earlier pre-Office 2010 PowerPoint media
    embedding strategy"). No `mc:Ignorable` needed for `p14:media` here,
    unlike `p14:dur`/`a14:m` elsewhere in this file -- confirmed against
    the real vendored schema: `<p:ext>` (`CT_Extension`/
    `CT_OfficeArtExtension`) already declares an `xsd:any
    processContents="lax"` wildcard, so foreign-namespaced content inside
    an extLst is schema-legitimate on its own, unlike a bare foreign
    attribute/element with no such wildcard slot."""
    from lxml import etree

    pic = etree.Element(f"{{{P_NS}}}pic")
    nv_pic_pr = etree.SubElement(pic, f"{{{P_NS}}}nvPicPr")
    c_nv_pr = etree.SubElement(
        nv_pic_pr, f"{{{P_NS}}}cNvPr", id=str(shape_id), name=shape_name
    )
    etree.SubElement(
        c_nv_pr,
        f"{{{A_NS}}}hlinkClick",
        {f"{{{R_NS}}}id": "", "action": "ppaction://media"},
    )
    c_nv_pic_pr = etree.SubElement(nv_pic_pr, f"{{{P_NS}}}cNvPicPr")
    etree.SubElement(c_nv_pic_pr, f"{{{A_NS}}}picLocks", noChangeAspect="1")
    nv_pr = etree.SubElement(nv_pic_pr, f"{{{P_NS}}}nvPr")
    etree.SubElement(nv_pr, f"{{{A_NS}}}audioFile", {f"{{{R_NS}}}link": audio_rid})
    ext_lst = etree.SubElement(nv_pr, f"{{{P_NS}}}extLst")
    ext = etree.SubElement(ext_lst, f"{{{P_NS}}}ext", uri=_AUDIO_EXT_URI, nsmap={"p14": P14_NS})
    etree.SubElement(ext, f"{{{P14_NS}}}media", {f"{{{R_NS}}}embed": media_rid})

    blip_fill = etree.SubElement(pic, f"{{{P_NS}}}blipFill")
    etree.SubElement(blip_fill, f"{{{A_NS}}}blip", {f"{{{R_NS}}}embed": poster_rid})
    stretch = etree.SubElement(blip_fill, f"{{{A_NS}}}stretch")
    etree.SubElement(stretch, f"{{{A_NS}}}fillRect")

    sp_pr = etree.SubElement(pic, f"{{{P_NS}}}spPr")
    xfrm = etree.SubElement(sp_pr, f"{{{A_NS}}}xfrm")
    etree.SubElement(xfrm, f"{{{A_NS}}}off", x=str(x_emu), y=str(y_emu))
    etree.SubElement(xfrm, f"{{{A_NS}}}ext", cx=str(size_emu), cy=str(size_emu))
    prst_geom = etree.SubElement(sp_pr, f"{{{A_NS}}}prstGeom", prst="rect")
    etree.SubElement(prst_geom, f"{{{A_NS}}}avLst")
    return pic


def build_audio_timing_node(shape_id: int, ctn_id: int, start_delay_ms: int | None) -> Any:
    """<p:audio> media-playback timing node -- auto-plays `start_delay_ms`
    after the slide begins, or (when `start_delay_ms` is None) waits for
    the shape's own `ppaction://media` click hyperlink instead
    (`delay="indefinite"`, matching python-pptx's own `add_movie`/
    `_add_video_timing` for the click-triggered case). Adapted from
    hugohe3/ppt-master's own `svg_to_pptx/pptx_package/narration.py`'s
    `_create_audio_timing_element` (commit
    `6e3ce9c5a3b994a0e223a14a0f7edd42fd0b9f5`)."""
    from lxml import etree

    audio = etree.Element(f"{{{P_NS}}}audio")
    media_node = etree.SubElement(audio, f"{{{P_NS}}}cMediaNode", vol="80000")
    time_node = etree.SubElement(
        media_node, f"{{{P_NS}}}cTn", id=str(ctn_id), fill="hold", display="0"
    )
    delay = "indefinite" if start_delay_ms is None else str(start_delay_ms)
    st_cond_lst = etree.SubElement(time_node, f"{{{P_NS}}}stCondLst")
    etree.SubElement(st_cond_lst, f"{{{P_NS}}}cond", delay=delay)
    target = etree.SubElement(media_node, f"{{{P_NS}}}tgtEl")
    etree.SubElement(target, f"{{{P_NS}}}spTgt", spid=str(shape_id))
    return audio


def _append_step(
    child_lst: Any,
    step_id: int,
    row_id: int,
    shape_id: int,
    animation: str,
    duration_ms: int,
    node_type: str,
    start_ms: int,
    paragraph_index: int | None,
) -> None:
    """Append one more <p:par> step to `child_lst` (a group's own
    childTnLst, or a freshly-created group's), starting `start_ms`
    milliseconds after whatever that group's own trigger condition
    resolves. This is the one shape shared by a click group's first (and
    only, pre-this-feature) step and every with-previous/after-previous
    step chained onto an existing group -- structurally identical, only
    `start_ms` and `node_type` differ."""
    from lxml import etree

    step_par = etree.SubElement(child_lst, f"{{{P_NS}}}par")
    step_ctn = etree.SubElement(step_par, f"{{{P_NS}}}cTn", id=str(step_id), fill="hold")
    step_st = etree.SubElement(step_ctn, f"{{{P_NS}}}stCondLst")
    etree.SubElement(step_st, f"{{{P_NS}}}cond", delay=str(start_ms))
    step_child = etree.SubElement(step_ctn, f"{{{P_NS}}}childTnLst")
    row_par = etree.SubElement(step_child, f"{{{P_NS}}}par")
    _instantiate_animation_preset_row(
        row_par, row_id, shape_id, animation, duration_ms, node_type, paragraph_index
    )


def _step_timing(step_par: Any) -> tuple[int, int]:
    """(start_ms, duration_ms) already recorded for one existing step
    <p:par> (built by _append_step) -- used to compute where the *next*
    with-previous/after-previous step chained onto the same group should
    start. duration_ms is the max `dur` among the step's own descendant
    <p:cTn> elements (every animation type here sets `dur=str(duration_ms)`
    on at least one -- the motion element itself, not just the 1ms
    visibility toggle -- so max() recovers it without per-type
    special-casing)."""
    step_ctn = step_par.find(f"{{{P_NS}}}cTn")
    cond = step_ctn.find(f"{{{P_NS}}}stCondLst/{{{P_NS}}}cond")
    start_ms = int(cond.get("delay"))
    durations = [
        int(element.get("dur"))
        for element in step_ctn.iter(f"{{{P_NS}}}cTn")
        if element is not step_ctn and element.get("dur") not in (None, "indefinite")
    ]
    return start_ms, max(durations, default=0)


def add_animation_step(
    slide_element: Any,
    shape_id: int,
    animation: str,
    duration_ms: int,
    trigger: str,
    delay_ms: int,
    paragraph_index: int | None,
) -> None:
    """Add one animation to `slide_element`'s (a <p:sld>) <p:timing> tree,
    creating the tree if this is the slide's first animation.

    trigger="on-click" always starts a brand-new top-level click group --
    PowerPoint plays click groups in the order they appear in childTnLst,
    so on-click animations added in call order play in that order during
    the slideshow, same as this file's behavior before trigger existed.

    trigger="with-previous"/"after-previous" instead chains onto the LAST
    existing group on this slide (whichever kind it is) as one more step,
    computing its start time from that group's own most-recently-added
    step: with-previous starts at the same time as that step, after-
    previous starts once that step's own animation duration has elapsed
    -- `delay_ms` adds any extra gap on top of either. If the slide has
    no groups yet, a with-previous/after-previous call instead becomes
    the anchor of a brand-new group that starts automatically when the
    slide itself begins (no click needed) -- matching real PowerPoint,
    where the very first animation on a slide still plays even if its
    own Start mode is "After Previous"."""
    node_type = _TRIGGER_NODE_TYPES[trigger]
    timing = slide_element.find(f"{{{P_NS}}}timing")
    if timing is None:
        timing, main_child = _new_timing_tree(slide_element)
        group = None
    else:
        main_child = timing.find(f".//{{{P_NS}}}cTn[@nodeType='mainSeq']/{{{P_NS}}}childTnLst")
        if main_child is None:
            # add_pptx_audio already created this slide's <p:timing> tree
            # without a mainSeq (an empty <p:seq> is itself schema-
            # invalid, so it's only ever added once an animation needs
            # it) -- add one now, alongside whatever audio/video nodes
            # are already there, rather than discarding the tree.
            root_child = timing.find(
                f".//{{{P_NS}}}cTn[@nodeType='tmRoot']/{{{P_NS}}}childTnLst"
            )
            main_child = _append_main_seq(root_child, next_timing_id(timing))
            group = None
        else:
            group = main_child[-1] if len(main_child) else None

    next_id = next_timing_id(timing)

    if trigger == "on-click" or group is None:
        from lxml import etree

        outer_id, step_id, row_id = next_id, next_id + 1, next_id + 2
        outer_par = etree.SubElement(main_child, f"{{{P_NS}}}par")
        outer_ctn = etree.SubElement(outer_par, f"{{{P_NS}}}cTn", id=str(outer_id), fill="hold")
        outer_st = etree.SubElement(outer_ctn, f"{{{P_NS}}}stCondLst")
        etree.SubElement(outer_st, f"{{{P_NS}}}cond", delay="indefinite")
        if trigger != "on-click":
            # This slide has no existing animation to chain onto, so this
            # with-previous/after-previous call anchors a new group that
            # starts on slide entry instead: it waits for mainSeq (id=2)
            # itself to begin, not a click.
            begin_cond = etree.SubElement(outer_st, f"{{{P_NS}}}cond", evt="onBegin", delay="0")
            etree.SubElement(begin_cond, f"{{{P_NS}}}tn", val="2")
        outer_child = etree.SubElement(outer_ctn, f"{{{P_NS}}}childTnLst")
        _append_step(
            outer_child, step_id, row_id, shape_id, animation, duration_ms, node_type,
            delay_ms, paragraph_index,
        )
        return

    group_ctn = group.find(f"{{{P_NS}}}cTn")
    group_child = group_ctn.find(f"{{{P_NS}}}childTnLst")
    prev_start_ms, prev_duration_ms = _step_timing(group_child[-1])
    start_ms = (
        prev_start_ms + delay_ms
        if trigger == "with-previous"
        else prev_start_ms + prev_duration_ms + delay_ms
    )
    step_id, row_id = next_id, next_id + 1
    _append_step(
        group_child, step_id, row_id, shape_id, animation, duration_ms, node_type,
        start_ms, paragraph_index,
    )


def ensure_paragraph_build(timing: Any, shape_id: int) -> None:
    """Add <p:bldP spid=shape_id grpId="0" build="p"/> to <p:timing>'s
    <p:bldLst> (creating it as tnLst's next sibling if needed -- CT_Timing's
    own child order is tnLst then bldLst) -- the sibling element real
    PowerPoint always emits alongside per-paragraph <p:txEl><p:pRg>
    targeting, declaring that this shape's text frame builds in one
    paragraph at a time rather than all at once. Idempotent per shape --
    a second by_paragraph call for the same shape must not add a
    duplicate bldP (spid, grpId) pair, which real PowerPoint XML never
    repeats."""
    from lxml import etree

    bld_lst = timing.find(f"{{{P_NS}}}bldLst")
    if bld_lst is None:
        bld_lst = etree.SubElement(timing, f"{{{P_NS}}}bldLst")
    for existing in bld_lst.findall(f"{{{P_NS}}}bldP"):
        if existing.get("spid") == str(shape_id):
            return
    etree.SubElement(bld_lst, f"{{{P_NS}}}bldP", spid=str(shape_id), grpId="0", build="p")


def verify_animation_readback(
    pptx_path: Path,
    slide: int,
    shape_id: int,
    animation: str,
    trigger: str,
    paragraph_indexes: list[int] | None,
) -> None:
    """Re-open the just-saved file and confirm every animation we intended
    to add is structurally present -- one click/with/after-previous step
    per expected paragraph (or one step targeting the whole shape, if
    `paragraph_indexes` is None) whose effect node targets `shape_id` with
    the right presetID/presetClass/presetSubtype/nodeType, containing
    every one of the preset's own distinguishing motion/effect tags (see
    `_animation_preset_expected_children` -- animEffect for a fade,
    anim/tavLst for a fly, animScale for a grow, animMotion for a motion
    path, and so on for all 203 vendored presets, not a hand-maintained
    per-preset list). This is a *structural* check, not a visual one -- it
    catches "we wrote something that doesn't even parse back as intended"
    (a real risk for hand-written OOXML), not "this looks right in
    PowerPoint" (which this sandbox, with no real PowerPoint, has no way
    to check). presetClass and nodeType must match too, not just
    presetID/presetSubtype -- entrance/exit variants of the same effect
    share identical presetID/presetSubtype in real PowerPoint XML, and the
    three trigger modes share presetID/presetClass/presetSubtype entirely
    (see _TRIGGER_NODE_TYPES's comment) -- so presetClass disambiguates
    entrance/exit/emphasis/path and nodeType disambiguates trigger, and
    skipping either would let this check silently pass on a structurally
    wrong animation or trigger."""
    from pptx import Presentation

    prs = Presentation(str(pptx_path))
    target_slide = prs.slides[slide - 1]
    preset = resolve_animation_preset(animation)
    preset_class = preset["category"][:4]
    preset_id = str(preset["preset_id"])
    preset_subtype = str(preset["preset_subtype"])
    node_type = _TRIGGER_NODE_TYPES[trigger]
    expected_children = _animation_preset_expected_children(animation)
    expected: list[int | None] = (
        list(paragraph_indexes) if paragraph_indexes is not None else [None]
    )

    matches = [
        cTn
        for cTn in target_slide.element.iter(f"{{{P_NS}}}cTn")
        if cTn.get("presetID") == preset_id
        and cTn.get("presetSubtype") == preset_subtype
        and cTn.get("presetClass") == preset_class
        and cTn.get("nodeType") == node_type
    ]
    found: set[int | None] = set()
    for candidate in matches:
        sp_tgt = candidate.find(f".//{{{P_NS}}}spTgt")
        if sp_tgt is None or sp_tgt.get("spid") != str(shape_id):
            continue
        if not all(
            candidate.find(f".//{{{P_NS}}}{tag}") is not None for tag in expected_children
        ):
            continue
        p_rg = sp_tgt.find(f"{{{P_NS}}}txEl/{{{P_NS}}}pRg")
        found.add(int(p_rg.get("st")) if p_rg is not None else None)

    missing = [p for p in expected if p not in found]
    if missing:
        raise RuntimeError(
            f"add_pptx_animation: read-back verification failed -- the saved file's "
            f"timing tree doesn't structurally match the {animation!r}/{trigger!r} "
            f"animation just added to shape {shape_id} on slide {slide} "
            f"(paragraph(s) {missing} not found as expected). The file was not modified."
        )
