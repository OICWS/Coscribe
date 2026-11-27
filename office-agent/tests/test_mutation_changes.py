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
    assert mutation.changed_lines(diff) == {3, 11, 12, 22, 23}


def test_a_function_that_only_lost_lines_is_still_mutated(mutation: ModuleType) -> None:
    before = "def check(value):\n    if value < 0:\n        raise ValueError\n    return value\n"
    after = "def check(value):\n    return value\n"
    diff = "@@ -2,2 +1,0 @@\n-    if value < 0:\n-        raise ValueError\n"
    assert before != after
    assert mutation.mutant_prefixes(after, mutation.changed_lines(diff)) == ["x_check__mutmut_"]


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


def test_a_decorated_function_is_not_asked_for_since_mutmut_leaves_it_alone(
    mutation: ModuleType,
) -> None:
    source = (
        "@cache\ndef cached():\n    return 1\n\n\n"
        "class Box:\n"
        "    @recorded\n    async def turn(self):\n        return 2\n\n"
        "    @staticmethod\n    def make():\n        return 3\n"
    )

    assert mutation.mutant_prefixes(source, {3, 9, 13}) == ["xǁBoxǁmake__mutmut_"]


def test_protocol_method_declarations_have_no_mutants(mutation: ModuleType) -> None:
    source = "class Host(Protocol):\n    async def deliver(self) -> None: ...\n"
    assert mutation.mutant_prefixes(source, {2}) == []


def test_an_attribute_annotation_alone_does_not_mutate_a_method(mutation: ModuleType) -> None:
    before = "class Session:\n    def __init__(self):\n        self.items: list[str] = []\n"
    after = before.replace("list[str]", "list[Note]")
    assert mutation.mutant_prefixes(after, {3}, before) == []
    changed = after.replace("= []", "= [Note()]")
    assert mutation.mutant_prefixes(changed, {3}, before) == ["xǁSessionǁ__init____mutmut_"]
