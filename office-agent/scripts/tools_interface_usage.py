#!/usr/bin/env python3
"""Which names of `coscribe.tools.__all__` are used from outside `tools`, and by whom.

    python scripts/tools_interface_usage.py            print the table as Markdown
    python scripts/tools_interface_usage.py --json     the same numbers as JSON

A use is `from coscribe.tools import X` (or the relative form), or `tools.X` after
`from coscribe import tools`, in a module outside `coscribe.tools`. Uses in `tests/` are
counted apart: a name only a test imports still costs every session that reads the card.
Each name also gets the sub-component it is re-exported from, because a name that already
lives in a sub-component is the cheap one to move.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coscribe"
TESTS = ROOT / "tests"
TOOLS = SRC / "tools"
PACKAGE = "coscribe.tools"


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _component(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else parts[0]


def interface() -> list[str]:
    tree = ast.parse((TOOLS / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            return [e.value for e in node.value.elts]  # type: ignore[attr-defined]
    raise SystemExit("tools/__init__.py has no __all__")


def sources() -> dict[str, str]:
    """Name -> the module of `tools` it is imported from in `tools/__init__.py`."""
    tree = ast.parse((TOOLS / "__init__.py").read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                found[alias.asname or alias.name] = node.module
    return found


def _resolve(module: str | None, level: int, importer: str, is_package: bool) -> str:
    if not level:
        return module or ""
    base = importer.split(".")
    if not is_package:
        base = base[:-1]
    base = base[: len(base) - (level - 1)]
    return ".".join([*base, module] if module else base)


def _uses(path: Path, importer: str, names: set[str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    is_package = path.name == "__init__.py"
    used: set[str] = set()
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve(node.module, node.level, importer, is_package)
            if module == PACKAGE:
                used.update(a.name for a in node.names if a.name in names)
            elif module == "coscribe":
                aliases.update(a.asname or a.name for a in node.names if a.name == "tools")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == PACKAGE and a.asname:
                    aliases.add(a.asname)
    if aliases:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in aliases
                and node.attr in names
            ):
                used.add(node.attr)
    return used


def measure() -> dict[str, object]:
    names = interface()
    wanted = set(names)
    src_users: dict[str, set[str]] = defaultdict(set)
    test_users: dict[str, set[str]] = defaultdict(set)
    for path in sorted(SRC.rglob("*.py")):
        importer = _module_name(path)
        if importer == PACKAGE or importer.startswith(PACKAGE + "."):
            continue
        for name in _uses(path, importer, wanted):
            src_users[name].add(_component(importer))
    for path in sorted(TESTS.rglob("*.py")):
        for name in _uses(path, "tests." + path.stem, wanted):
            test_users[name].add(path.name)
    origin = sources()
    rows = []
    for name in names:
        module = origin.get(name, "?")
        rows.append(
            {
                "name": name,
                "from": module,
                "src": sorted(src_users.get(name, ())),
                "tests": len(test_users.get(name, ())),
            }
        )
    return {"total": len(names), "rows": rows}


def _group(row: dict[str, object]) -> str:
    module = str(row["from"])
    if module == "?":
        return module
    parts = module.split(".")
    return ".".join(parts[:2]) if parts[0] == "office" and len(parts) > 1 else parts[0]


def markdown(result: dict[str, object]) -> str:
    rows: list[dict[str, object]] = result["rows"]  # type: ignore[assignment]
    unused = [r for r in rows if not r["src"] and not r["tests"]]
    tests_only = [r for r in rows if not r["src"] and r["tests"]]
    by_origin: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_origin[_group(row)].append(row)
    out = [f"`coscribe.tools.__all__` has {result['total']} names.", ""]
    out += [
        "| Re-exported from | Names | Used by `src` outside `tools` | Only tests | Unused |",
        "|---|---|---|---|---|",
    ]
    for origin in sorted(by_origin, key=lambda k: -len(by_origin[k])):
        group = by_origin[origin]
        out.append(
            f"| `{origin}` | {len(group)} | {sum(1 for r in group if r['src'])} "
            f"| {sum(1 for r in group if not r['src'] and r['tests'])} "
            f"| {sum(1 for r in group if not r['src'] and not r['tests'])} |"
        )
    out += ["", "## Names by the components that use them", ""]
    users: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        src: list[str] = row["src"]  # type: ignore[assignment]
        if src:
            users[", ".join(src)].append(str(row["name"]))
    out += ["| Used by | Count |", "|---|---|"]
    for key in sorted(users, key=lambda k: -len(users[k])):
        out.append(f"| {key} | {len(users[key])} |")
    out += [
        "",
        f"## Used by no module of `src` outside `tools`: {len(unused) + len(tests_only)}",
        "",
    ]
    out.append(f"Unused anywhere ({len(unused)}): " + ", ".join(f"`{r['name']}`" for r in unused))
    out.append("")
    out.append(
        f"Used only by tests ({len(tests_only)}): "
        + ", ".join(f"`{r['name']}`" for r in tests_only)
    )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = measure()
    print(json.dumps(result, indent=1) if args.json else markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
