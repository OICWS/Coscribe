"""The editor's source round trip, judged by the server (batch 10 item 10): every section that the
panel's TypeScript produces (the ten layouts, each insert, text written back, a changed tag,
notes) must be accepted by `parse_section` and compile without errors.

vitest writes the sources (`frontend/src/components/slides/sectionDom.test.ts`, which also checks
what each function does on its own, in a DOM environment for that file only) and this test reads
them, so the real editor code runs and the Python side stays the judge.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from coscribe.tools.office.pptx.engine import compile_sections
from coscribe.tools.office.pptx.engine.section_format import parse_section

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
_NPX = shutil.which("npx.cmd" if sys.platform == "win32" else "npx")

pytestmark = pytest.mark.skipif(
    _NPX is None or not (FRONTEND / "node_modules" / "vitest").is_dir(),
    reason="needs node and the frontend's dependencies (npm ci)",
)


@pytest.fixture(scope="module")
def sources(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    out = tmp_path_factory.mktemp("slide-sources") / "sources.json"
    assert _NPX is not None
    run = subprocess.run(
        [_NPX, "vitest", "run", "src/components/slides/sectionDom.test.ts"],
        cwd=FRONTEND,
        env={**os.environ, "SLIDE_SOURCES_OUT": str(out)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    found: dict[str, str] = json.loads(out.read_text(encoding="utf-8"))
    return found


def test_every_source_the_editor_produces_is_accepted_by_the_servers_parser(
    sources: dict[str, str],
) -> None:
    assert len(sources) > 20
    for name, text in sources.items():
        try:
            parse_section(text)
        except Exception as e:  # noqa: BLE001 - the name of the source is the point
            pytest.fail(f"{name}: {e}\n{text}")


def test_every_source_compiles_without_errors(sources: dict[str, str], tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    Image.new("RGB", (400, 300), (30, 120, 200)).save(tmp_path / "assets" / "picture.png")
    names = list(sources)
    report = compile_sections(
        [(f"{i:03d}.html", sources[name]) for i, name in enumerate(names, start=1)],
        tmp_path / "deck.pptx",
        resource_root=tmp_path,
        sections_dir=tmp_path,
    )
    failed = {names[i]: page.errors for i, page in enumerate(report.pages) if page.errors}
    assert not failed, failed
