#!/usr/bin/env python3
"""A ratchet: numbers about the code that may only get better.

`quality/baseline.json` holds what each number was when it was last accepted.
This script measures the code again and compares:

    python scripts/ratchet.py                 print the comparison, never fail
    python scripts/ratchet.py --enforce       exit 1 if any number got worse
    python scripts/ratchet.py --update        write the measured numbers as the baseline,
                                              but only when none of them got worse
    python scripts/ratchet.py --update --accept-worse
                                              write them even though some got worse

Nothing existing has to be fixed first: today's offenders are the baseline, and
only new or growing ones count as worse. The baseline file is a CODEOWNERS path:
raising a number there loosens the rule, and only a human may approve that
(decision 0009). `--update` refuses to write a worse number so that tightening the
baseline cannot loosen it by the way; `--accept-worse` is the maintainer's flag.

Every metric is a mapping from a name to a number, so "worse" is the same
everywhere: a name that is new, or a number that grew.
"""

from __future__ import annotations

import argparse
import ast
import functools
import importlib
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import grimp
import vulture

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coscribe"
TESTS = ROOT / "tests"
BASELINE = ROOT / "quality" / "baseline.json"

# Files above this are listed; one function above it is listed too.
FILE_LINES_LISTED = 800
FUNCTION_LINES_LISTED = 100
COMPLEXITY_LISTED = 15
# Direct imports of other coscribe modules per module (assessment 2.5).
FAN_OUT_LISTED = 25
# vulture's own scale: 60 is "never referenced by name", 100 is "provably unused". Below 60 it
# would also list every import.
DEAD_CODE_CONFIDENCE = 60

# The TypeScript sources, measured with the same limits as the Python.
FRONTEND_DIRS = ("office-agent/frontend/src", "office-agent-desktop/src")

# Vendored code is left alone so a diff against its upstream stays meaningful.
VENDORED = (
    "tools/_native_formula/",
    "tools/_native_docx_tracks/",
    "tools/_native_svg/",
)

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


@functools.cache
def _ts_sizes(repo: Path, dirs: tuple[str, ...]) -> dict[str, dict[str, int]]:
    """Line counts of every TypeScript file and named function, from `ts_sizes.mjs`."""
    if not (Path(__file__).resolve().parents[1] / "frontend/node_modules/typescript").is_dir():
        raise SystemExit("ratchet: the frontend is not installed; run `npm ci` in frontend/ first")
    result = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("ts_sizes.mjs")),
            str(repo),
            *(str(repo / d) for d in dirs),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    sizes: dict[str, dict[str, int]] = json.loads(result.stdout)
    return sizes


def frontend_file_lines(
    repo: Path | None = None, dirs: tuple[str, ...] = FRONTEND_DIRS, listed: int = FILE_LINES_LISTED
) -> dict[str, int]:
    sizes = _ts_sizes(repo or ROOT.parent, dirs)["files"]
    return {name: n for name, n in sizes.items() if n > listed}


def frontend_long_functions(
    repo: Path | None = None,
    dirs: tuple[str, ...] = FRONTEND_DIRS,
    listed: int = FUNCTION_LINES_LISTED,
) -> dict[str, int]:
    sizes = _ts_sizes(repo or ROOT.parent, dirs)["functions"]
    return {name: n for name, n in sizes.items() if n > listed}


def frontend_unused_exports(repo: Path | None = None) -> dict[str, int]:
    """Exports, types and files nothing imports, per file, from knip (frontend/knip.json)."""
    frontend = (repo or ROOT.parent) / "office-agent" / "frontend"
    # npm links a shell script for POSIX and a .cmd shim for Windows; only the shim starts there.
    knip = frontend / "node_modules" / ".bin" / ("knip.cmd" if sys.platform == "win32" else "knip")
    if not knip.is_file():
        raise SystemExit("ratchet: the frontend is not installed; run `npm ci` in frontend/ first")
    # knip exits 1 whenever it finds something, which is the normal case here.
    result = subprocess.run(
        [str(knip), "--include", "exports,types,files,enumMembers", "--reporter", "json"],
        cwd=frontend,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    found: dict[str, int] = {}
    for issue in json.loads(result.stdout)["issues"]:
        count = sum(len(issue[kind]) for kind in ("exports", "types", "files", "enumMembers"))
        if count:
            found[f"office-agent/frontend/{issue['file']}"] = count
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


def fan_out(src: Path = SRC, listed: int = FAN_OUT_LISTED) -> dict[str, int]:
    """Distinct other modules of the package each module imports directly. A package's
    `__init__` counts as the package; external packages are not counted. Too many
    imports in one module is where a read-in-one-session limit and bad splits start."""
    sys.path.insert(0, str(src.parent))
    try:
        importlib.invalidate_caches()
        spec = importlib.util.find_spec(src.name)
        locations = spec.submodule_search_locations if spec else None
        # An installed or already imported copy would make grimp read another tree.
        if locations is not None and src.resolve() not in {Path(p).resolve() for p in locations}:
            raise RuntimeError(f"{src.name} resolves to {list(locations)}, not {src}")
        graph = grimp.build_graph(src.name, cache_dir=None)
    finally:
        sys.path.remove(str(src.parent))
    found: dict[str, int] = {}
    for module in sorted(graph.modules):
        count = len(graph.find_modules_directly_imported_by(module) - {module})
        if count > listed:
            found[module] = count
    return found


def dead_code(src: Path = SRC, confidence: int = DEAD_CODE_CONFIDENCE) -> dict[str, int]:
    """Names vulture finds no reference to, counted per file and kind. Many are not dead: a
    tool the model calls, a route, a Protocol member or a pydantic field is only ever reached
    by name at run time. Those are the baseline (the whitelist), so what the ratchet catches
    is a new unreferenced name. Removing one, or using it, makes the number better."""
    checker = vulture.Vulture()
    files = [str(p) for p in _python_files(src, skip_vendored=True)]
    checker.scavenge(files)
    found: dict[str, int] = {}
    for item in checker.get_unused_code(min_confidence=confidence):
        path = Path(item.filename).resolve().relative_to(src.parent.resolve()).as_posix()
        key = f"{path}::{item.typ} {item.name}"
        found[key] = found.get(key, 0) + 1
    return found


METRICS = {
    "file_lines": file_lines,
    "long_functions": long_functions,
    "complex_functions": complex_functions,
    "frontend_file_lines": frontend_file_lines,
    "frontend_long_functions": frontend_long_functions,
    "frontend_unused_exports": frontend_unused_exports,
    "suppressions": suppressions,
    "deep_imports": deep_imports,
    "tests_without_a_check": tests_without_a_check,
    "patch_by_string": patch_by_string,
    "fan_out": fan_out,
    "dead_code": dead_code,
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
    parser.add_argument(
        "--accept-worse",
        action="store_true",
        help="with --update: also accept numbers that got worse (the maintainer decides)",
    )
    args = parser.parse_args(argv)

    measured = measure()
    if args.update:
        if BASELINE.is_file() and not args.accept_worse:
            worse, _ = compare(json.loads(BASELINE.read_text(encoding="utf-8")), measured)
            if worse:
                for line in worse:
                    print(f"  WORSE  {line}")
                print("Not written: --update only tightens. Fix what got worse, or ask the")
                print("maintainer to run it with --accept-worse.")
                return 1
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
        print("  Some numbers improved: run `python scripts/ratchet.py --update` and commit it.")
    if worse:
        print("  Fix what got worse. Raising the baseline loosens the rule: a human approves that")
        print("  (`--update --accept-worse`).")
    return 1 if (worse and args.enforce) else 0


if __name__ == "__main__":
    raise SystemExit(main())
