"""scripts/mutation.py's pull request run: which functions a diff changed, in mutmut's names."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mutation.py"


@pytest.fixture(scope="module")
def mutation() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mutation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mutation"] = module
    spec.loader.exec_module(module)
    return module


def test_the_new_side_lines_of_each_hunk_are_the_changed_ones(mutation: ModuleType) -> None:
    diff = (
        "--- a/x.py\n+++ b/x.py\n"
        "@@ -3 +3 @@ def a():\n-    return 1\n+    return 2\n"
        "@@ -10,0 +11,2 @@\n+x = 1\n+y = 2\n"
        "@@ -20,3 +22,0 @@\n-gone\n-gone\n-gone\n"
    )
    assert mutation.changed_lines(diff) == {3, 11, 12}


SOURCE = """\
def untouched():
    return 1


def changed(value):
    def inner():
        return value
    return inner()


class Box:
    size = 1

    def kept(self):
        return 1

    async def grown(self):
        return 2
"""


def test_a_changed_line_names_its_function_or_method_as_mutmut_does(
    mutation: ModuleType,
) -> None:
    # Line 7 is inside the nested `inner`: mutmut mutates it as part of `changed`.
    # Line 12 is a class attribute, in no function.
    assert mutation.mutant_prefixes(SOURCE, {7, 12, 18}) == [
        "x_changed__mutmut_",
        "xǁBoxǁgrown__mutmut_",
    ]
    assert mutation.mutant_prefixes(SOURCE, set()) == []
