"""Builds a deck from two slide pages in a workspace, for the Slides panel spec:
`python build_deck.py <workspace> <name>` writes `<name>.pptx` and its pages folder."""

import shutil
import sys
from pathlib import Path

from coscribe.tools.office.pptx.engine import build_deck
from tests.test_deck_engine import CARDS, COVER

workspace, name = Path(sys.argv[1]), sys.argv[2]
folder = workspace / f"{name}-pages"
shutil.rmtree(folder, ignore_errors=True)
folder.mkdir(parents=True)
(folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
(folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
report = build_deck(folder, workspace / f"{name}.pptx", resource_root=workspace)
if not report.ok:
    sys.exit(f"the deck did not build: {report}")
