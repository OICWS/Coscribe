"""Condition E: coscribe's own route, one shot: write_pptx (+ layout directives, theme) and add_pptx_chart.

Same outline as A-D. The model gets the built-in pptx skill and the two tools' docstrings, as the agent
would, and returns the calls as JSON; the calls run through coscribe's real tool functions.
Run with office-agent's venv.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from openai import OpenAI

from coscribe.tools.presentations import build_presentation_tools

S = Path(__file__).resolve().parents[1]
SKILL = Path("/home/user/coscribe/office-agent/src/coscribe/builtin_skills/pptx/SKILL.md")
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")


def main(task_stem: str) -> None:
    tdir = S / "exp/runs" / task_stem
    outline = json.loads((tdir / "outline.json").read_text(encoding="utf-8"))
    cdir = tdir / "E"
    cdir.mkdir(exist_ok=True)
    tools = {t.__name__: t for t in build_presentation_tools(cdir)}
    system = (
        "You build a slide deck with coscribe's PowerPoint tools. Skill guidance:\n\n"
        + SKILL.read_text(encoding="utf-8")
        + "\n\nTool write_pptx:\n" + (tools["write_pptx"].__doc__ or "")
        + "\n\nTool add_pptx_chart:\n" + (tools["add_pptx_chart"].__doc__ or "")
        + '\n\nReturn JSON only: {"theme": str, "content": str, "charts": [{"slide": int, "chart_type": str, '
        '"data": str, "title": str}]}. `content` is write_pptx\'s markdown (layout directives allowed).'
    )
    t0 = time.time()
    r = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": json.dumps(outline, ensure_ascii=False)}],
        response_format={"type": "json_object"},
    )
    plan = json.loads(r.choices[0].message.content or "{}")
    (cdir / "calls.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    result: dict = {"write": tools["write_pptx"](path="deck.pptx", content=plan["content"], theme=plan.get("theme", ""))}
    result["charts"] = []
    for c in plan.get("charts", []):
        try:
            result["charts"].append(tools["add_pptx_chart"](path="deck.pptx", **c))
        except Exception as e:  # noqa: BLE001
            result["charts"].append({"error": str(e)})
    result["seconds"] = round(time.time() - t0)
    result["tokens_in"], result["tokens_out"] = r.usage.prompt_tokens, r.usage.completion_tokens
    (cdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    rd = cdir / "render"
    rd.mkdir(exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(rd), str(cdir / "deck.pptx")],
                   capture_output=True, timeout=300)
    subprocess.run(["pdftoppm", "-r", "60", "-png", str(next(rd.glob("*.pdf"))), str(rd / "page")], check=True)
    print(json.dumps({k: v for k, v in result.items() if k != "write"}, ensure_ascii=False, default=str)[:1500])


if __name__ == "__main__":
    main(sys.argv[1])
