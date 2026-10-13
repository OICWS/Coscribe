"""Edit a generated deck through its SVG page sources: each page is offered the request and either
returns UNCHANGED or a full new SVG; changed pages are re-exported with ppt-master's converter.

Usage: edit_svg.py <run_dir> <name> "<request>"
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ablation as ab  # noqa: E402

SYS = ab.TECH + """
You are editing an existing slide. Apply the user's change request to this page only where it applies;
keep everything else identical (same layout, ids, coordinates, colors), unless the request asks otherwise.
Recompute any derived figure on this page that the change affects (totals, percentages, labels, bar heights).
If the request does not affect this page at all, answer exactly UNCHANGED."""


def main(run_dir: Path, name: str, request: str) -> None:
    src = run_dir / "svg_output"
    pages = sorted(src.glob("*.svg"))
    outline = (run_dir.parent / "outline.json").read_text(encoding="utf-8")
    t0 = time.time()
    n0 = len(ab.USAGE)

    def one(p: Path):
        msg = (f"Deck content outline (for context):\n{outline}\n\nChange request: {request}\n\n"
               f"Page {p.stem} SVG:\n{p.read_text(encoding='utf-8')}")
        out = ab.chat(SYS, msg).strip()
        return p.name, None if out.startswith("UNCHANGED") else ab.extract_svg(out)

    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(one, pages))
    proj = ab.new_project(f"edit_{name}_{int(time.time())}")
    changed = []
    for fname, svg in results:
        text = svg if svg is not None else (src / fname).read_text(encoding="utf-8")
        if svg is not None:
            changed.append(fname)
        (proj / "svg_output" / fname).write_text(text, encoding="utf-8")
    res = ab.export(proj, len(pages))
    out = run_dir.parent / f"edit_{name}"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(proj / "svg_output", out / "svg_output")
    calls = ab.USAGE[n0:]
    summary = {"request": request, "changed": changed, "seconds": round(time.time() - t0), "calls": len(calls),
               "tokens_in": sum(c["in"] for c in calls), "tokens_out": sum(c["out"] for c in calls),
               "checker": res["report_summary"], "pptx": res["pptx"]}
    if res["pptx"]:
        shutil.copy(res["pptx"], out / "deck.pptx")
        ab.render(str(out / "deck.pptx"), out / "render")
    (out / "result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
