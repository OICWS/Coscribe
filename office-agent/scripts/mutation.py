#!/usr/bin/env python3
"""Mutation testing of the modules where a silent mistake is a security or data problem.

    python scripts/mutation.py list                       the module keys, one per line
    python scripts/mutation.py run KEY --out DIR          mutate one module, write DIR/KEY.json
                                                          and DIR/KEY-survivors.txt
    python scripts/mutation.py summary DIR                a markdown table of every DIR/*.json

mutmut changes the code (a `<` to `<=`, a deleted line) and runs the tests; a change no
test notices is a survivor. It reads one `[tool.mutmut]` section from the pyproject.toml
in the current directory, so each run happens in a scratch copy of `src/` and `tests/`
whose pyproject.toml gets a section naming that one module and the tests that own it.
Running the whole suite is wrong here: mutmut wraps every function in a trampoline, and
`tests/test_tool_deferral.py` reads tool schemas from function signatures.

mutmut forks, so this runs on Linux only (the product is not affected). It is a report:
a survivor is a gap to turn into an issue, not a failure, and the exit code is 0 unless
mutmut itself broke.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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
    "workflow_spec": ("workflows/spec.py", ["tests/test_workflow_spec.py"]),
    "xlsx_calc": ("tools/office/xlsx/calc.py", ["tests/test_xlsx_calc.py"]),
}


def _toml_list(items: list[str]) -> str:
    return "[" + ", ".join(json.dumps(item) for item in items) + "]"


def _prepare(work: Path, key: str) -> None:
    module, pytest_args = MODULES[key]
    shutil.copytree(
        ROOT / "src",
        work / "src",
        ignore=shutil.ignore_patterns("__pycache__", "node_modules"),
    )
    shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    # Tests that build the app need web/static/, a build output this job does not make.
    static = work / PACKAGE / "web" / "static"
    if not static.exists():
        static.mkdir(parents=True)
        (static / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # `also_copy = ["src"]` puts the whole package next to the mutated file; without it the
    # package would hold only that file and every other import would fail.
    config += (
        "\n[tool.mutmut]\n"
        f"source_paths = {_toml_list([f'{PACKAGE}/{module}'])}\n"
        'also_copy = ["src"]\n'
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
        stats = json.loads((work / "mutants" / "mutmut-cicd-stats.json").read_text(encoding="utf-8"))
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
            for field in ("killed", "survived", "timeout", "no_tests", "suspicious", "skipped", "segfault")
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
    missing = sorted(set(MODULES) - {p.stem for p in rows})
    if missing:
        lines += ["", "No result for: " + ", ".join(f"`{key}`" for key in missing)]
    lines += ["", "The survivor lists (each with its diff) are in the `mutation-survivors` artifact."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("key", choices=sorted(MODULES))
    run_parser.add_argument("--out", type=Path, required=True)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "list":
        print("\n".join(MODULES))
        return 0
    if args.command == "run":
        return run(args.key, args.out)
    sys.stdout.write(summary(args.directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
