"""Ablation of what makes SVG-page decks good: medium, design guidance, spec, checker.

Conditions (same fixed content outline per task):
  A  technical SVG contract only
  B  A + design guidance (ppt-master's executor Page Expression Core + aesthetic baseline)
  C  B + a deck design spec written first and given to every page
  D  C + one repair round driven by ppt-master's quality checker
ppt-master is used only as an instrument here (its converter and checker, unmodified).
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from openai import OpenAI

S = Path(__file__).resolve().parents[1]
PM = S / "research/ppt-master/skills/ppt-master"
REF = PM / "references"
PY = str(S / "pmvenv/bin/python")
OUT = S / "exp/runs"
MODEL = os.environ.get("ABL_MODEL", "deepseek-flash")
EFFORT = os.environ.get("ABL_EFFORT")  # none / low / high (DeepSeek default high)
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")
USAGE: list[dict] = []


def chat(system: str, user: str, *, json_mode: bool = False) -> str:
    for attempt in range(4):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_object"} if json_mode else None,
                **({"reasoning_effort": EFFORT} if EFFORT else {}),
            )
            u = r.usage
            USAGE.append({"in": u.prompt_tokens, "out": u.completion_tokens,
                          "hit": getattr(u, "prompt_cache_hit_tokens", 0) or 0})
            return r.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            print("retry", attempt, e, file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("model call failed")


TECH = """You write ONE slide as ONE SVG file. Output only the SVG, nothing else.
Technical contract (a converter turns the SVG into native, editable PowerPoint shapes):
- Root: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" data-pptx-page-role="cover|toc|section|content|ending" font-family="Microsoft YaHei, Arial">. 1 px = 1/96 inch.
- Allowed: rect (rx), circle, ellipse, line, polyline, polygon, path, text with tspan, g, defs with linearGradient / radialGradient, filter with feDropShadow, clipPath on images, marker for arrowheads.
- Forbidden: mask, <style>, class, CSS, foreignObject, textPath, @font-face, animate/set, script, iframe, HTML entities (write raw Unicode; escape & < > as &amp; &lt; &gt;).
- Paint: uppercase #RRGGBB, opacity via fill-opacity / stroke-opacity / opacity.
- Text never wraps by itself: one <text> per paragraph; extra lines are <tspan x="same x" dy="..."> children; inline emphasis is a non-positional <tspan> with its own fill / font-weight.
- A full-canvas <rect> first becomes the slide background.
- Group each logical unit (title, card, chart, list item...) in a top-level <g id="descriptive-id" data-pptx-bounds="x y w h"> whose bounds hold its content; top-level groups must not overlap; text must stay inside its group bounds and inside the canvas.
- Charts are drawn with shapes and text (bars, axes, labels); every number shown must come from the content given.
"""


def design_text() -> str:
    exe = (REF / "executor-base.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(exe) if l.startswith("## Page Expression Core"))
    end = next(i for i, l in enumerate(exe) if l.startswith("## 1. Effect Capability Discovery"))
    core = "\n".join(exe[start:end])
    ss = (REF / "shared-standards-core.md").read_text(encoding="utf-8")
    aesthetic = ss[ss.index("## 6. Shared Aesthetic Baseline"):]
    return "Design guidance (follow it):\n\n" + core + "\n\n" + aesthetic


PLAN_SYS = """You plan the content of a slide deck. Return JSON:
{"deck_title": str, "language": "zh-CN", "pages": [{"id": "P01", "role": "cover|toc|section|content|ending",
 "title": str, "takeaway": str, "content": str}]}
`content` holds everything the page must show (points, every number, table rows) as plain text.
Use only facts in the brief; keep numbers exact. Page count as the brief says."""

SPEC_SYS = """You are the deck's designer. Write a concise design spec (Markdown, under 900 words) that every page
will follow: audience and tone; a color system with roles and exact #RRGGBB (background, primary, accent,
text, secondary text, divider, chart series); typography (font, sizes for title / subtitle / body / caption /
hero number); a grid (margins, title zone, content field); a recurring visual motif; and for EACH page:
its layout structure (chosen for its information), the focal element, and density (anchor / dense /
breathing). Do not write SVG."""


def plan(task: Path, dest: Path) -> dict:
    f = dest / "outline.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    o = json.loads(chat(PLAN_SYS, task.read_text(encoding="utf-8"), json_mode=True))
    f.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    return o


def page_prompt(outline: dict, page: dict, spec: str | None) -> str:
    deck = "\n".join(f"{p['id']} [{p['role']}] {p['title']}" for p in outline["pages"])
    s = f"Deck: {outline['deck_title']}\nAll pages:\n{deck}\n\n"
    if spec:
        s += f"Design spec (binding):\n{spec}\n\n"
    s += f"Write page {page['id']} ({page['role']}).\nTitle: {page['title']}\nTakeaway: {page['takeaway']}\nContent:\n{page['content']}\n"
    return s


def extract_svg(text: str) -> str:
    m = re.search(r"<svg[\s\S]*</svg>", text)
    return m.group(0) if m else text


def new_project(name: str) -> Path:
    r = subprocess.run([PY, str(PM / "scripts/project_manager.py"), "init", name, "--format", "ppt169"],
                       capture_output=True, text=True, cwd=S / "exp")
    m = re.search(r"Project created: (.+)", r.stdout)
    assert m, r.stdout + r.stderr
    return Path(m.group(1).strip())


LOCK = (S / "exp/lock_template.md")


def export(proj: Path, n_pages: int) -> dict:
    lock = LOCK.read_text(encoding="utf-8")
    rhythm = "\n".join(f"- P{i:02d}: dense" for i in range(1, n_pages + 1))
    (proj / "spec_lock.md").write_text(lock.replace("{RHYTHM}", rhythm), encoding="utf-8")
    chk = subprocess.run([PY, str(PM / "scripts/svg_quality_checker.py"), str(proj), "--canonical-authoring",
                          "--stage", "final", "--json"], capture_output=True, text=True)
    report = json.loads((proj / "validation/svg_quality_report.json").read_text(encoding="utf-8"))
    args = [PY, str(PM / "scripts/svg_to_pptx.py"), str(proj), "--no-notes", "-a", "none"]
    ex = subprocess.run(args, capture_output=True, text=True)
    forced = False
    if ex.returncode != 0:
        forced = True
        ex = subprocess.run(args + ["--enable-dangerous-nonconforming-svg-export"], capture_output=True, text=True)
    pptx = sorted((proj / "exports").glob("*.pptx"))
    return {"checker_exit": chk.returncode, "report_summary": summarize(report), "forced_export": forced,
            "export_exit": ex.returncode, "export_tail": ex.stdout[-1500:] + ex.stderr[-1500:],
            "pptx": str(pptx[-1]) if pptx else None}


def summarize(report: dict) -> dict:
    out = {"errors": 0, "warnings": 0, "error_msgs": []}
    for f in report.get("files", report.get("results", [])) if isinstance(report, dict) else []:
        errs = f.get("errors", []) if isinstance(f, dict) else []
        warns = f.get("warnings", []) if isinstance(f, dict) else []
        errs = [e for e in errs if not NOISE.search(str(e))]
        warns = [w for w in warns if not NOISE.search(str(w))]
        out["errors"] += len(errs)
        out["warnings"] += len(warns)
        out["error_msgs"] += [f"{f.get('file', '?')}: {str(e)[:300]}" for e in errs]
    return out


# Findings about my generic stand-in spec_lock and canonical spelling, not about the page.
NOISE = re.compile(r"typography-size recurrence|Noncanonical compact authoring|Paint recommendation")


def page_findings(proj: Path, svg_name: str, errors_only: bool = False) -> list[str]:
    report = json.loads((proj / "validation/svg_quality_report.json").read_text(encoding="utf-8"))
    for f in report.get("files", report.get("results", [])):
        if isinstance(f, dict) and Path(str(f.get("file", ""))).name == svg_name:
            items = f.get("errors", []) + ([] if errors_only else f.get("warnings", []))
            return [str(x)[:400] for x in items if not NOISE.search(str(x))]
    return []


def render(pptx: str, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(dest), pptx],
                   capture_output=True, timeout=300)
    pdf = next(dest.glob("*.pdf"))
    subprocess.run(["pdftoppm", "-r", "60", "-png", str(pdf), str(dest / "page")], check=True)
    return sorted(dest.glob("page*.png"))


def run(task: Path, cond: str) -> dict:
    tdir = OUT / task.stem
    tdir.mkdir(parents=True, exist_ok=True)
    outline = plan(task, tdir)
    cdir = tdir / cond
    shutil.rmtree(cdir, ignore_errors=True)
    cdir.mkdir()
    t0 = time.time()
    n0 = len(USAGE)
    system = TECH + ("\n\n" + design_text() if cond[0] in "BCD" else "")
    spec = None
    if cond[0] in "CD":
        spec = chat(SPEC_SYS + "\n\n" + design_text(), json.dumps(outline, ensure_ascii=False))
        (cdir / "design_spec.md").write_text(spec, encoding="utf-8")
    pages = outline["pages"]
    with cf.ThreadPoolExecutor(6) as ex:
        svgs = list(ex.map(lambda p: extract_svg(chat(system, page_prompt(outline, p, spec))), pages))
    proj = new_project(f"{task.stem}_{cond}_{int(time.time())}")
    names = []
    for i, (p, svg) in enumerate(zip(pages, svgs), 1):
        name = f"P{i:02d}.svg"
        names.append(name)
        (proj / "svg_output" / name).write_text(svg, encoding="utf-8")
    result = export(proj, len(pages))
    result["first_pass"] = result["report_summary"]
    result["first_pass_exported"] = not result["forced_export"]

    def repair(kind: str) -> int:
        fixes = {}
        for name, p in zip(names, pages):
            found = page_findings(proj, name, errors_only=(kind == "errors"))
            if found:
                fixes[name] = (p, found)

        def fix(item):
            name, (p, found) = item
            cur = (proj / "svg_output" / name).read_text(encoding="utf-8")
            ask = ("Fix every error." if kind == "errors" else
                   "Fix every error; fix warnings about overflow, overlap and contrast.")
            msg = (page_prompt(outline, p, spec) + "\n\nYour current SVG:\n" + cur +
                   "\n\nA quality checker reported:\n- " + "\n- ".join(found) +
                   "\n\nReturn the corrected full SVG. " + ask)
            return name, extract_svg(chat(system, msg))

        with cf.ThreadPoolExecutor(6) as ex:
            for name, svg in ex.map(fix, fixes.items()):
                (proj / "svg_output" / name).write_text(svg, encoding="utf-8")
        return len(fixes)

    # Every condition must compile: A-C repair only what blocks export; D also repairs
    # the checker's overflow / overlap / contrast warnings once.
    result["repairs"] = []
    if cond[0] == "D":
        result["repairs"].append(("all", repair("all")))
        result.update(export(proj, len(pages)))
    for _ in range(2):
        if not result["forced_export"]:
            break
        result["repairs"].append(("errors", repair("errors")))
        result.update(export(proj, len(pages)))
    shutil.copytree(proj / "svg_output", cdir / "svg_output")
    result["seconds"] = round(time.time() - t0)
    calls = USAGE[n0:]
    result["calls"] = len(calls)
    result["tokens_in"] = sum(c["in"] for c in calls)
    result["tokens_out"] = sum(c["out"] for c in calls)
    result["cache_hit"] = sum(c["hit"] for c in calls)
    if result["pptx"]:
        shutil.copy(result["pptx"], cdir / "deck.pptx")
        result["pngs"] = [str(p) for p in render(str(cdir / "deck.pptx"), cdir / "render")]
    (cdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    task = Path(sys.argv[1])
    for cond in sys.argv[2:]:
        r = run(task, cond)
        print(cond, {k: v for k, v in r.items() if k not in ("export_tail", "pngs")})
