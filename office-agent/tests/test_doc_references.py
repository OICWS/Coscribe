"""A path named in a living document or a comment must be a file that exists.

Documents and comments name files, and nothing failed when a file moved: after
`web/session.py` became `conversation/session.py`, 46 places still sent a reader (or a
session looking for what to read) to the old path. This reads the Markdown files, the
comments and docstrings of the Python source and the comments of the TypeScript source, and
fails for a path that no file of the repository ends with.

Not checked: the documents that record history (`docs/history`, `docs/log`, `docs/assessments`,
the roadmap index, `PPTX_DESIGN.md`, the runtime README), because they name files as they were;
vendored code; tests (their fixtures name made-up files). A path that is not ours (a build
output, another project's file) goes in `tests/doc_reference_allowlist.txt`, a `CODEOWNERS` path.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import tokenize
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = Path(__file__).with_name("doc_reference_allowlist.txt")

HISTORY = (
    "docs/history/",
    "docs/log/",
    "docs/assessments/",
    "office-agent/ROADMAP.md",
    "office-agent/PPTX_DESIGN.md",
    "office-agent/src/coscribe/runtime_lg/README.md",
)
VENDORED = (
    "office-agent/src/coscribe/tools/_native_formula/",
    "office-agent/src/coscribe/tools/_native_docx_tracks/",
    "office-agent/src/coscribe/tools/_native_animation_presets/",
    "office-agent/src/coscribe/tools/_native_svg/",
)

_EXTENSIONS = "py|ts|tsx|md|json|toml|yml|yaml|sh|txt|css|html|js|mjs|ps1"
_PATH = re.compile(rf"(?<![\w./@-])((?:[\w.-]+/)+[\w.-]+\.(?:{_EXTENSIONS}))(?![\w])")
_FILE_NAME = re.compile(r"\.\w{1,4}$")


def _tracked() -> list[str]:
    """The files of the repository, including new ones not yet committed."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.splitlines()


def _suffixes(files: list[str]) -> set[str]:
    found: set[str] = set()
    for name in files:
        parts = name.split("/")
        found.update("/".join(parts[i:]) for i in range(len(parts)))
    return found


def _allowed_prefixes() -> list[str]:
    lines = ALLOWLIST.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def stale_in_text(text: str, suffixes: set[str], allowed: list[str]) -> list[str]:
    """The paths in `text` that no file ends with and that are not allowed."""
    stale = []
    for match in _PATH.finditer(text):
        path = match.group(1)
        segments = path.split("/")
        if any(c in path for c in "*<>{}$") or path.startswith(("./", "../")):
            continue
        # A shorthand list of files ("cli.py/web/app.py"), or tools named in a list ("Pandoc/Marp").
        if any(_FILE_NAME.search(segment) for segment in segments[:-1]) or segments[0][0].isupper():
            continue
        if path in suffixes or any(path.startswith(prefix) for prefix in allowed):
            continue
        stale.append(path)
    return stale


def _python_texts(path: Path) -> Iterator[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                yield token.start[0], token.string
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                docstring = ast.get_docstring(node, clean=False)
                if docstring and node.body and isinstance(node.body[0], ast.Expr):
                    yield node.body[0].lineno, docstring
    except (SyntaxError, tokenize.TokenError):
        return


def _texts(name: str) -> Iterator[tuple[int, str]]:
    path = ROOT / name
    if name.endswith(".md"):
        yield from enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    elif name.endswith(".py") and "/src/" in name:
        for line, text in _python_texts(path):
            for offset, part in enumerate(text.splitlines()):
                yield line + offset, part
    elif name.endswith((".ts", ".tsx")) and "/src/" in name:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith(("//", "/*", "*")):
                yield number, line


def find_stale() -> list[str]:
    files = _tracked()
    suffixes = _suffixes(files)
    allowed = _allowed_prefixes()
    found = []
    for name in files:
        if name.startswith(HISTORY) or name.startswith(VENDORED) or "node_modules" in name:
            continue
        for number, text in _texts(name):
            found += [f"{name}:{number}: {path}" for path in stale_in_text(text, suffixes, allowed)]
    return found


def test_every_path_named_in_a_document_or_comment_exists() -> None:
    stale = find_stale()

    assert not stale, (
        "A document or comment names a file that does not exist. Fix the path, or delete the "
        "mention if the file is gone (a comment that narrates a removed module belongs in the "
        "commit message):\n" + "\n".join(stale)
    )


@pytest.mark.parametrize(
    ("text", "stale"),
    [
        ("see `web/session.py` for it", ["web/session.py"]),
        ("see `conversation/session.py`", []),
        ("in tests/web/test_chat.py and src/coscribe/web/app.py", []),
        ("the shorthand cli.py/web/app.py names two", []),
        ("Pandoc/Marp/reveal.js are tools", []),
        ("a build output dist/index.html", []),
        ("an example ./MEMORY.md and ../x.txt", []),
        ("a pattern notes/*.txt or <date>/x.md", []),
    ],
)
def test_what_counts_as_a_stale_path(text: str, stale: list[str]) -> None:
    files = [
        "office-agent/src/coscribe/conversation/session.py",
        "office-agent/tests/web/test_chat.py",
        "office-agent/src/coscribe/web/app.py",
    ]

    assert stale_in_text(text, _suffixes(files), ["dist/"]) == stale
