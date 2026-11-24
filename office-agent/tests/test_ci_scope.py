"""Which tests a pull request runs (`scripts/ci_scope.py`, decision 0059)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_spec = importlib.util.spec_from_file_location("ci_scope", SCRIPTS / "ci_scope.py")
assert _spec is not None and _spec.loader is not None
ci_scope = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci_scope)


@pytest.mark.parametrize(
    "paths",
    [
        ["docs/plan.md"],
        [
            "docs/assessments/2026-10-13-office-route.md",
            "docs/assessments/x/scripts/a.py",
            "docs/x/a.jpg",
        ],
        ["AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md"],
        ["office-agent/CLAUDE.md", "office-agent/PPTX_DESIGN.md"],
        [
            "office-agent/src/coscribe/workflows/AGENTS.md",
            "office-agent/src/coscribe/workflows/CLAUDE.md",
        ],
    ],
)
def test_documentation_only_needs_the_docs_tests(paths: list[str]) -> None:
    assert ci_scope.scope(paths) == "docs"


@pytest.mark.parametrize(
    "paths",
    [
        [],
        ["docs/plan.md", "office-agent/pyproject.toml"],
        ["office-agent/uv.lock"],
        ["office-agent/tests/conftest.py"],
        ["office-agent/tests/web/conftest.py"],
        [".github/workflows/office-agent-ci.yml"],
        [".github/workflows/windows.yml"],
        ["office-agent/scripts/check.sh"],
        # Split, so this file does not name it.
        ["office-agent/" + "nobody-" + "names-this.txt"],
    ],
)
def test_what_changes_how_every_test_runs_runs_everything(paths: list[str]) -> None:
    assert ci_scope.scope(paths) == "full"


def test_the_listed_tests_exist() -> None:
    root = SCRIPTS.parent
    assert all((root / name).is_file() for name in ci_scope.ALWAYS)


# A small tree laid out like the repository: office-agent/{src/coscribe,tests}.
TREE = {
    "src/coscribe/__init__.py": "",
    "src/coscribe/base.py": "def helper():\n    return 1\n",
    "src/coscribe/fixture_target.py": "from coscribe.base import helper\nSTATE = {}\n",
    "src/coscribe/office/__init__.py": (
        '"""The interface."""\n'
        "from .deck import make_deck\n"
        "from .sheet import make_sheet\n"
        '__all__ = ["make_deck", "make_sheet"]\n'
    ),
    "src/coscribe/office/deck.py": "from coscribe.base import helper\ndef make_deck(): ...\n",
    "src/coscribe/office/sheet.py": "def make_sheet(): ...\n",
    "src/coscribe/office/layouts.json": "{}",
    "src/coscribe/app.py": "from .office import make_sheet\nRUNNING = make_sheet\n",
    "src/coscribe/wired/__init__.py": "from .parts import part\nREGISTRY = [part]\n",
    "src/coscribe/wired/parts.py": "def part(): ...\n",
    "src/coscribe/wired/other.py": "def other(): ...\n",
    "tests/__init__.py": "",
    "tests/conftest.py": "from coscribe import fixture_target\n",
    "tests/helpers.py": "from coscribe.office import make_deck\n",
    "tests/test_deck.py": "from coscribe.office import make_deck\n",
    "tests/test_sheet.py": "from coscribe.office import make_sheet\n",
    "tests/test_app.py": "import coscribe.app\n",
    "tests/test_by_string.py": 'TARGET = "coscribe.office.sheet.make_sheet"\n',
    "tests/test_via_helper.py": "from .helpers import *\n",
    "tests/test_frontend_text.py": 'BUILD = "frontend/dist"\n',
    "tests/test_reads_a_file.py": 'NAME = "notes.txt"\n',
    "tests/test_gone.py": "from coscribe.removed import thing\n",
    "tests/test_wired.py": "from coscribe.wired import other\n",
    "tests/test_doc_references.py": "",
}


@pytest.fixture
def graph(tmp_path: Path) -> Any:
    root = tmp_path / "office-agent"
    for rel, text in TREE.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / "scripts").mkdir()
    return ci_scope.Graph.build(root)


def _selected(graph: Any, *paths: str) -> set[str] | None:
    tests = graph.select(["office-agent/" + p for p in paths])
    if tests is None:
        return None
    return {t.removeprefix("tests/").removesuffix(".py") for t in tests if t not in ci_scope.ALWAYS}


def test_a_module_behind_an_interface_selects_only_the_tests_that_use_it(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/office/deck.py") == {"test_deck", "test_via_helper"}
    assert _selected(graph, "src/coscribe/office/sheet.py") == {
        "test_sheet",
        "test_app",
        "test_by_string",
    }


def test_the_interface_itself_selects_every_test_that_imports_it(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/office/__init__.py") == {
        "test_deck",
        "test_sheet",
        "test_app",
        "test_via_helper",
    }


def test_a_change_reaches_through_every_module_that_imports_it(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/base.py") == {"test_deck", "test_via_helper"}


def test_a_package_that_runs_code_is_a_dependency_as_a_whole(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/wired/parts.py") == {"test_wired"}
    assert _selected(graph, "src/coscribe/wired/other.py") == {"test_wired"}


def test_a_module_the_conftest_names_selects_every_test_but_its_imports_do_not(
    graph: Any,
) -> None:
    every = _selected(graph, "src/coscribe/fixture_target.py")
    assert every is not None and {"test_deck", "test_sheet", "test_gone", "test_wired"} <= every
    assert "test_wired" not in (_selected(graph, "src/coscribe/base.py") or set())


def test_a_data_file_belongs_to_its_package(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/office/layouts.json") == _selected(
        graph, "src/coscribe/office/__init__.py"
    )


def test_a_changed_test_runs_itself(graph: Any) -> None:
    assert _selected(graph, "tests/test_sheet.py") == {"test_sheet"}
    assert _selected(graph, "tests/helpers.py") == {"test_via_helper"}


def test_a_deleted_module_selects_the_tests_still_importing_it(graph: Any) -> None:
    assert _selected(graph, "src/coscribe/removed.py") == {"test_gone"}


def test_a_file_outside_python_is_found_by_its_name_or_runs_everything(graph: Any) -> None:
    assert _selected(graph, "frontend/src/App.tsx") == {"test_frontend_text"}
    assert _selected(graph, "tests/fixtures/notes.txt") == {"test_reads_a_file"}
    assert _selected(graph, "tests/fixtures/unnamed.bin") is None


def test_the_tests_that_read_the_whole_tree_always_run(graph: Any) -> None:
    tests = graph.select(["office-agent/src/coscribe/wired/other.py"])
    assert "tests/test_doc_references.py" in tests


def test_the_real_tree_places_a_change_to_one_office_format_away_from_the_others() -> None:
    graph = ci_scope.Graph.build(ci_scope.ROOT)
    tests = graph.select(["office-agent/src/coscribe/tools/office/pdf/__init__.py"])
    assert tests is not None
    assert "tests/test_xlsx_golden.py" not in tests
