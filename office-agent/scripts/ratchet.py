#!/usr/bin/env python3
"""A ratchet: numbers about the code that may only get better.

`quality/baseline.json` holds what each number was when it was last accepted.
This script measures the code again and compares:

    python scripts/ratchet.py            print the comparison, never fail
    python scripts/ratchet.py --enforce  exit 1 if any number got worse
    python scripts/ratchet.py --update   write the measured numbers as the baseline

Nothing existing has to be fixed first: today's offenders are the baseline, and
only new or growing ones count as worse. The baseline file is a CODEOWNERS path:
raising a number there loosens the rule, and only a human may approve that
(decision 0009).

Every metric is a mapping from a name to a number, so "worse" is the same
everywhere: a name that is new, or a number that grew.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coscribe"
TESTS = ROOT / "tests"
BASELINE = ROOT / "quality" / "baseline.json"

# Files above this are listed; one function above it is listed too.
FILE_LINES_LISTED = 800
FUNCTION_LINES_LISTED = 100
COMPLEXITY_LISTED = 15

# Vendored code is left alone so a diff against its upstream stays meaningful.
VENDORED = ("tools/_native_formula/", "tools/_native_docx_tracks/", "providers/gemini_provider.py")

SUPPRESSIONS = {
    "type_ignore": re.compile(r"#\s*type:\s*ignore"),
    "noqa": re.compile(r"#\s*noqa"),
    "pragma_no_cover": re.compile(r"#\s*pragma:\s*no cover"),
}


def _python_files(root: Path, *, skip_vendored: bool) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if skip_vendored and any(rel.startswith(v) for v in VENDORED):
            continue
        yield path


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def file_lines(src: Path = SRC, listed: int = FILE_LINES_LISTED) -> dict[str, int]:
    sizes = {
        _rel(p): len(p.read_text(encoding="utf-8").splitlines())
        for p in _python_files(src, skip_vendored=True)
    }
    return {name: n for name, n in sizes.items() if n > listed}


def _functions(tree: ast.Module) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    def walk(
        node: ast.AST, prefix: str
    ) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                yield from walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                yield f"{prefix}{child.name}", child
                yield from walk(child, f"{prefix}{child.name}.")

    yield from walk(tree, "")


def long_functions(src: Path = SRC, listed: int = FUNCTION_LINES_LISTED) -> dict[str, int]:
    found: dict[str, int] = {}
    for path in _python_files(src, skip_vendored=True):
        tree = _parse(path)
        if tree is None:
            continue
        for name, node in _functions(tree):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > listed:
                found[f"{_rel(path)}::{name}"] = length
    return found


def complex_functions(src: Path = SRC, listed: int = COMPLEXITY_LISTED) -> dict[str, int]:
    """McCabe complexity from ruff's C901, so the number is the one a contributor sees."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--select",
            "C901",
            "--config",
            f"lint.mccabe.max-complexity = {listed}",
            "--output-format",
            "json",
            str(src),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if not result.stdout.strip():
        return {}
    found: dict[str, int] = {}
    for item in json.loads(result.stdout):
        path = Path(item["filename"])
        if any(_rel(path).removeprefix("src/coscribe/").startswith(v) for v in VENDORED):
            continue
        match = re.search(r"`(.+)` is too complex \((\d+)", item["message"])
        if match:
            found[f"{_rel(path)}::{match.group(1)}"] = int(match.group(2))
    return found


def suppressions(src: Path = SRC) -> dict[str, int]:
    counts = dict.fromkeys(SUPPRESSIONS, 0)
    for path in _python_files(src, skip_vendored=True):
        for line in path.read_text(encoding="utf-8").splitlines():
            for name, pattern in SUPPRESSIONS.items():
                if pattern.search(line):
                    counts[name] += 1
    return counts


def _module_name(path: Path, src: Path) -> str:
    parts = list(path.relative_to(src.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _component(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else parts[0]


def deep_imports(src: Path = SRC) -> dict[str, int]:
    """Imports that reach into another package's submodule instead of the package
    itself (`coscribe.tools.documents` from `coscribe.web`, not `coscribe.tools`),
    keyed `importer -> imported`, plus imports of private names across packages."""
    found: dict[str, int] = {}
    for path in _python_files(src, skip_vendored=True):
        tree = _parse(path)
        if tree is None:
            continue
        importer = _module_name(path, src)
        here = _component(importer)
        for node in ast.walk(tree):
            targets: list[tuple[str, list[str]]] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level:
                    base = importer.split(".")
                    if path.name != "__init__.py":
                        base = base[:-1]
                    base = base[: len(base) - (node.level - 1)]
                    module = ".".join([*base, node.module])
                else:
                    module = node.module
                targets.append((module, [a.name for a in node.names]))
            elif isinstance(node, ast.Import):
                targets.extend((a.name, []) for a in node.names)
            for module, names in targets:
                if not module.startswith("coscribe."):
                    continue
                if _component(module) == here:
                    continue
                if module.count(".") >= 2:
                    key = f"{importer} -> {module}"
                    found[key] = found.get(key, 0) + 1
                for name in names:
                    if name.startswith("_") and not name.startswith("__"):
                        key = f"{importer} -> {module}:{name}"
                        found[key] = found.get(key, 0) + 1
    return found


def _has_check(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            callee = ast.unparse(node.func)
            if callee.endswith(("pytest.raises", "pytest.warns", "pytest.fail", "pytest.skip")):
                return True
            if re.search(r"\.assert_\w+$|\.assertEqual$|\.assertTrue$", callee):
                return True
    return False


def tests_without_a_check(tests: Path = TESTS) -> dict[str, int]:
    found: dict[str, int] = {}
    for path in _python_files(tests, skip_vendored=False):
        tree = _parse(path)
        if tree is None:
            continue
        for name, node in _functions(tree):
            if name.split(".")[-1].startswith("test_") and not _has_check(node):
                found[f"{_rel(path)}::{name}"] = 1
    return found


def patch_by_string(tests: Path = TESTS) -> dict[str, int]:
    """`monkeypatch.setattr("coscribe.x.y", ...)`: breaks silently when the thing moves."""
    pattern = re.compile(r"monkeypatch\.(?:setattr|delattr)\(\s*[\"']coscribe\.")
    found: dict[str, int] = {}
    for path in _python_files(tests, skip_vendored=False):
        count = len(pattern.findall(path.read_text(encoding="utf-8")))
        if count:
            found[_rel(path)] = count
    return found


METRICS = {
    "file_lines": file_lines,
    "long_functions": long_functions,
    "complex_functions": complex_functions,
    "suppressions": suppressions,
    "deep_imports": deep_imports,
    "tests_without_a_check": tests_without_a_check,
    "patch_by_string": patch_by_string,
}


def measure() -> dict[str, dict[str, int]]:
    return {name: function() for name, function in METRICS.items()}


def compare(
    baseline: dict[str, dict[str, int]], measured: dict[str, dict[str, int]]
) -> tuple[list[str], list[str]]:
    """(worse, better): a name that is new or a number that grew, and the opposite."""
    worse: list[str] = []
    better: list[str] = []
    for metric, now in measured.items():
        before = baseline.get(metric, {})
        for name, value in sorted(now.items()):
            if name not in before:
                worse.append(f"{metric}: new  {name} = {value}")
            elif value > before[name]:
                worse.append(f"{metric}: {name} grew {before[name]} -> {value}")
            elif value < before[name]:
                better.append(f"{metric}: {name} {before[name]} -> {value}")
        for name in sorted(set(before) - set(now)):
            better.append(f"{metric}: {name} is gone (was {before[name]})")
    return worse, better


def _summary(measured: dict[str, dict[str, int]]) -> str:
    return ", ".join(f"{name} {len(items)}" for name, items in measured.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--enforce", action="store_true", help="exit 1 if any number got worse")
    parser.add_argument(
        "--update", action="store_true", help="write the measured numbers as the baseline"
    )
    args = parser.parse_args(argv)

    measured = measure()
    if args.update:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(measured, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Baseline written: {_summary(measured)}")
        return 0
    if not BASELINE.is_file():
        print("No quality/baseline.json yet; run with --update to create it.")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    worse, better = compare(baseline, measured)
    print(f"Ratchet: {_summary(measured)}")
    for line in worse:
        print(f"  WORSE  {line}")
    for line in better:
        print(f"  better {line}")
    if better:
        print(
            "  Some numbers improved: run `python scripts/ratchet.py --update` and commit the baseline."
        )
    if worse:
        print("  Fix what got worse. Raising the baseline loosens the rule: a human approves that.")
    return 1 if (worse and args.enforce) else 0


if __name__ == "__main__":
    raise SystemExit(main())
