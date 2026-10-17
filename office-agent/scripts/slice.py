"""Print the slice a session needs to change one file: its component, the card, the interface,
the tests and the dependents. `docs/components.md` is the map; this is the map applied to a path.

    python scripts/slice.py src/coscribe/tools/office/docx/tools.py
    python scripts/slice.py office-agent/frontend/src/App.tsx
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
SRC = "office-agent/src/"
CHARS_PER_TOKEN = 4
BUDGET_FILES = 15
BUDGET_TOKENS = 150_000


def components() -> list[dict[str, object]]:
    with (ROOT / "components.toml").open("rb") as handle:
        return list(tomllib.load(handle)["component"])


def repo_path(argument: str) -> str:
    """The path relative to the repository root, whichever directory it was typed from."""
    path = Path(argument)
    if not path.is_absolute():
        for base in (Path.cwd(), ROOT, ROOT / "office-agent"):
            if (base / path).exists():
                path = (base / path).resolve()
                break
    return path.resolve().relative_to(ROOT).as_posix()


def owning_component(path: str, items: list[dict[str, object]]) -> dict[str, object] | None:
    """The component with the longest path that contains `path`."""
    best = None
    for item in items:
        base = str(item["path"])
        if (path == base or path.startswith(base.rstrip("/") + "/")) and (
            best is None or len(base) > len(str(best["path"]))
        ):
            best = item
    return best


def module_name(path: str) -> str | None:
    if not path.startswith(SRC) or not path.endswith(".py"):
        return None
    parts = path.removeprefix(SRC).removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def public_names(component: dict[str, object]) -> list[str]:
    """`__all__` of a package, read from the source so nothing is imported."""
    path = ROOT / str(component["path"])
    init = path if path.suffix == ".py" else path / "__init__.py"
    if not init.is_file():
        return []
    for node in ast.parse(init.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            return [str(ast.literal_eval(e)) for e in getattr(node.value, "elts", [])]
    return []


def card_tests(card: Path) -> list[str]:
    """The test paths the card's `## Tests` section names."""
    text = card.read_text(encoding="utf-8")
    match = re.search(r"^## Tests\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    found = re.findall(r"`((?:office-agent/)?tests/[\w/.*-]+)`", match.group(1) if match else "")
    return [name.removeprefix("office-agent/") for name in found]


def tests_importing(module: str) -> list[str]:
    """Test files that name the module (by text, not by running them)."""
    pattern = re.compile(rf"\b{re.escape(module)}\b")
    return [
        test.relative_to(ROOT).as_posix()
        for test in sorted((ROOT / "office-agent" / "tests").rglob("test_*.py"))
        if pattern.search(test.read_text(encoding="utf-8", errors="replace"))
    ]


def sibling_tests(path: str) -> list[str]:
    """A frontend file's unit tests sit next to it: `x.ts` has `x.test.ts`."""
    base = ROOT / path
    return [
        sibling.relative_to(ROOT).as_posix()
        for sibling in sorted(base.parent.glob(f"{base.stem}.test.*"))
    ]


def dependents(module: str) -> dict[str, list[str]]:
    import grimp

    graph = grimp.build_graph("coscribe", include_external_packages=False)
    if module.startswith("coscribe.") and module not in graph.modules:
        return {}
    found: dict[str, list[str]] = {}
    for importer in sorted(graph.find_modules_that_directly_import(module)):
        found.setdefault(".".join(importer.split(".")[:3]), []).append(importer)
    return found


def tokens(paths: list[str]) -> int:
    total = 0
    for name in paths:
        path = ROOT / name
        if path.is_file():
            total += len(path.read_text(encoding="utf-8", errors="replace")) // CHARS_PER_TOKEN
    return total


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = repo_path(argv[0])
    items = components()
    component = owning_component(path, items)
    if component is None:
        print(f"{path}: not in any component of components.toml")
        return 1
    print(f"file:      {path}")
    owners = ", ".join(cast("list[str]", component["owner"]))
    print(f"component: {component['name']}  (layer {component['layer']}, owner {owners})")
    card = component.get("card")
    print(f"card:      {card or 'none'}")
    names = public_names(component)
    if names:
        print(f"interface: {', '.join(names)}")
    reading = [str(card)] if card else []
    tests: list[str] = []
    if card:
        tests += [f"office-agent/{t}" for t in card_tests(ROOT / str(card))]
    module = module_name(path)
    if module:
        tests += tests_importing(module)
        print("dependents (the modules that import this one):")
        users = dependents(module)
        for owner, modules in users.items():
            print(f"  {owner}: {', '.join(m.removeprefix(owner + '.') or m for m in modules)}")
        if not users:
            print("  none")
    tests += sibling_tests(path)
    tests = [t for t in dict.fromkeys(tests) if "*" not in t and (ROOT / t).is_file()]
    print("tests:")
    for test in tests:
        print(f"  {test}")
    reading += [path, *tests]
    size = tokens(reading)
    print(
        f"read: {len(reading)} files, about {size:,} tokens "
        f"(budget {BUDGET_FILES} files, {BUDGET_TOKENS:,} tokens)"
    )
    return 0 if len(reading) <= BUDGET_FILES and size <= BUDGET_TOKENS else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
