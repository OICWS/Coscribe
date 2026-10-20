"""Builds a deck of two section pages (HTML, as the Slides editor writes them) in a workspace, for
the properties-panel and container specs: `python build_section_deck.py <workspace> <name>` writes
`<name>.pptx` and its pages folder. The first slide holds a text box, a table and a shape; the
second only a title, with room for a container to be inserted; the third has a row container of two
texts and a loose text below it."""

import shutil
import sys
from pathlib import Path

from coscribe.tools.office.pptx.engine import build_deck

PANELS = """<section>
  <p id="note" style="left:160px;top:140px;width:900px;height:120px;font-size:32px">Panel text</p>
  <table id="grid" style="left:160px;top:380px;width:900px;height:240px;font-size:28px;border-color:#CBD2DC">
    <tr><th style="background:#1A73E8;color:#FFFFFF">Name</th><th style="background:#1A73E8;color:#FFFFFF">Value</th></tr>
    <tr><td>Alpha</td><td>1</td></tr>
    <tr><td>Beta</td><td>2</td></tr>
  </table>
  <x-shape id="card" data-shape="round-rect" style="left:1250px;top:140px;width:400px;height:240px;background:#1A73E8;border-radius:24px"/>
</section>"""

EMPTY = """<section>
  <p id="heading" style="left:160px;top:60px;width:900px;height:80px;font-size:40px">Containers</p>
</section>"""

ROW = """<section>
  <x-stack id="row" data-layout="row" style="left:160px;top:200px;width:1600px;height:300px;gap:40px;padding:30px;background:#F3F4F6;border-radius:16px">
    <p id="first" style="flex-grow:1;font-size:36px">First</p>
    <p id="second" style="flex-grow:1;font-size:36px">Second</p>
  </x-stack>
  <p id="loose" style="left:160px;top:800px;width:600px;height:80px;font-size:36px">Loose</p>
</section>"""

workspace, name = Path(sys.argv[1]), sys.argv[2]
folder = workspace / f"{name}-pages"
shutil.rmtree(folder, ignore_errors=True)
folder.mkdir(parents=True)
(folder / "01-panels.html").write_text(PANELS, encoding="utf-8")
(folder / "02-empty.html").write_text(EMPTY, encoding="utf-8")
(folder / "03-row.html").write_text(ROW, encoding="utf-8")
report = build_deck(folder, workspace / f"{name}.pptx", resource_root=workspace)
if not report.ok:
    sys.exit(f"the deck did not build: {report}")
