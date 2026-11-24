#!/usr/bin/env python3
"""Mutation testing of the modules where a silent mistake is a security or data problem.

    python scripts/mutation.py list                       the module keys, one per line
    python scripts/mutation.py run KEY --out DIR          mutate one module, write DIR/KEY.json
                                                          and DIR/KEY-survivors.txt
    python scripts/mutation.py summary DIR                a markdown table of every DIR/*.json
    python scripts/mutation.py changed --base SHA --out DIR
                                                          mutate only the functions a pull request
                                                          changed, with the tests that reach them

mutmut changes the code (a `<` to `<=`, a deleted line) and runs the tests; a change no
test notices is a survivor. It reads one `[tool.mutmut]` section from the pyproject.toml
in the current directory, so each run happens in a scratch copy of `src/` and `tests/`
whose pyproject.toml gets a section naming that one module and the tests that own it.
Running the whole suite is wrong here: mutmut wraps every function in a trampoline, and
`tests/test_tool_deferral.py` reads tool schemas from function signatures.

`changed` is the pull request's run (`.github/workflows/mutation-changes.yml`): for each
module under `src/coscribe` whose functions the pull request changed (at most `CHANGED_MODULES`),
it picks the tests with `ci_scope`'s import graph and runs only the mutants of the changed
functions, so the report is about the lines the pull request wrote.

mutmut forks, so this runs on Linux only (the product is not affected). It is a report:
a survivor is a gap to turn into an issue, not a failure, and the exit code is 0 unless
mutmut itself broke.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "src/coscribe"

# key -> (module under src/coscribe, the pytest arguments that select its own tests)
MODULES: dict[str, tuple[str, list[str]]] = {
    "secret_store": (
        "runtime/secret_store.py",
        ["tests/test_secret_store.py", "tests/test_secret_redaction_properties.py"],
    ),
    "secrets": (
        "runtime/secrets.py",
        ["tests/test_secrets.py", "tests/test_secret_redaction_properties.py"],
    ),
    "exec_policy": ("runtime_lg/exec_policy.py", ["tests/test_exec_policy.py"]),
    "code_permissions": (
        "code_runtime/permissions.py",
        [
            "tests/web/test_settings.py",
            "tests/test_code_agent.py",
            "tests/test_code_permissions.py",
            "-k",
            "code_permissions or always_allowing",
        ],
    ),
    "script_guard": ("tools/exec/script_guard.py", ["tests/test_script_guard.py"]),
    "workflow_spec": ("workflow_spec/spec.py", ["tests/test_workflow_spec.py"]),
    "xlsx_calc": ("tools/office/xlsx/calc.py", ["tests/test_xlsx_calc.py"]),
}


CHANGED_MODULES = 5  # a pull request's run stays inside one job's time limit
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.M)


def changed_lines(diff: str) -> set[int]:
    """The new-side line numbers a unified diff with `-U0` adds or changes.

    A hunk that only deletes has no new-side line; the lines on either side of
    the gap stand for it, so a function that only lost statements is still mutated."""
    lines: set[int] = set()
    for match in _HUNK.finditer(diff):
        start, count = int(match.group(1)), int(match.group(2) or 1)
        if count == 0:
            lines.update({start, start + 1} - {0})
        else:
            lines.update(range(start, start + count))
    return lines


def mutant_prefixes(source: str, lines: set[int]) -> list[str]:
    """mutmut's name prefix for each top-level function and method that a changed line is in.

    mutmut 3 names a function's mutants `x_<name>__mutmut_<n>` and a method's
    `xǁ<Class>ǁ<name>__mutmut_<n>`; a nested function is mutated as part of its parent."""
    prefixes = []

    def touched(node: ast.AST) -> bool:
        end = getattr(node, "end_lineno", None) or node.lineno  # type: ignore[attr-defined]
        return any(node.lineno <= line <= end for line in lines)  # type: ignore[attr-defined]

    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and touched(node):
            prefixes.append(f"x_{node.name}__mutmut_")
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and touched(item):
                    prefixes.append(f"x\u01c1{node.name}\u01c1{item.name}__mutmut_")
    return prefixes


def _toml_list(items: list[str]) -> str:
    return "[" + ", ".join(json.dumps(item) for item in items) + "]"


def _prepare(work: Path, key: str) -> None:
    _prepare_module(work, *MODULES[key])


def _prepare_module(work: Path, module: str, pytest_args: list[str]) -> None:
    shutil.copytree(
        ROOT / "src",
        work / "src",
        ignore=shutil.ignore_patterns("__pycache__", "node_modules"),
    )
    shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    # Some tests import the evaluations or a script, directly or through a helper.
    for folder in ("evals", "scripts"):
        if (ROOT / folder).is_dir():
            shutil.copytree(
                ROOT / folder, work / folder, ignore=shutil.ignore_patterns("__pycache__")
            )
    # Tests that build the app need web/static/, a build output this job does not make.
    static = work / PACKAGE / "web" / "static"
    if not static.exists():
        static.mkdir(parents=True)
        (static / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
    copied = ["src", *(folder for folder in ("evals", "scripts") if (work / folder).is_dir())]
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # `also_copy = ["src"]` puts the whole package next to the mutated file; without it the
    # package would hold only that file and every other import would fail.
    config += (
        "\n[tool.mutmut]\n"
        f"source_paths = {_toml_list([f'{PACKAGE}/{module}'])}\n"
        f"also_copy = {_toml_list(copied)}\n"
        f"pytest_add_cli_args_test_selection = {_toml_list(pytest_args)}\n"
    )
    (work / "pyproject.toml").write_text(config, encoding="utf-8")
    readme = ROOT / "README.md"
    if readme.exists():
        shutil.copy(readme, work / "README.md")


def _mutmut(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mutmut", *args],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
    )


def run(key: str, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"mutation-{key}-") as tmp:
        work = Path(tmp)
        _prepare(work, key)
        result = _mutmut(work, "run")
        sys.stdout.write(result.stdout[-4000:])
        sys.stderr.write(result.stderr[-4000:])
        if _mutmut(work, "export-cicd-stats").returncode != 0:
            print(f"mutmut produced no results for {key}", file=sys.stderr)
            return 1
        stats = json.loads(
            (work / "mutants" / "mutmut-cicd-stats.json").read_text(encoding="utf-8")
        )
        listing = _mutmut(work, "results", "--all", "true").stdout
        survivors = [
            line.strip().rsplit(":", 1)[0]
            for line in listing.splitlines()
            if line.strip().endswith((": survived", ": no tests"))
        ]
        # mutmut exits 0 even when the tests fail before any mutation ("failed to collect
        # stats", a failing clean run), so the output and the counts decide.
        decided = sum(
            stats[field]
            for field in (
                "killed",
                "survived",
                "timeout",
                "no_tests",
                "suspicious",
                "skipped",
                "segfault",
            )
        )
        broken = "failed to" in (result.stdout + result.stderr) or decided != stats["total"]
        counts = {
            "module": f"{PACKAGE}/{MODULES[key][0]}",
            "mutants": stats["total"],
            "killed": stats["killed"],
            "survived": stats["survived"],
            "timeout": stats["timeout"],
            "no_tests": stats["no_tests"],
            "other": stats["suspicious"] + stats["segfault"] + stats["skipped"],
        }
        # The counts go out before the per-survivor diffs, which take a process each.
        if not broken and counts["mutants"]:
            (out / f"{key}.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
        blocks: list[str] = []
        for name in survivors:
            shown = _mutmut(work, "show", name).stdout.strip()
            blocks.append(shown or f"# {name}")
    (out / f"{key}-survivors.txt").write_text(
        "\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8"
    )
    print(json.dumps(counts))
    # A run that tested nothing or stopped early means the setup broke, not that the tests
    # are perfect; no JSON is written, so the summary lists the module as missing.
    return 1 if broken or not counts["mutants"] else 0


def _own_tests(graph: Any, ci_scope: Any, path: str) -> list[str]:
    """The tests that import the module itself, or else every test that reaches it.

    mutmut first runs all the tests it is given once, so the module's own tests keep a run
    inside the job's time; the tests that read the whole tree (`ALWAYS`) can't run in the
    scratch copy."""
    module = ci_scope.module_of(path)
    own = sorted(
        test.replace(".", "/") + ".py"
        for test, imported in graph.imports.items()
        if test.startswith("tests.") and module in imported
    )
    always = {*ci_scope.ALWAYS, *ci_scope.DOCS_TESTS}
    return [test for test in own or graph.select([path]) or [] if test not in always]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def changed(base: str, out: Path) -> int:
    """Mutate the functions this checkout changed since `base`; a report, like `run`."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ci_scope

    out.mkdir(parents=True, exist_ok=True)
    paths = _git("diff", "--name-only", "--diff-filter=AM", base, "--", PACKAGE).split()
    graph = ci_scope.Graph.build(ROOT)
    picked = []
    for path in sorted(p for p in paths if p.endswith(".py")):
        rel = path.removeprefix("office-agent/")
        lines = changed_lines(_git("diff", "-U0", base, "--", rel))
        prefixes = mutant_prefixes((ROOT / rel).read_text(encoding="utf-8"), lines)
        tests = _own_tests(graph, ci_scope, path)
        if prefixes and tests:
            picked.append((rel.removeprefix(PACKAGE + "/"), prefixes, tests))
    notes = [f"Changed modules with changed functions: {len(picked)}"]
    if len(picked) > CHANGED_MODULES:
        notes.append(f"Only the first {CHANGED_MODULES} were mutated.")
    status = 0
    for module, prefixes, tests in picked[:CHANGED_MODULES]:
        key = module.removesuffix(".py").replace("/", ".")
        dotted = "coscribe." + key
        with tempfile.TemporaryDirectory(prefix="mutation-changed-") as tmp:
            work = Path(tmp)
            _prepare_module(work, module, tests)
            result = _mutmut(work, "run", *(f"{dotted}.{prefix}*" for prefix in prefixes))
            sys.stdout.write(result.stdout[-2000:])
            if "failed to" in result.stdout + result.stderr:
                status = 1
                notes.append(f"`{PACKAGE}/{module}`: the tests failed before any mutation")
                sys.stderr.write(result.stderr[-2000:])
                continue
            listing = _mutmut(work, "results", "--all", "true").stdout
            states = [
                line.strip().rsplit(": ", 1)
                for line in listing.splitlines()
                if any(f"{dotted}.{prefix}" in line for prefix in prefixes)
                and ": " in line
                and not line.strip().endswith(": not checked")
            ]
            if not states:
                status = 1
                notes.append(f"`{PACKAGE}/{module}`: mutmut produced no result")
                continue
            survivors = [name for name, state in states if state in ("survived", "no tests")]
            count = {state: sum(1 for _, s in states if s == state) for _, state in states}
            counts = {
                "module": f"{PACKAGE}/{module}",
                "mutants": len(states),
                "killed": count.get("killed", 0),
                "survived": count.get("survived", 0),
                "timeout": count.get("timeout", 0),
                "no_tests": count.get("no tests", 0),
            }
            (out / f"{key}.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
            blocks = [
                _mutmut(work, "show", name).stdout.strip() or f"# {name}" for name in survivors
            ]
        (out / f"{key}-survivors.txt").write_text(
            "\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8"
        )
    (out / "notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return status


def summary(directory: Path) -> str:
    rows = sorted(directory.glob("**/*.json"))
    lines = [
        "## Mutation testing",
        "",
        "| Module | Mutants | Killed | Survived | Timed out | No test reaches it |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    totals = dict.fromkeys(("mutants", "killed", "survived", "timeout", "no_tests"), 0)
    for path in rows:
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in totals:
            totals[field] += data[field]
        lines.append(
            f"| `{data['module']}` | {data['mutants']} | {data['killed']} | {data['survived']} "
            f"| {data['timeout']} | {data['no_tests']} |"
        )
    lines.append(
        f"| **Total** | {totals['mutants']} | {totals['killed']} | {totals['survived']} "
        f"| {totals['timeout']} | {totals['no_tests']} |"
    )
    notes = directory / "notes.txt"
    if notes.is_file():  # a pull request's `changed` run, which has no fixed module list
        lines += ["", *notes.read_text(encoding="utf-8").splitlines()]
        return "\n".join(lines) + "\n"
    missing = sorted(set(MODULES) - {p.stem for p in rows})
    if missing:
        lines += ["", "No result for: " + ", ".join(f"`{key}`" for key in missing)]
    lines += [
        "",
        "The survivor lists (each with its diff) are in the `mutation-survivors` artifact.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("key", choices=sorted(MODULES))
    run_parser.add_argument("--out", type=Path, required=True)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("directory", type=Path)
    changed_parser = sub.add_parser("changed")
    changed_parser.add_argument("--base", required=True)
    changed_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "list":
        print("\n".join(MODULES))
        return 0
    if args.command == "run":
        return run(args.key, args.out)
    if args.command == "changed":
        return changed(args.base, args.out)
    sys.stdout.write(summary(args.directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
