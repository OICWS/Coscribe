from pathlib import Path
from typing import Any

import pytest

from .helpers import (
    _P_NS,
    _libreoffice_actually_works,
    _tools_by_name,
)


def test_add_pptx_animation_fade_is_structurally_present(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")

    prs = Presentation(tmp_path / "deck.pptx")
    title_id = prs.slides[0].shapes.title.shape_id
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    assert timing is not None
    matches = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "10" and cTn.get("presetSubtype") == "0"
    ]
    assert len(matches) == 1
    sp_tgt = matches[0].find(f".//{{{_P_NS}}}spTgt")
    assert sp_tgt.get("spid") == str(title_id)
    assert matches[0].find(f".//{{{_P_NS}}}animEffect") is not None


def test_add_pptx_animation_fly_in_is_structurally_present(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=1, animation="fly-in")

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    matches = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "2" and cTn.get("presetSubtype") == "4"
    ]
    assert len(matches) == 1
    anim_elements = matches[0].findall(f".//{{{_P_NS}}}anim")
    assert len(anim_elements) == 2


def test_add_pptx_animation_default_trigger_uses_click_effect_node_type(tmp_path: Path) -> None:
    """Regression test for a real, evidence-backed bug found while
    researching trigger-mode support: nodeType on the presetID-bearing
    <p:cTn> encodes which Animation Pane Start mode a row uses
    (on-click -> "clickEffect", with-previous -> "withEffect",
    after-previous -> "afterEffect" -- cross-checked against
    hugohe3/ppt-master's pptx_animations.py, which always overwrites this
    attribute at row-instantiation time based on the caller's actual
    trigger). This file's own previous hardcoded "afterEffect" (itself a
    prior "fix" from "clickEffect", see git history) was wrong for the
    on-click-only trigger this tool exposed at the time -- the default
    `trigger="on-click"` must produce "clickEffect", not "afterEffect"."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    matches = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "10" and cTn.get("presetSubtype") == "0"
    ]
    assert matches[0].get("nodeType") == "clickEffect"


@pytest.mark.parametrize(
    ("animation", "preset_id", "preset_subtype", "preset_class", "child_tag"),
    [
        ("exit-fade", "10", "0", "exit", "animEffect"),
        ("exit-fly", "2", "4", "exit", "anim"),
        ("emphasis-grow", "6", "0", "emph", "animScale"),
        ("emphasis-spin", "8", "0", "emph", "animRot"),
    ],
)
def test_add_pptx_animation_new_effect_types_are_structurally_present(
    tmp_path: Path,
    animation: str,
    preset_id: str,
    preset_subtype: str,
    preset_class: str,
    child_tag: str,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation=animation)

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    matches = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == preset_id and cTn.get("presetSubtype") == preset_subtype
    ]
    assert len(matches) == 1
    assert matches[0].get("presetClass") == preset_class
    assert matches[0].find(f".//{{{_P_NS}}}{child_tag}") is not None


def test_add_pptx_animation_exit_fade_and_entrance_fade_are_distinguishable(
    tmp_path: Path,
) -> None:
    """Regression test for the real disambiguation bug fixed alongside
    the new effect types: exit-fade and fade share the exact same
    presetID/presetSubtype in real PowerPoint XML (both 10/0) -- only
    presetClass ("exit" vs "entr") tells them apart. Adding exit-fade to
    one shape and fade to another on the same slide must produce two
    genuinely distinct rows, not one row two overlapping readback checks
    both accept."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=1, animation="exit-fade")

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    same_ids = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "10" and cTn.get("presetSubtype") == "0"
    ]
    assert len(same_ids) == 2
    assert {cTn.get("presetClass") for cTn in same_ids} == {"entr", "exit"}


def test_add_pptx_animation_two_calls_produce_unique_ids(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=1, animation="fly-in")

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    ids = [cTn.get("id") for cTn in timing.iter(f"{{{_P_NS}}}cTn")]
    assert len(ids) == len(set(ids))

    # Both click groups must sit directly under mainSeq's childTnLst.
    main_ctn = timing.find(f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']")
    click_groups = main_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    assert len(click_groups) == 2


def test_add_pptx_animation_with_previous_chains_into_the_same_group(tmp_path: Path) -> None:
    """with-previous/after-previous append into the LAST existing group
    on the slide as one more step, rather than starting a new top-level
    click group -- the whole point of auto-play is that the presenter
    doesn't click again for these."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=1, animation="fly-in", trigger="with-previous"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    main_ctn = timing.find(f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']")
    groups = main_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    assert len(groups) == 1
    group_ctn = groups[0].find(f"{{{_P_NS}}}cTn")
    steps = group_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    assert len(steps) == 2


def test_add_pptx_animation_with_previous_starts_at_same_time_as_previous_step(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=1, animation="fly-in", trigger="with-previous"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    group_path = (
        f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']"
        f"/{{{_P_NS}}}childTnLst/{{{_P_NS}}}par/{{{_P_NS}}}cTn"
    )
    group_ctn = timing.find(group_path)
    steps = group_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    delays = [
        step.find(f"{{{_P_NS}}}cTn/{{{_P_NS}}}stCondLst/{{{_P_NS}}}cond").get("delay")
        for step in steps
    ]
    assert delays == ["0", "0"]


def test_add_pptx_animation_after_previous_starts_once_previous_duration_elapses(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="fade", duration=0.4
    )
    tools["add_pptx_animation"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        animation="emphasis-grow",
        duration=0.3,
        trigger="after-previous",
        delay=0.1,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    group_path = (
        f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']"
        f"/{{{_P_NS}}}childTnLst/{{{_P_NS}}}par/{{{_P_NS}}}cTn"
    )
    group_ctn = timing.find(group_path)
    steps = group_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    second_cond = steps[1].find(f"{{{_P_NS}}}cTn/{{{_P_NS}}}stCondLst/{{{_P_NS}}}cond")
    # previous (fade) starts at 0, lasts 400ms; +100ms extra delay = 500ms.
    assert second_cond.get("delay") == "500"


def test_add_pptx_animation_after_previous_with_no_existing_animation_auto_anchors(
    tmp_path: Path,
) -> None:
    """The very first animation on a slide still plays even when its own
    Start mode is "After Previous" -- matching real PowerPoint, where
    there's nothing to wait for, so it starts on slide entry instead of
    needing a click."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="fade", trigger="after-previous"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    main_ctn = timing.find(f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']")
    groups = main_ctn.find(f"{{{_P_NS}}}childTnLst").findall(f"{{{_P_NS}}}par")
    assert len(groups) == 1
    conds = groups[0].find(f"{{{_P_NS}}}cTn/{{{_P_NS}}}stCondLst").findall(f"{{{_P_NS}}}cond")
    assert [cond.get("delay") for cond in conds] == ["indefinite", "0"]
    assert conds[1].get("evt") == "onBegin"

    row = groups[0].find(f".//{{{_P_NS}}}cTn[@presetID]")
    assert row.get("nodeType") == "afterEffect"


def test_add_pptx_animation_rejects_unknown_trigger(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="Unknown trigger"):
        tools["add_pptx_animation"](
            path="deck.pptx", slide=1, shape_index=0, animation="fade", trigger="bogus"
        )


def test_add_pptx_animation_by_paragraph_targets_each_non_empty_paragraph(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one\n- two\n- three")

    result = tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=1, animation="fade", by_paragraph=True
    )
    assert result["paragraph_count"] == 3

    prs = Presentation(tmp_path / "deck.pptx")
    body_id = list(prs.slides[0].shapes)[1].shape_id
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    p_indexes = set()
    for cTn in timing.iter(f"{{{_P_NS}}}cTn"):
        if cTn.get("presetID") != "10" or cTn.get("presetClass") != "entr":
            continue
        sp_tgt = cTn.find(f".//{{{_P_NS}}}spTgt")
        if sp_tgt is None or sp_tgt.get("spid") != str(body_id):
            continue
        p_rg = sp_tgt.find(f"{{{_P_NS}}}txEl/{{{_P_NS}}}pRg")
        if p_rg is not None:
            p_indexes.add(int(p_rg.get("st")))
    assert p_indexes == {0, 1, 2}


def test_add_pptx_animation_by_paragraph_adds_one_bldp_entry(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one\n- two")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=1, animation="fade", by_paragraph=True
    )

    prs = Presentation(tmp_path / "deck.pptx")
    body_id = list(prs.slides[0].shapes)[1].shape_id
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    bld_p = timing.find(f"{{{_P_NS}}}bldLst").findall(f"{{{_P_NS}}}bldP")
    assert len(bld_p) == 1
    assert bld_p[0].get("spid") == str(body_id)
    assert bld_p[0].get("build") == "p"


def test_add_pptx_animation_by_paragraph_rejects_shape_without_text_frame(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n| a | b |\n| - | - |\n| 1 | 2 |")

    with pytest.raises(ValueError, match="no text frame"):
        tools["add_pptx_animation"](
            path="deck.pptx", slide=1, shape_index=1, animation="fade", by_paragraph=True
        )


def test_add_pptx_animation_rejects_unknown_animation(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="Unknown animation"):
        tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="spin")


def test_add_pptx_animation_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="2 shape"):
        tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=99, animation="fade")


def test_add_pptx_animation_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["add_pptx_animation"](path="deck.pptx", slide=5, shape_index=0, animation="fade")


def test_add_pptx_animation_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_animation"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_add_pptx_animation_survives_libreoffice_conversion(tmp_path: Path) -> None:
    import subprocess

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=1, animation="fly-in")

    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(tmp_path / "deck.pptx"),
        ],
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "deck.pdf").is_file()


def test_add_pptx_animation_writes_the_registered_preset_for_every_animation(
    tmp_path: Path,
) -> None:
    """Every single one of the 203 vendored presets + 6 legacy aliases
    actually produces schema-valid, read-back-verified OOXML (via the
    real assert_ooxml_valid/_verify_animation_readback calls
    add_pptx_animation itself makes) -- not just the few spot-checked
    above. A real, cheap way to catch a bad id-renumbering/spid-retarget/
    duration-scaling edge case across the whole catalog at once, the same
    role test_set_pptx_transition_writes_the_registered_effect_for_
    every_transition plays for the 56-entry transition registry."""
    from pptx import Presentation

    from coscribe.tools.office.pptx.animation import (
        ANIMATION_ALIASES,
        ANIMATIONS,
        load_animation_presets,
    )

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    def effect_nodes() -> list[Any]:
        slide_el = Presentation(tmp_path / "deck.pptx").slides[0].element
        timing = slide_el.find(f"{{{_P_NS}}}timing")
        assert timing is not None
        return [cTn for cTn in timing.iter(f"{{{_P_NS}}}cTn") if cTn.get("presetClass")]

    for added, animation in enumerate(sorted(ANIMATIONS), start=1):
        tools["add_pptx_animation"](
            path="deck.pptx", slide=1, shape_index=0, animation=animation, trigger="with-previous"
        )

        # Aliases share their target's preset, so only the per-call count and the
        # newest node's preset prove each call wrote its own effect.
        effects = effect_nodes()
        assert len(effects) == added, animation
        preset = load_animation_presets()[ANIMATION_ALIASES.get(animation, animation)]
        assert effects[-1].get("presetID") == str(preset["preset_id"]), animation
        assert effects[-1].get("presetSubtype") == str(preset["preset_subtype"]), animation


def test_the_animation_preset_catalog_is_found_next_to_the_package() -> None:
    from coscribe.tools.office.pptx.animation import _ANIMATION_PRESETS_PATH

    assert _ANIMATION_PRESETS_PATH.is_file()


def test_list_pptx_animation_types_matches_the_real_registry(tmp_path: Path) -> None:
    from coscribe.tools.office.pptx.animation import ANIMATION_ALIASES, load_animation_presets

    tools = _tools_by_name(tmp_path)

    result = tools["list_pptx_animation_types"]()

    assert result == sorted({*load_animation_presets(), *ANIMATION_ALIASES})
    assert len(result) == 203 + 6


def test_add_pptx_animation_new_catalog_preset_is_structurally_present(
    tmp_path: Path,
) -> None:
    """A preset from the full 203-entry catalog that was never one of the
    original 6 short-named presets -- proves the general parse/renumber/
    retarget path works for a name that never had hand-written XML, not
    just the 6 that used to."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="path_circle")

    prs = Presentation(tmp_path / "deck.pptx")
    title_id = prs.slides[0].shapes.title.shape_id
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    matches = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "1" and cTn.get("presetClass") == "path"
    ]
    assert len(matches) == 1
    sp_tgt = matches[0].find(f".//{{{_P_NS}}}spTgt")
    assert sp_tgt.get("spid") == str(title_id)
    assert matches[0].find(f".//{{{_P_NS}}}animMotion") is not None


def test_add_pptx_animation_scales_duration_from_the_presets_own_default(
    tmp_path: Path,
) -> None:
    """entrance_fly's two <p:anim> nodes are each authored at dur=500 (its
    real default_duration_ms) -- requesting duration=2.0 (2000ms) must
    scale both by the same 4x ratio, not just plug 2000 into one of them."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    result = tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="entrance_fly", duration=2.0
    )
    assert result["duration_ms"] == 2000

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    anim_durations = {
        cTn.get("dur")
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.getparent().tag == f"{{{_P_NS}}}cBhvr"
        and cTn.getparent().getparent().tag == f"{{{_P_NS}}}anim"
    }
    assert anim_durations == {"2000"}


def test_add_pptx_animation_non_scalable_preset_ignores_requested_duration(
    tmp_path: Path,
) -> None:
    """entrance_appear isn't duration-adjustable in real PowerPoint either
    (it's an instant toggle) -- a requested duration must be silently
    ignored rather than corrupting its authored 1ms timing, and the
    result must report the real duration actually used, not a value that
    implies the request took effect."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    result = tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="entrance_appear", duration=5.0
    )

    assert result["duration_ms"] == 1


def test_add_pptx_animation_legacy_alias_and_full_name_produce_identical_xml(
    tmp_path: Path,
) -> None:
    """ "fade" (the pre-203-catalog short name) and "entrance_fade" (the
    real preset key it was always secretly implementing, per
    ANIMATION_ALIASES) must resolve to the exact same preset -- not two
    presets that happen to look similar."""
    import re

    from lxml import etree
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=1, animation="entrance_fade")

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    rows = [
        cTn
        for cTn in timing.iter(f"{{{_P_NS}}}cTn")
        if cTn.get("presetID") == "10" and cTn.get("presetClass") == "entr"
    ]
    assert len(rows) == 2
    # id (per-row running counter) and spid (the two calls deliberately
    # target different shapes) are both expected to differ -- strip both
    # before comparing everything else.
    normalized = [re.sub(r' (id|spid)="\d+"', "", etree.tostring(row).decode()) for row in rows]
    assert normalized[0] == normalized[1]


def test_list_pptx_animation_types_is_read_and_no_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["list_pptx_animation_types"])
    assert metadata.risk_category == "READ"
    assert metadata.requires_approval is False


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_add_pptx_animation_all_four_categories_survive_libreoffice_conversion(
    tmp_path: Path,
) -> None:
    """One preset from each of the 4 categories (entrance/emphasis/exit/
    path), mixed triggers, plus by_paragraph, on one real deck -- can't
    verify the animation *plays back* correctly in a static test (that
    needs a human watching real PowerPoint/LibreOffice), but a real
    subprocess conversion succeeding, plus a warnings-as-errors
    python-pptx round-trip, is the strongest automated check available."""
    import subprocess
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- alpha\n- beta\n- gamma")
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="entrance_bounce", trigger="on-click"
    )
    tools["add_pptx_animation"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        animation="emphasis_teeter",
        trigger="with-previous",
    )
    tools["add_pptx_animation"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        animation="path_bean",
        trigger="after-previous",
        delay=0.2,
    )
    tools["add_pptx_animation"](
        path="deck.pptx", slide=1, shape_index=0, animation="exit_bounce", trigger="after-previous"
    )
    tools["add_pptx_animation"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        animation="entrance_fly",
        by_paragraph=True,
        trigger="on-click",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(tmp_path / "deck.pptx")
        assert len(prs.slides) == 1

    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(tmp_path / "deck.pptx"),
        ],
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "deck.pdf").is_file()
