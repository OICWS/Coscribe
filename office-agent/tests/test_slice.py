"""`scripts/slice.py` applies the component map to one path: the card, the interface, the tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "slice.py"
spec = importlib.util.spec_from_file_location("slice_script", SCRIPT)
assert spec and spec.loader
slice_script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = slice_script
spec.loader.exec_module(slice_script)


def test_a_file_resolves_to_its_most_specific_component() -> None:
    items = slice_script.components()
    path = "office-agent/src/coscribe/tools/office/docx/tools.py"
    assert slice_script.owning_component(path, items)["name"] == "tools.office.docx"
    other = "office-agent/src/coscribe/tools/files.py"
    assert slice_script.owning_component(other, items)["name"] == "tools"
    assert slice_script.owning_component("README.md", items) is None


def test_the_slice_of_a_docx_file_names_its_card_interface_and_tests(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = slice_script.main(["office-agent/src/coscribe/tools/office/docx/tools.py"])
    out = capsys.readouterr().out
    assert code == 0
    assert "component: tools.office.docx" in out
    assert "tools/office/docx/AGENTS.md" in out
    assert "build_docx_tools" in out
    assert "tests/test_docx_review_tool.py" in out


def test_a_frontend_file_lists_its_sibling_unit_test(capsys: pytest.CaptureFixture[str]) -> None:
    slice_script.main(["office-agent/frontend/src/lib/dockLayout.ts"])
    assert "frontend/src/lib/dockLayout.test.ts" in capsys.readouterr().out


def test_a_path_outside_every_component_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    assert slice_script.main(["README.md"]) == 1
    assert "not in any component" in capsys.readouterr().out


def test_a_packages_interface_leaves_out_what_its_sub_components_export() -> None:
    items = slice_script.components()
    tools = next(item for item in items if item["name"] == "tools")

    own, reexported = slice_script.public_names(tools)

    assert "build_file_tools" in own
    assert "run_python_script" not in own
    assert reexported > len(own)
