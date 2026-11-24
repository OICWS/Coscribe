"""scripts/selection_audit.py: how a module is broken for the audit of decision 0059."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "selection_audit.py"


@pytest.fixture(scope="module")
def audit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("selection_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["selection_audit"] = module
    spec.loader.exec_module(module)
    return module


SOURCE = '''
def tool(x):
    """The docstring a tool schema is read from."""
    return x


class Box:
    async def open(self):
        return 1

    def close(self):
        def inner():
            return 2
        return inner()
'''


def test_every_function_raises_and_keeps_its_docstring(audit: ModuleType) -> None:
    text, count = audit.broken(SOURCE)
    assert count == 4
    namespace: dict[str, object] = {}
    exec(compile(text, "<audit>", "exec"), namespace)
    tool = namespace["tool"]
    assert tool.__doc__ == "The docstring a tool schema is read from."
    with pytest.raises(RuntimeError, match="selection audit"):
        tool(1)
    box = namespace["Box"]()
    with pytest.raises(RuntimeError, match="selection audit"):
        box.close()


def test_a_failing_test_file_is_read_from_the_junit_report(
    audit: ModuleType, tmp_path: Path
) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="tests.test_ci_scope" name="a"><failure/></testcase>'
        '<testcase classname="tests.test_ci_scope" name="b"/>'
        '<testcase classname="tests.test_ratchet" name="c"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert audit.failing_tests(junit) == {"tests/test_ci_scope.py"}


def test_the_candidates_leave_vendored_code_alone(audit: ModuleType) -> None:
    found = audit.candidates()
    assert found and not any("_native_" in path for path in found)
