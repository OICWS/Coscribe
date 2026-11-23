"""List what a pull request loosens: limits that only the maintainer may raise (decision 0009).

    python scripts/loosened.py --base <sha> --head <sha>

Compares the two commits and prints one line per loosening: a number in
`quality/baseline.json` that got worse or a name that is new there, a budget in
`quality/budgets.json` that grew, a component no longer counted as core, an `ignore_imports`
entry added in `components.toml` or `pyproject.toml`, the coverage floor lowered, or a new
ruff, mypy or exclusion setting that turns a check off for some code. Exit 1 when there is one
and the pull request does not carry both a `Loosened: <why>` line in its description
(`PR_BODY`) and the `loosening-approved` label (`PR_LABELS`, comma-separated), which only the
maintainer adds. Sessions share the maintainer's GitHub account, so the label marks a decision
the maintainer made, not an identity GitHub checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
LABEL = "loosening-approved"
REASON = re.compile(r"^\s*Loosened:\s*\S", re.MULTILINE | re.IGNORECASE)


def _show(sha: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{sha}:{path}"], cwd=REPO, capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def _json(text: str | None) -> dict[str, Any]:
    return json.loads(text) if text else {}


def _toml(text: str | None) -> dict[str, Any]:
    return tomllib.loads(text) if text else {}


def _get(data: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def baseline(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    found = []
    for metric, now in sorted(after.items()):
        # A metric the base did not have limits something that was unlimited: a new ratchet.
        if metric not in before:
            continue
        was = before[metric]
        for name, value in sorted(now.items()):
            if name not in was:
                found.append(f"quality/baseline.json: {metric}: new {name} = {value}")
            elif value > was[name]:
                found.append(f"quality/baseline.json: {metric}: {name} {was[name]} -> {value}")
    return found


def budgets(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    found = []
    for name, value in sorted(after.items()):
        if name in before and value > before[name]:
            found.append(f"quality/budgets.json: {name} {before[name]} -> {value}")
    for name in sorted(set(before) - set(after)):
        found.append(f"quality/budgets.json: {name} removed")
    return found


def _added(label: str, before: Iterable[str], after: Iterable[str]) -> list[str]:
    return [f"{label}: added {item}" for item in sorted(set(after) - set(before))]


def components(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    def ignores(data: dict[str, Any]) -> set[str]:
        return {
            f"{c['name']}: {entry}"
            for c in data.get("component", [])
            for entry in c.get("ignore_imports", [])
        }

    def core(data: dict[str, Any]) -> set[str]:
        return {c["name"] for c in data.get("component", []) if c.get("core")}

    found = _added("components.toml ignore_imports", ignores(before), ignores(after))
    found += [
        f"components.toml: {name} is no longer core" for name in sorted(core(before) - core(after))
    ]
    return found


def pyproject(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    found = []
    floor_before = _get(before, "tool", "coverage", "report", "fail_under")
    floor_after = _get(after, "tool", "coverage", "report", "fail_under")
    if floor_before is not None and (floor_after is None or floor_after < floor_before):
        found.append(f"pyproject.toml: coverage fail_under {floor_before} -> {floor_after}")

    def contracts(data: dict[str, Any]) -> set[str]:
        return {
            f"{c.get('name', '?')}: {entry}"
            for c in _get(data, "tool", "importlinter", "contracts") or []
            for entry in c.get("ignore_imports", [])
        }

    found += _added(
        "pyproject.toml importlinter ignore_imports", contracts(before), contracts(after)
    )

    def per_file(data: dict[str, Any]) -> set[str]:
        table = _get(data, "tool", "ruff", "lint", "per-file-ignores") or {}
        return {f"{path} {rule}" for path, rules in table.items() for rule in rules}

    found += _added("pyproject.toml ruff per-file-ignores", per_file(before), per_file(after))
    for keys in (
        ("tool", "ruff", "lint", "ignore"),
        ("tool", "ruff", "extend-exclude"),
        ("tool", "ruff", "exclude"),
        ("tool", "mypy", "exclude"),
        ("tool", "coverage", "run", "omit"),
    ):
        found += _added(
            "pyproject.toml " + ".".join(keys[1:]),
            _get(before, *keys) or [],
            _get(after, *keys) or [],
        )
    if _get(before, "tool", "mypy", "strict") and not _get(after, "tool", "mypy", "strict"):
        found.append("pyproject.toml: mypy strict turned off")

    def mypy_off(data: dict[str, Any]) -> set[str]:
        out = set()
        for override in _get(data, "tool", "mypy", "overrides") or []:
            modules = override.get("module", [])
            for module in [modules] if isinstance(modules, str) else modules:
                for key, value in override.items():
                    if key != "module" and value in (True, False):
                        out.add(f"{module} {key}={value}")
        return out

    found += _added("pyproject.toml mypy overrides", mypy_off(before), mypy_off(after))
    return found


def loosenings(base: str, head: str) -> list[str]:
    def pair(path: str) -> tuple[str | None, str | None]:
        return _show(base, path), _show(head, path)

    b, h = pair("office-agent/quality/baseline.json")
    found = baseline(_json(b), _json(h))
    b, h = pair("office-agent/quality/budgets.json")
    found += budgets(_json(b), _json(h))
    b, h = pair("components.toml")
    found += components(_toml(b), _toml(h))
    b, h = pair("office-agent/pyproject.toml")
    found += pyproject(_toml(b), _toml(h))
    return found


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    found = loosenings(args.base, args.head)
    if not found:
        print("Nothing loosened.")
        return 0
    for line in found:
        print(f"LOOSENED  {line}")
    labels = {s.strip() for s in os.environ.get("PR_LABELS", "").split(",")}
    has_reason = bool(REASON.search(os.environ.get("PR_BODY", "")))
    if has_reason and LABEL in labels:
        print(f"Accepted: the description says why, and the pull request has `{LABEL}`.")
        return 0
    if not has_reason:
        print("::error::Say why in the description, on a line starting `Loosened:`.")
    if LABEL not in labels:
        print(
            f"::error::Only the maintainer may loosen these (decision 0009): the `{LABEL}` label "
            "is theirs to add. A session never adds it."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
