from pathlib import Path

import pytest

from tests.libreoffice_probe import convert_with_libreoffice

from .helpers import (
    _P14_NS,
    _P_NS,
    _libreoffice_actually_works,
    _tools_by_name,
)

_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


_P15_NS = "http://schemas.microsoft.com/office/powerpoint/2012/main"


_P159_NS = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"


def test_set_pptx_transition_adds_transition_element(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade", duration=0.8)

    prs = Presentation(tmp_path / "deck.pptx")
    transition_el = prs.slides[0].element.find(f"{{{_P_NS}}}transition")
    assert transition_el is not None
    assert [c.tag.split("}")[-1] for c in transition_el] == ["fade"]
    # p14:dur is a PowerPoint-2010 extension attribute with no home in the
    # base ECMA-376 schema -- valid OOXML only because mc:Ignorable marks
    # its namespace prefix ignorable (see _mark_mce_ignorable's docstring).
    # A real slide always carries both together, not just the attribute.
    assert (prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") or "").split() == ["p14"]


def test_set_pptx_transition_none_removes_any_existing_transition(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="none")

    prs = Presentation(tmp_path / "deck.pptx")
    assert prs.slides[0].element.find(f"{{{_P_NS}}}transition") is None
    # No p14: content left on the slide -- mc:Ignorable shouldn't still
    # claim there is any.
    assert prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") is None


def test_set_pptx_transition_replaces_rather_than_duplicates(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="wipe")

    prs = Presentation(tmp_path / "deck.pptx")
    transitions = prs.slides[0].element.findall(f"{{{_P_NS}}}transition")
    assert len(transitions) == 1
    assert [c.tag.split("}")[-1] for c in transitions[0]] == ["wipe"]


def test_set_pptx_transition_rejects_unknown_transition(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="Unknown transition"):
        tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="not-a-real-transition")


def test_set_pptx_transition_supports_a_p14_extension_effect(tmp_path: Path) -> None:
    """ "vortex" lives in the PowerPoint-2010 extension namespace (p14),
    not the base ECMA-376 "p" namespace fade/push/wipe use -- both the
    effect element itself and the p14:dur attribute need mc:Ignorable."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="vortex", duration=0.8)

    prs = Presentation(tmp_path / "deck.pptx")
    transition_el = prs.slides[0].element.find(f"{{{_P_NS}}}transition")
    assert transition_el is not None
    effect = transition_el[0]
    assert effect.tag == f"{{{_P14_NS}}}vortex"
    assert effect.get("dir") == "r"
    assert (prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") or "").split() == ["p14"]


def test_set_pptx_transition_supports_a_p159_extension_effect(tmp_path: Path) -> None:
    """ "morph" is the one native transition in the newest (2015/09,
    p159) extension namespace."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="morph")

    prs = Presentation(tmp_path / "deck.pptx")
    transition_el = prs.slides[0].element.find(f"{{{_P_NS}}}transition")
    effect = transition_el[0]
    assert effect.tag == f"{{{_P159_NS}}}morph"
    ignorable = (prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") or "").split()
    assert set(ignorable) == {"p14", "p159"}


def test_every_ignorable_prefix_is_declared_on_the_slide_root(tmp_path: Path) -> None:
    """PowerPoint asks to repair a slide whose mc:Ignorable names a prefix only a descendant
    declares (found on Windows with a Morph transition); the saved root must declare each one."""
    import zipfile

    from lxml import etree

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="morph")

    with zipfile.ZipFile(tmp_path / "deck.pptx") as package:
        root = etree.fromstring(package.read("ppt/slides/slide1.xml"))
    ignorable = (root.get(f"{{{_MC_NS}}}Ignorable") or "").split()
    assert ignorable and all(prefix in root.nsmap for prefix in ignorable)
    assert root.nsmap["p159"] == _P159_NS


def test_set_pptx_transition_switching_namespaces_cleans_up_the_old_prefix(
    tmp_path: Path,
) -> None:
    """p14 -> p15 -> base "p": each switch must leave mc:Ignorable naming
    only the prefix(es) the *current* transition actually uses, not a
    stale leftover from whichever effect was set before it."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="vortex")  # p14
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fracture")  # p15
    prs = Presentation(tmp_path / "deck.pptx")
    ignorable = (prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") or "").split()
    assert set(ignorable) == {"p14", "p15"}

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade")  # base "p"
    prs = Presentation(tmp_path / "deck.pptx")
    ignorable = (prs.slides[0].element.get(f"{{{_MC_NS}}}Ignorable") or "").split()
    assert ignorable == ["p14"]  # only the p14:dur attribute remains foreign


def test_set_pptx_transition_resolves_legacy_aliases(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="wheel")  # alias for "clock"

    prs = Presentation(tmp_path / "deck.pptx")
    transition_el = prs.slides[0].element.find(f"{{{_P_NS}}}transition")
    effect = transition_el[0]
    assert effect.tag == f"{{{_P_NS}}}wheel"
    assert effect.get("spokes") == "1"


def test_set_pptx_transition_writes_the_registered_effect_for_every_transition(
    tmp_path: Path,
) -> None:
    """Every single one of the 48 native transitions + 8 aliases actually
    produces schema-valid OOXML (via the real assert_ooxml_valid call
    set_pptx_transition itself makes) -- not just the few spot-checked
    above. A real, cheap way to catch a typo'd element/attribute name
    across the whole retyped registry at once."""
    from coscribe.tools.office.pptx.transitions import TRANSITION_ALIASES, TRANSITION_SPECS

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    from lxml import etree
    from pptx import Presentation

    for transition in (*TRANSITION_SPECS, *TRANSITION_ALIASES):
        tools["set_pptx_transition"](path="deck.pptx", slide=1, transition=transition)

        spec = TRANSITION_SPECS[TRANSITION_ALIASES.get(transition, transition)]
        slide_el = Presentation(tmp_path / "deck.pptx").slides[0].element
        transitions = slide_el.findall(f"{{{_P_NS}}}transition")
        assert len(transitions) == 1, transition
        effects = [etree.QName(child).localname for child in transitions[0]]
        assert effects == [spec["element"].split(":")[-1]], transition


def test_list_pptx_transition_types_matches_the_real_registry(tmp_path: Path) -> None:
    from coscribe.tools.office.pptx.transitions import TRANSITION_ALIASES, TRANSITION_SPECS

    tools = _tools_by_name(tmp_path)

    result = tools["list_pptx_transition_types"]()

    assert result == sorted({*TRANSITION_SPECS, *TRANSITION_ALIASES})
    assert "none" not in result
    assert len(result) == 48 + 8


def test_set_pptx_transition_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["set_pptx_transition"](path="deck.pptx", slide=5, transition="fade")


def test_set_pptx_transition_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["set_pptx_transition"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_set_pptx_transition_survives_libreoffice_conversion(tmp_path: Path) -> None:

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade", duration=0.8)

    convert_with_libreoffice(tmp_path / "deck.pptx", tmp_path)
    assert (tmp_path / "deck.pdf").is_file()


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_set_pptx_transition_exotic_effects_survive_libreoffice_conversion(
    tmp_path: Path,
) -> None:
    """A mix across all 4 namespace tiers (base "p", p14, p15, p159) plus
    a legacy alias, on one real 5-slide deck -- not just the single base
    "fade" case above. Can't verify the transition *animation* itself in
    a static test (that needs a human watching real PowerPoint/LibreOffice
    play it back), but a real subprocess conversion succeeding, plus a
    warnings-as-errors python-pptx round-trip, is the strongest automated
    check available: it proves the file isn't corrupted the way a
    hand-XML mistake across a 48-entry retyped registry plausibly could
    produce for at least one entry."""
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](
        path="deck.pptx",
        content="# S1\n- a\n---\n# S2\n- b\n---\n# S3\n- c\n---\n# S4\n- d\n---\n# S5\n- e",
    )
    for slide, transition in enumerate(["vortex", "fracture", "morph", "fade", "wheel"], start=1):
        tools["set_pptx_transition"](
            path="deck.pptx", slide=slide, transition=transition, duration=0.7
        )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(tmp_path / "deck.pptx")
        assert len(prs.slides) == 5

    convert_with_libreoffice(tmp_path / "deck.pptx", tmp_path)
    assert (tmp_path / "deck.pdf").is_file()
