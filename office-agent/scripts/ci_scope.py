"""Decide how much CI a pull request needs, from the files it changes (one path per stdin line).

Prints `scope=docs` when every changed file is documentation that only the documentation tests
read, `scope=selected` when every changed file can be placed in the import graph, and `scope=full`
otherwise. With `--tests` it reads the same paths and prints the test files to run instead: the
documentation tests for `docs`, the tests that can reach a change for `selected` (decision 0059),
nothing for `full` (pytest then collects every test). The Linux `test` job and the Windows
`pytest` job are required checks, so they always run and report; a `paths:` filter would leave
them unreported and block the merge. Markdown that the product reads (a skill's SKILL.md, a
template) is not documentation here.

A test is selected when the modules it imports, followed through every module they import,
reach a changed module; when its text names a changed file that is not Python; or when it is
one of `ALWAYS`, the tests that read the whole tree. A changed path the graph can't place (the
pytest configuration, the lockfile, a workflow, a file no test names) makes the scope `full`.
`main` and the nightly run always run every test.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # office-agent/
REPO = ROOT.parent
PREFIX = "office-agent/"

DOCS = (
    re.compile(r"docs/.+"),
    re.compile(r"[^/]+\.md"),  # README, AGENTS, CLAUDE, ARCHITECTURE at the root
    re.compile(r"office-agent/[^/]+\.md"),  # CLAUDE, README, ROADMAP, PPTX_DESIGN
    re.compile(r"office-agent/src/coscribe/(?:[\w-]+/)*(?:AGENTS|CLAUDE)\.md"),  # package cards
)

DOCS_TESTS = (
    "tests/test_doc_references.py",
    "tests/test_docs_layout.py",
    "tests/test_file_sizes.py",
    "tests/test_module_cards.py",
)

# Tests that walk the whole tree, or check that generated files agree with it: no import edge
# leads to them, so they run on every selected pull request.
ALWAYS = (
    *DOCS_TESTS,
    "tests/test_ci_scope.py",
    "tests/test_components_map.py",
    "tests/test_doc_files.py",
    "tests/test_doc_freshness.py",
    "tests/test_ratchet.py",
)

# The import roots a path can belong to, as (directory under office-agent/, module prefix).
PACKAGES = (("src/coscribe", "coscribe"), ("tests", "tests"), ("evals", "evals"))

# Changes no import edge or file name can place: they change how every test runs.
FULL = (
    re.compile(r"office-agent/(?:pyproject\.toml|uv\.lock|\.python-version)"),
    re.compile(r"office-agent/tests/(?:.+/)?conftest\.py"),
    re.compile(r"office-agent/tests/flaky_policy\.py"),
    re.compile(r"office-agent/scripts/(?:ci_scope\.py|check\.sh|install_locked\.py)"),
    # The workflows that run pytest; the others are read by the tests that name `.github`.
    re.compile(r"\.github/workflows/(?:office-agent-ci|windows)\.yml"),
)

# Folders whose files' tests are found by the folder's name in a test's text.
NAMED_BY_FOLDER = {
    ".github/": ".github",
    "office-agent/frontend/": "frontend",
    "office-agent-desktop/": "office-agent-desktop",
}

_MODULE_STRING = re.compile(r"(?:coscribe|evals|tests)(?:\.\w+)+")


def is_docs(path: str) -> bool:
    return any(rule.fullmatch(path) for rule in DOCS)


def plan(paths: list[str], graph: Graph | None = None) -> tuple[str, list[str]]:
    """The scope, and the test files to run (empty for `full`: pytest collects them all)."""
    changed = [p.strip() for p in paths if p.strip()]
    if changed and all(is_docs(p) for p in changed):
        return "docs", list(DOCS_TESTS)
    if not changed or any(rule.fullmatch(p) for p in changed for rule in FULL):
        return "full", []
    tests = (graph or Graph.build(ROOT)).select(changed)
    return ("full", []) if tests is None else ("selected", tests)


def scope(paths: list[str]) -> str:
    return plan(paths)[0]


def module_of(path: str) -> str | None:
    """The dotted module a repository path is, or None when it is not Python in a package."""
    if not path.startswith(PREFIX) or not path.endswith(".py"):
        return None
    rel = path[len(PREFIX) : -len(".py")]
    for folder, prefix in PACKAGES:
        if rel == folder or rel.startswith(folder + "/"):
            parts = [prefix, *rel[len(folder) :].strip("/").split("/")]
            if parts[-1] == "__init__":
                parts.pop()
            return ".".join(p for p in parts if p)
    if rel.startswith("scripts/") and rel.count("/") == 1:
        return "scripts." + rel.split("/")[1]
    return None


class Graph:
    """Which module uses which, over coscribe, the tests, the evaluations and the scripts.

    An edge goes to the module that defines what is imported. A package whose `__init__.py`
    only re-exports (imports, `__all__`, a docstring) is a public interface, not a dependency
    on everything it lists: `from coscribe.tools import run_script` is an edge to the module
    that defines `run_script` and to the `__init__` itself, not to every tool. Python does run
    the parents' `__init__` on import, so a module that fails to import fails its siblings'
    tests too; mypy, ruff and the module's own tests catch that before the import graph matters.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.imports: dict[str, set[str]] = defaultdict(set)
        self.text: dict[str, str] = {}  # test module -> its source, for names of other files
        self.files: dict[str, str] = {}  # module -> repository path
        self.packages: set[str] = set()
        self.reexports: dict[str, dict[str, str]] = {}  # pure package -> name -> module
        self._raw: dict[str, list[tuple[str, tuple[str, ...]]]] = {}

    @classmethod
    def build(cls, root: Path) -> Graph:
        graph = cls(root)
        for path in graph._sources():
            rel = str(path.relative_to(root.parent)).replace("\\", "/")
            module = module_of(rel)
            if module is None:
                continue
            graph.files[module] = rel
            if path.name == "__init__.py":
                graph.packages.add(module)
        for module, rel in graph.files.items():
            source = (root.parent / rel).read_text(encoding="utf-8", errors="replace")
            graph._read(module, source)
        for module, raw in graph._raw.items():
            edges = graph.imports[module]
            if module in graph.reexports:
                continue  # a pure interface: its importers get edges to the definers instead
            for base, names in raw:
                edges.update(graph._targets(base, names))
            edges.discard(module)
        graph._conftests()
        return graph

    def _sources(self) -> Iterator[Path]:
        for folder, _ in PACKAGES:
            base = self.root / folder
            if base.is_dir():
                yield from (p for p in base.rglob("*.py") if "node_modules" not in p.parts)
        yield from (self.root / "scripts").glob("*.py")

    def _read(self, module: str, source: str) -> None:
        if module.startswith("tests."):
            self.text[module] = source
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return
        package = module if module in self.packages else module.rpartition(".")[0]
        raw: list[tuple[str, tuple[str, ...]]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                raw.extend((alias.name, ()) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = _absolute(node, package)
                if base is not None:
                    raw.append((base, tuple(alias.name for alias in node.names)))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # `monkeypatch.setattr("coscribe.x.y", ...)`, `python -m coscribe.cli`.
                raw.extend((name, ()) for name in _MODULE_STRING.findall(node.value))
        self._raw[module] = raw
        if module in self.packages and _only_reexports(tree):
            exported: dict[str, str] = {}
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    base = _absolute(node, package)
                    for alias in node.names:
                        if base is not None:
                            exported[alias.asname or alias.name] = f"{base}.{alias.name}"
            self.reexports[module] = exported

    def _owner(self, name: str) -> str:
        """The longest known module a dotted name starts with (`a.b.attr` -> `a.b`); the name
        itself when none is known, so an import of a deleted module still matches it."""
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in self.files:
                return candidate
        return name

    def _targets(self, base: str, names: tuple[str, ...], depth: int = 0) -> set[str]:
        """The modules `from base import names` (or `import base`, with no names) depends on."""
        owner = self._owner(base)
        found = {owner, base}  # `base` itself matches when it is a module this change deleted
        if depth > 10:
            return found
        if owner != base:
            # `coscribe.tools.run_script` written as a string: an attribute of `owner`.
            if owner in self.reexports:
                found |= self._targets(owner, (base[len(owner) + 1 :].split(".")[0],), depth + 1)
            return found
        for name in names:
            submodule = f"{owner}.{name}"
            if submodule in self.files:
                found.add(submodule)
                continue
            target = self.reexports.get(owner, {}).get(name)
            if target is None:
                continue
            if target in self.files:
                found.add(target)
                continue
            source, _, attr = target.rpartition(".")
            found |= self._targets(source, (attr,), depth + 1)
        return found

    def _conftests(self) -> None:
        """A conftest's autouse fixtures run around every test below it. They touch the modules
        the conftest names, not what those import, so a test gains them as direct imports only
        (`reaches` follows such an edge only from a module that changed itself)."""
        for module, rel in self.files.items():
            if not rel.endswith("/conftest.py"):
                continue
            direct = {m for m in self.imports[module] if self._known(m)}
            folder = module.rpartition(".")[0]
            for test in self.text:
                if test.startswith(folder + "."):
                    self.imports[test].update(f"conftest:{m}" for m in direct)

    def _known(self, name: str) -> bool:
        return name in self.files

    def tests(self) -> list[str]:
        return sorted(m for m in self.text if m.rpartition(".")[2].startswith("test_"))

    def reaches(self, changed: set[str]) -> set[str]:
        """Every module whose imports, followed all the way, include a changed one, and every
        test under a conftest that names a changed module."""
        users: dict[str, set[str]] = defaultdict(set)
        fixture_users: dict[str, set[str]] = defaultdict(set)
        for module, edges in self.imports.items():
            for name in edges:
                if name.startswith("conftest:"):
                    fixture_users[name[len("conftest:") :]].add(module)
                else:
                    users[name].add(module)
        start = set(changed)
        for name in changed:
            start |= fixture_users.get(name, set())
        reached: set[str] = set()
        todo = list(start)
        while todo:
            name = todo.pop()
            for user in users.get(name, ()):
                if user not in reached:
                    reached.add(user)
                    todo.append(user)
        return reached | (start & set(self.files))

    def select(self, paths: Iterable[str]) -> list[str] | None:
        """The test files to run for these changed paths, or None when one can't be placed."""
        changed_modules: set[str] = set()
        named: list[str] = []
        for path in paths:
            if is_docs(path):
                continue
            module = module_of(path)
            if module is not None:
                changed_modules.add(module)
                continue
            data = self._data_owner(path)
            if data is not None:
                changed_modules.add(data)
                continue
            folder = next((n for p, n in NAMED_BY_FOLDER.items() if path.startswith(p)), None)
            named.append(folder or path.rpartition("/")[2])
        selected = {m for m in self.reaches(changed_modules) if m in self.text}
        for name in named:
            hits = {m for m, text in self.text.items() if name in text}
            if not hits:
                return None
            selected |= hits
        selected |= {module_of(PREFIX + t) or "" for t in ALWAYS}
        return sorted(
            self.files[m][len(PREFIX) :]
            for m in selected
            if m in self.files and m.rpartition(".")[2].startswith("test_")
        )

    def _data_owner(self, path: str) -> str | None:
        """A file that is not Python inside coscribe belongs to the package that holds it: the
        code reading it is there or imports it, and every importer of a module in a package
        runs the package's __init__."""
        prefix = PREFIX + "src/coscribe/"
        if not path.startswith(prefix):
            return None
        parts = path[len(PREFIX) + len("src/") :].split("/")[:-1]
        while parts:
            name = ".".join(parts)
            if name in self.packages:
                return name
            parts.pop()
        return None


def _only_reexports(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if all(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                continue
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.dump(node.test):
            continue
        return False
    return True


def _absolute(node: ast.ImportFrom, package: str) -> str | None:
    if node.level == 0:
        return node.module
    parts = package.split(".")
    if node.level > 1:
        parts = parts[: -(node.level - 1)]
    if not parts:
        return None
    return ".".join([*parts, node.module] if node.module else parts)


def main(argv: list[str]) -> int:
    kind, tests = plan(sys.stdin.read().splitlines())
    if argv == ["--tests"]:
        print(" ".join(tests))
    else:
        print(f"scope={kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
