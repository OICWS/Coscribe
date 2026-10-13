"""Blind judge for the ablation decks: Gemini scores rendered pages (PPTEval-style) and ranks decks.

Usage: judge.py <task_dir> <cond> [<cond> ...]
Decks are relabelled with random letters; the mapping is stored next to the scores.
"""

from __future__ import annotations

import base64
import json
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.environ.get("JUDGE_MODEL", "gemini-3.1-pro-preview")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={os.environ['GEMINI_API_KEY']}"

RUBRIC = """You are a strict senior presentation designer judging slide decks made for a real business audience.
Score each deck on a 1-5 scale (decimals allowed) on:
- design: harmonious colors, clear hierarchy, layout that aids reading, alignment, spacing, no overlap, no overflow or clipped text, no awkward empty space, professional look;
- content: concise and readable text, numbers and labels legible, the page's message is clear, visuals support the message;
- coherence: the deck reads as one consistent, progressing story with a consistent visual language.
Also list the 3 most serious concrete defects you see in each deck (page number + defect).
Finally rank all decks from best to worst.
Return JSON only: {"decks": {"<label>": {"design": n, "content": n, "coherence": n, "defects": [str]}}, "ranking": ["<label>", ...]}"""


def part_image(path: Path) -> dict:
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(path.read_bytes()).decode()}}


def main(task_dir: Path, conds: list[str]) -> None:
    rng = random.Random(int(os.environ.get("JUDGE_SEED", "7")))
    labels = [f"Deck {c}" for c in "PQRSTUVW"[: len(conds)]]
    rng.shuffle(labels)
    mapping = dict(zip(labels, conds))
    parts: list[dict] = [{"text": RUBRIC}]
    brief = (task_dir / "outline.json").read_text(encoding="utf-8")
    parts.append({"text": "The content outline every deck was built from:\n" + brief})
    for label in sorted(mapping):
        cond = mapping[label]
        pages = sorted((task_dir / cond / "render").glob("page*.png"))
        parts.append({"text": f"\n=== {label}: {len(pages)} pages ==="})
        for i, p in enumerate(pages, 1):
            parts.append({"text": f"{label}, page {i}:"})
            parts.append(part_image(p))
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    import time
    models = [MODEL] + [m for m in ("gemini-3.5-flash", "gemini-3.6-flash") if m != MODEL]
    for attempt in range(10):
        model = models[attempt % len(models)]
        url = URL.replace(f"/models/{MODEL}:", f"/models/{model}:")
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or attempt == 9:
                raise
            time.sleep(30)
    out_model = model
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    out = {"model": out_model, "mapping": mapping, "result": result}
    (task_dir / f"judge_{MODEL}_{os.environ.get('JUDGE_SEED', '7')}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    inv = {k.split()[-1]: v for k, v in mapping.items()}
    for label, s in result["decks"].items():
        print(inv.get(label.split()[-1], label), s.get("design"), s.get("content"), s.get("coherence"))
    print("ranking:", [inv.get(x.split()[-1], x) for x in result.get("ranking", [])])


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
