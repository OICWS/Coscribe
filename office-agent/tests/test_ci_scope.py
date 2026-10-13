"""Which pull requests may skip the full CI run (`scripts/ci_scope.py`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

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
        ["docs/plan.md", "office-agent/src/coscribe/cli.py"],
        ["office-agent/src/coscribe/builtin_skills/pptx/SKILL.md"],
        ["office-agent/src/coscribe/tools/README.md"],
        ["office-agent/tests/golden/pptx/bullets.txt"],
        [".github/workflows/office-agent-ci.yml"],
        ["office-agent/frontend/README.md"],
        ["office-agent/quality/baseline.json"],
    ],
)
def test_anything_else_runs_everything(paths: list[str]) -> None:
    assert ci_scope.scope(paths) == "full"


def test_the_docs_tests_exist() -> None:
    root = SCRIPTS.parent
    assert all((root / name).is_file() for name in ci_scope.DOCS_TESTS)
