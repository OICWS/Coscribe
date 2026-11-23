"""Check that the tests a pull request would select include every test its change can break.

For each module picked, every function and method in it is made to raise on its first line,
the whole suite runs, and each test that fails is looked up in what `ci_scope.py` selects for a
change to that module. A failing test that was not selected is a dependency the import graph
missed (decision 0059): the run fails and names it.

    python scripts/selection_audit.py --pick 3 --seed 2026-11-23    # what the nightly run does
    python scripts/selection_audit.py src/coscribe/tools/office/pdf/__init__.py

The module is restored afterwards, also when the run is stopped.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import random
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("ci_scope", ROOT / "scripts" / "ci_scope.py")
assert _spec is not None and _spec.loader is not None
ci_scope = importlib.util.module_from_spec(_spec)
sys.modules["ci_scope"] = ci_scope
_spec.loader.exec_module(ci_scope)

MARK = "selection audit"
# Vendored code is left alone (scripts/ratchet.py), and a module this small has nothing to break.
SKIPPED = ("tools/_native_",)
MIN_FUNCTIONS = 3


class _Raise(ast.NodeTransformer):
    def __init__(self) -> None:
        self.count = 0

    def _visit(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit(node)
        raise_ = ast.parse(f"raise RuntimeError({MARK!r})").body[0]
        body = node.body
        # A docstring stays first, so `__doc__` (the tool schemas read it) is unchanged.
        keep = (
            1
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            else 0
        )
        node.body = [*body[:keep], raise_, *body[keep:]]
        self.count += 1
        return node

    visit_FunctionDef = _visit
    visit_AsyncFunctionDef = _visit


def broken(source: str) -> tuple[str, int]:
    tree = ast.parse(source)
    transformer = _Raise()
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), transformer.count


def candidates() -> list[str]:
    found = []
    for path in sorted((ROOT / "src" / "coscribe").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if any(s in rel for s in SKIPPED):
            continue
        if broken(path.read_text(encoding="utf-8"))[1] >= MIN_FUNCTIONS:
            found.append(rel)
    return found


def imports_cleanly(rel: str) -> bool:
    module = ci_scope.module_of(ci_scope.PREFIX + rel)
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], cwd=ROOT, capture_output=True, text=True
    )
    return result.returncode == 0


def failing_tests(junit: Path) -> set[str]:
    failed = set()
    for case in ET.parse(junit).getroot().iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        parts = (case.get("classname") or "").split(".")
        for i in range(len(parts), 0, -1):
            candidate = "/".join(parts[:i]) + ".py"
            if (ROOT / candidate).is_file():
                failed.add(candidate)
                break
    return failed


def audit(rel: str, pytest_args: list[str]) -> list[str]:
    """The failing test files a change to `rel` would not have run."""
    path = ROOT / rel
    original = path.read_text(encoding="utf-8")
    selected = set(ci_scope.plan([ci_scope.PREFIX + rel])[1])
    text, count = broken(original)
    print(f"== {rel}: {count} functions raise; {len(selected)} test files selected", flush=True)
    try:
        path.write_text(text, encoding="utf-8")
        if not imports_cleanly(rel):
            print("   skipped: the module runs its own functions on import", flush=True)
            return []
        with tempfile.TemporaryDirectory() as tmp:
            junit = Path(tmp) / "junit.xml"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    f"--junitxml={junit}",
                    *pytest_args,
                ],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            failed = failing_tests(junit) if junit.is_file() else set()
    finally:
        path.write_text(original, encoding="utf-8")
    missed = sorted(failed - selected)
    print(f"   {len(failed)} test files failed; not selected: {missed or 'none'}", flush=True)
    return missed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("modules", nargs="*", help="paths under office-agent/")
    parser.add_argument("--pick", type=int, default=0, help="also pick this many at random")
    parser.add_argument("--seed", default="", help="the random pick's seed (the date, nightly)")
    parser.add_argument("--pytest-args", default="-n 4", help="passed on to pytest")
    args = parser.parse_args(argv)
    modules = list(args.modules)
    if args.pick:
        pool = [m for m in candidates() if m not in modules]
        modules += random.Random(args.seed).sample(pool, min(args.pick, len(pool)))
    misses = {m: audit(m, args.pytest_args.split()) for m in modules}
    misses = {m: t for m, t in misses.items() if t}
    for module, tests in misses.items():
        print(f"::error::A change to {module} breaks {', '.join(tests)}, which it does not select.")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
