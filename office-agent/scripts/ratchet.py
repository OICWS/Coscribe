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
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

import grimp
import vulture

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coscribe"
TESTS = ROOT / "tests"
BASELINE = ROOT / "quality" / "baseline.json"
# Limits on size rather than numbers that may only shrink (decision 0009: the core about 100k
# lines; a component small enough that its card and interface fit a session's slice).
BUDGETS = ROOT / "quality" / "budgets.json"
COMPONENTS = ROOT.parent / "components.toml"

# Files above this are listed; one function above it is listed too.
FILE_LINES_LISTED = 800
FUNCTION_LINES_LISTED = 100
COMPLEXITY_LISTED = 15
# Direct imports of other coscribe modules per module (assessment 2.5).
FAN_OUT_LISTED = 25
# vulture's own scale: 60 is "never referenced by name", 100 is "provably unused". Below 60 it
# would also list every import.
DEAD_CODE_CONFIDENCE = 60

# A package whose `__all__` lists more names than this is listed: its card and `slice.py` open
# every slice with that list (issue #677).
INTERFACE_LISTED = 50

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


_TS_IMPORT = re.compile(
    r"""(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]"""
    r"""|import\s*\(\s*['"]([^'"]+)['"]\s*\)"""
    r"""|^\s*import\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def _frontend_part(path: Path, src: Path) -> str:
    """The feature a file belongs to (`components/<feature>/`), or the folder it sits in."""
    parts = path.relative_to(src).parts
    if parts[0] == "components" and len(parts) > 2:
        return f"components/{parts[1]}"
    if parts[0] == "components":
        return "components"
    return parts[0] if len(parts) > 1 else "src"


def _resolve_ts(source: Path, spec: str) -> Path | None:
    if not spec.startswith("."):
        return None
    base = (source.parent / spec).resolve()
    for candidate in (
        base,
        base.with_name(base.name + ".ts"),
        base.with_name(base.name + ".tsx"),
        base / "index.ts",
        base / "index.tsx",
    ):
        if candidate.is_file():
            return candidate
    return None


def frontend_feature_imports(src: Path | None = None) -> dict[str, int]:
    """Imports from outside a frontend feature (`components/<feature>/`) into one of its files
    other than its `index.ts`, per pair: a feature entered through its index can change inside
    without its users changing, like a Python package through `__all__`."""
    src = (src or ROOT / "frontend" / "src").resolve()
    found: dict[str, int] = {}
    for path in sorted(src.rglob("*.ts*")):
        if ".test." in path.name or path.suffix not in (".ts", ".tsx"):
            continue
        source = _frontend_part(path, src)
        for match in _TS_IMPORT.finditer(path.read_text(encoding="utf-8")):
            target = _resolve_ts(path, next(g for g in match.groups() if g))
            if target is None or src not in target.parents:
                continue
            feature = _frontend_part(target, src)
            if feature == source or not feature.startswith("components/"):
                continue
            if target.stem == "index":
                continue
            key = f"{source} -> {feature}"
            found[key] = found.get(key, 0) + 1
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


@functools.cache
def _nested_components() -> frozenset[str]:
    """The components inside another package (`runtime.models`), as `coscribe.<name>`: the
    package is their entry point, so importing it is not a reach into a submodule."""
    data = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "components.toml").read_text("utf-8")
    )
    return frozenset(f"coscribe.{c['name']}" for c in data.get("component", []) if "." in c["name"])


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
                if module.count(".") >= 2 and module not in _nested_components():
                    key = f"{importer} -> {module}"
                    found[key] = found.get(key, 0) + 1
                for name in names:
                    if name.startswith("_") and not name.startswith("__"):
                        key = f"{importer} -> {module}:{name}"
                        found[key] = found.get(key, 0) + 1
    return found


def interface_size(src: Path = SRC, listed: int = INTERFACE_LISTED) -> dict[str, int]:
    """Names in a package's `__all__`, for the packages over the limit."""
    found: dict[str, int] = {}
    for path in _python_files(src, skip_vendored=True):
        tree = None if path.name != "__init__.py" else _parse(path)
        if tree is None:
            continue
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
                and isinstance(node.value, (ast.List, ast.Tuple))
                and len(node.value.elts) > listed
            ):
                found[_module_name(path, src)] = len(node.value.elts)
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


# Libraries only an Office tool needs. Importing one at the top of a module the server loads on
# startup costs every launch its time and memory (docs/metrics/2026-10-20-startup-cost.md).
STARTUP_HEAVY = (
    "pptx",
    "docx",
    "openpyxl",
    "xlsxwriter",
    "lxml",
    "PIL",
    "pypdfium2",
    "pdfplumber",
    "reportlab",
    "mammoth",
    "markdownify",
    "bs4",
    "ironcalc",
    "resvg_py",
)
STARTUP_MODULE = "coscribe.web.app"


def startup_imports(
    module: str = STARTUP_MODULE,
    heavy: tuple[str, ...] = STARTUP_HEAVY,
    path: Path = SRC.parent,
) -> dict[str, int]:
    """The heavy libraries that importing `module` loads, measured in a fresh interpreter. A new
    name is worse: someone put an Office library back on the startup path. Moving an import into
    the function that needs it makes the number better."""
    code = (
        "import json, sys\n"
        f"import {module}\n"
        f"print(json.dumps([n for n in {list(heavy)!r} if n in sys.modules]))"
    )
    environment = {**os.environ, "PYTHONPATH": str(path)}
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, env=environment
    )
    return {name: 1 for name in json.loads(done.stdout.splitlines()[-1])}


METRICS = {
    "file_lines": file_lines,
    "long_functions": long_functions,
    "complex_functions": complex_functions,
    "frontend_file_lines": frontend_file_lines,
    "frontend_long_functions": frontend_long_functions,
    "frontend_unused_exports": frontend_unused_exports,
    "frontend_feature_imports": frontend_feature_imports,
    "suppressions": suppressions,
    "deep_imports": deep_imports,
    "interface_size": interface_size,
    "tests_without_a_check": tests_without_a_check,
    "patch_by_string": patch_by_string,
    "fan_out": fan_out,
    "dead_code": dead_code,
    "startup_imports": startup_imports,
}


FRONTEND_SHELL = "frontend"  # the frontend outside its feature folders: the app's frame


def _frontend_files(root: Path) -> list[Path]:
    return [
        f
        for pattern in ("*.ts", "*.tsx")
        for f in root.rglob(pattern)
        if ".test." not in f.name and "node_modules" not in f.parts
    ]


def component_lines(components_toml: Path = COMPONENTS) -> dict[str, int]:
    """Own source lines per component, without the components nested in it and without vendored
    code: Python under `src/coscribe`, TypeScript under `frontend/src` (tests left out)."""
    components = tomllib.loads(components_toml.read_text("utf-8")).get("component", [])
    repo = components_toml.parent
    roots = {c["name"]: repo / c["path"] for c in components if "/src/coscribe" in c["path"]}
    front = {
        c["name"]: repo / c["path"] / ("src" if c["name"] == FRONTEND_SHELL else "")
        for c in components
        if c["name"] == FRONTEND_SHELL or c["name"].startswith(FRONTEND_SHELL + ".")
    }
    sizes: dict[str, int] = {}
    for group, listing in (
        (roots, lambda root: _python_files(root, skip_vendored=False)),
        (front, _frontend_files),
    ):
        for name, root in group.items():
            nested = [r for n, r in group.items() if n != name and root in r.parents]
            files = [root] if root.suffix == ".py" else list(listing(root))
            sizes[name] = sum(
                len(f.read_text(encoding="utf-8").splitlines())
                for f in files
                if not any(r == f or r in f.parents for r in nested)
                and not any(v in f.as_posix() for v in VENDORED)
            )
    return sizes


def budget_problems(
    budgets: dict[str, int], sizes: dict[str, int], core: frozenset[str]
) -> list[str]:
    problems = []
    total = sum(size for name, size in sizes.items() if name in core)
    if total > budgets["core_lines"]:
        problems.append(f"core_lines: {total} over the budget of {budgets['core_lines']}")
    # The frame holds what no feature owns. Its budget sits just above its size when features
    # became components, so a new screen goes into a feature folder rather than the frame.
    shell = sizes.get(FRONTEND_SHELL, 0)
    if "frontend_shell_lines" in budgets and shell > budgets["frontend_shell_lines"]:
        problems.append(
            f"frontend_shell_lines: {shell} over the budget of {budgets['frontend_shell_lines']}"
        )
    for name, size in sorted(sizes.items()):
        if name != FRONTEND_SHELL and size > budgets["component_lines"]:
            problems.append(
                f"component_lines: {name} has {size}, over the budget of "
                f"{budgets['component_lines']}"
            )
    return problems


def core_components(components_toml: Path = COMPONENTS) -> frozenset[str]:
    data = tomllib.loads(components_toml.read_text("utf-8"))
    return frozenset(c["name"] for c in data.get("component", []) if c.get("core"))


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
    sizes = component_lines()
    core = core_components()
    budgets = json.loads(BUDGETS.read_text(encoding="utf-8"))
    parts = {k: v for k, v in sizes.items() if k != FRONTEND_SHELL}
    print(
        f"Budgets: core {sum(v for k, v in sizes.items() if k in core)} of "
        f"{budgets['core_lines']} lines; largest component {max(parts.values())} of "
        f"{budgets['component_lines']}; frontend frame {sizes.get(FRONTEND_SHELL, 0)} of "
        f"{budgets.get('frontend_shell_lines', 'no budget')}"
    )
    over = budget_problems(budgets, sizes, core)
    for line in over:
        print(f"  OVER   {line}")
    if over:
        print("  Split the component or move code out of the core. Raising a budget is the")
        print("  maintainer's decision (decision 0009).")
    for line in worse:
        print(f"  WORSE  {line}")
    for line in better:
        print(f"  better {line}")
    if better:
        print("  Some numbers improved: run `python scripts/ratchet.py --update` and commit it.")
    if worse:
        print("  Fix what got worse. Raising the baseline loosens the rule: a human approves that")
        print("  (`--update --accept-worse`).")
    return 1 if ((worse or over) and args.enforce) else 0


if __name__ == "__main__":
    raise SystemExit(main())
