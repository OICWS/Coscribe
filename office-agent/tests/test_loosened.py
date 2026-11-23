"""scripts/loosened.py: what counts as loosening a limit only the maintainer may raise."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "loosened.py"


@pytest.fixture(scope="module")
def loosened() -> ModuleType:
    spec = importlib.util.spec_from_file_location("loosened", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["loosened"] = module
    spec.loader.exec_module(module)
    return module


def test_a_worse_or_new_baseline_number_is_loosening_and_a_better_one_is_not(
    loosened: ModuleType,
) -> None:
    before = {"file_lines": {"a.py": 900, "b.py": 950}}
    after = {"file_lines": {"a.py": 901, "b.py": 800, "c.py": 820}}
    assert loosened.baseline(before, after) == [
        "quality/baseline.json: file_lines: a.py 900 -> 901",
        "quality/baseline.json: file_lines: new c.py = 820",
    ]
    assert loosened.baseline(after, {"file_lines": {"a.py": 900}}) == []


def test_a_raised_or_removed_budget_is_loosening(loosened: ModuleType) -> None:
    before = {"core_lines": 100000, "component_lines": 20000}
    assert loosened.budgets(before, {"core_lines": 120000}) == [
        "quality/budgets.json: core_lines 100000 -> 120000",
        "quality/budgets.json: component_lines removed",
    ]
    assert loosened.budgets(before, {"core_lines": 90000, "component_lines": 20000}) == []


def test_an_import_exception_or_a_component_leaving_the_core_is_loosening(
    loosened: ModuleType,
) -> None:
    before = {"component": [{"name": "web", "core": True, "ignore_imports": ["a -> b"]}]}
    after = {"component": [{"name": "web", "ignore_imports": ["a -> b", "c -> d"]}]}
    assert loosened.components(before, after) == [
        "components.toml ignore_imports: added web: c -> d",
        "components.toml: web is no longer core",
    ]
    assert loosened.components(after, before) == []


def test_turning_a_check_off_in_pyproject_is_loosening(loosened: ModuleType) -> None:
    before = {
        "tool": {
            "coverage": {"report": {"fail_under": 88}},
            "mypy": {
                "strict": True,
                "overrides": [{"module": "x.*", "ignore_missing_imports": True}],
            },
            "ruff": {"lint": {"per-file-ignores": {"a.py": ["E501"]}}},
        }
    }
    after = {
        "tool": {
            "coverage": {"report": {"fail_under": 85}},
            "mypy": {
                "strict": False,
                "overrides": [
                    {"module": "x.*", "ignore_missing_imports": True},
                    {"module": ["coscribe.web"], "ignore_errors": True},
                ],
            },
            "ruff": {"lint": {"per-file-ignores": {"a.py": ["E501", "B008"]}, "ignore": ["E"]}},
        }
    }
    assert loosened.pyproject(before, after) == [
        "pyproject.toml: coverage fail_under 88 -> 85",
        "pyproject.toml ruff per-file-ignores: added a.py B008",
        "pyproject.toml ruff.lint.ignore: added E",
        "pyproject.toml: mypy strict turned off",
        "pyproject.toml mypy overrides: added coscribe.web ignore_errors=True",
    ]
    assert loosened.pyproject(after, before) == []


def _run(loosened: ModuleType, monkeypatch: pytest.MonkeyPatch, body: str, labels: str) -> int:
    monkeypatch.setattr(loosened, "loosenings", lambda base, head: ["budgets: x 1 -> 2"])
    monkeypatch.setenv("PR_BODY", body)
    monkeypatch.setenv("PR_LABELS", labels)
    return int(loosened.main(["--base", "a", "--head", "b"]))


def test_a_loosening_passes_only_with_a_reason_and_the_maintainers_label(
    loosened: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    reason = "## What\nLoosened: the catalog grew with the 12 presets.\n"
    assert _run(loosened, monkeypatch, reason, "loosening-approved,ci") == 0
    assert _run(loosened, monkeypatch, reason, "ci") == 1
    assert _run(loosened, monkeypatch, "no reason", "loosening-approved") == 1


def test_the_real_history_reads(loosened: ModuleType) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SCRIPT.parent, capture_output=True, text=True
    ).stdout.strip()
    assert loosened.loosenings(head, head) == []
