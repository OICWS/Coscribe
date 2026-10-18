"""A tracked text file over 200 KB costs a session its context and slows every review.

The files below are the ones that already are. A new one fails this test: split it, or, if
it is data or generated output nobody should read whole, mark it in `.gitattributes`
(`linguist-generated=true`) and `.ignore`, and add it here with the reason.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIMIT_BYTES = 200_000

ALLOWED = {
    "docs/history/roadmap-through-2026-10-08.md": "frozen phase history, grepped by phase heading",
    "office-agent/src/coscribe/tools/_native_animation_presets/animation_presets.json": (
        "generated animation preset data"
    ),
    "site/index.html": "generated project site page",
    "office-agent/frontend/package-lock.json": "npm's generated lockfile",
    "office-agent/tests/test_presentations_tool.py": "tests of presentations.py, split with it",
    "office-agent/src/coscribe/tools/_ooxml_schemas/transitional/sml.xsd": (
        "vendored ECMA-376 schema"
    ),
    "office-agent/tests/golden/docx/_shared.txt": "shared docx golden data",
    "office-agent/PPTX_DESIGN.md": "numbered pptx design decisions, read by section",
    "office-agent/src/coscribe/runtime_lg/README.md": "runtime findings, searched, not read whole",
    "office-agent/src/coscribe/tools/_native_svg/pptx_shapes/data/presetShapeDefinitions.xml": (
        "vendored DrawingML preset geometry (Apache POI)"
    ),
}


def _blob_sizes() -> dict[str, int]:
    # The size git stores, not the working-tree file's: a Windows checkout converts line
    # endings and would push a file near the limit over it.
    staged = subprocess.run(
        ["git", "ls-files", "-s", "-z"], cwd=REPO, check=True, capture_output=True
    ).stdout.decode()
    blobs = {}
    for entry in filter(None, staged.split("\0")):
        meta, name = entry.split("\t", 1)
        mode, blob, _stage = meta.split()
        if mode != "160000":  # a submodule is a commit, not a blob
            blobs[name] = blob
    sizes = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objectsize)"],
        cwd=REPO,
        check=True,
        capture_output=True,
        input="".join(f"{blob}\n" for blob in blobs.values()).encode(),
    ).stdout.decode()
    size_of = {line.split()[0]: int(line.split()[1]) for line in sizes.splitlines()}
    return {name: size_of[blob] for name, blob in blobs.items()}


def _oversized_text_files() -> list[str]:
    found = []
    for name, size in _blob_sizes().items():
        path = REPO / name
        if size <= LIMIT_BYTES or not path.is_file():
            continue
        # A NUL byte in the first block is git's own test for binary.
        with path.open("rb") as handle:
            head = handle.read(8000)
        if b"\0" in head:
            continue
        found.append(name)
    return found


def test_no_new_large_text_file() -> None:
    new = sorted(set(_oversized_text_files()) - set(ALLOWED))
    assert not new, (
        f"Tracked text files over {LIMIT_BYTES // 1000} KB, not on the allow-list: {new}. "
        "Split the file, or mark it as data (`linguist-generated=true` in .gitattributes and a "
        "line in .ignore) and add it to ALLOWED in tests/test_file_sizes.py with a reason."
    )
