"""scripts/pr_gates.py: changed-line coverage, fails-before and the independent review link."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pr_gates.py"


@pytest.fixture(scope="module")
def gates() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pr_gates", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pr_gates"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("lines", "percent", "ok"),
    [(4, 0.0, True), (5, 79.9, False), (5, 80.0, True), (200, 100.0, True), (0, None, True)],
)
def test_changed_lines_are_80_percent_covered_from_5_lines(
    gates: ModuleType, lines: int, percent: float | None, ok: bool
) -> None:
    report = {"total_num_lines": lines, "total_percent_covered": percent}
    assert gates.coverage(report)[0] is ok


def test_a_reason_line_in_the_description_names_why_a_rule_does_not_apply(
    gates: ModuleType,
) -> None:
    body = "## Not verified\nFails before: a pure move of the routes.\n"
    assert gates.exemption("Fails before", body) == "a pure move of the routes."
    assert gates.exemption("Changed-line coverage", body) is None
    assert gates.exemption("Fails before", "Fails before:\n") is None


def test_code_without_a_changed_test_fails_and_docs_or_tests_alone_pass(
    gates: ModuleType,
) -> None:
    assert gates.fails_before("base", ["docs/plan.md", "office-agent/tests/test_x.py"])[0]
    ok, message = gates.fails_before("base", ["office-agent/src/coscribe/cli.py"])
    assert not ok and "no test file did" in message


def test_failing_and_erroring_tests_are_counted_from_the_junit_report(
    gates: ModuleType, tmp_path: Path
) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="tests.test_a" name="one"><failure/></testcase>'
        '<testcase classname="tests.test_a" name="two"><error/></testcase>'
        '<testcase classname="tests.test_a" name="three"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert gates.failures(junit) == 2


def test_an_invariant_path_needs_a_review_posted_on_this_pull_request(
    gates: ModuleType,
) -> None:
    files = ["office-agent/src/coscribe/runtime/secret_store.py", "docs/plan.md"]
    link = "https://github.com/OICWS/coscribe/pull/12#pullrequestreview-345"
    posted = {345}.__contains__
    assert gates.review(files, f"## Independent review\n{link}\n", 12, posted)[0]
    assert not gates.review(files, "## Independent review\nNot needed.\n", 12, posted)[0]
    assert not gates.review(files, link, 13, posted)[0]  # another pull request's review
    assert not gates.review(files, link, 12, {1}.__contains__)[0]  # no such review
    assert gates.review(["office-agent/src/coscribe/cli.py"], "", 12, posted)[0]


@pytest.mark.parametrize(
    "path",
    [
        "office-agent/src/coscribe/runtime/secrets.py",
        "office-agent/src/coscribe/runtime/secrets_env.py",
        "office-agent/src/coscribe/runtime_lg/tool_deferral.py",
        "office-agent/src/coscribe/runtime_lg/mcp_oauth.py",
        "office-agent/src/coscribe/code_runtime/permissions.py",
        "office-agent/src/coscribe/coordinator.py",
    ],
)
def test_the_invariant_paths_are_the_ones_the_rules_name(gates: ModuleType, path: str) -> None:
    assert any(rule.fullmatch(path) for rule in gates.INVARIANT_PATHS)
    rules = (SCRIPT.parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
    name = path.removeprefix("office-agent/src/coscribe/")
    assert name in rules or name.startswith("runtime/secrets")
