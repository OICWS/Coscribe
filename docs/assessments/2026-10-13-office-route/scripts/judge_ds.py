"""The same blind judge as judge.py, with deepseek-flash (vision) as the judge model.

Usage: JUDGE_SEED=n judge_ds.py <task_dir> <cond> [<cond> ...]
"""

from __future__ import annotations

import base64
import json
import os
import random
import sys
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from judge import RUBRIC  # noqa: E402

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")


def main(task_dir: Path, conds: list[str]) -> None:
    seed = int(os.environ.get("JUDGE_SEED", "7"))
    rng = random.Random(seed)
    labels = [f"Deck {c}" for c in "PQRSTUVW"[: len(conds)]]
    rng.shuffle(labels)
    mapping = dict(zip(labels, conds))
    content: list[dict] = [{"type": "text", "text": RUBRIC},
                           {"type": "text", "text": "The content outline every deck was built from:\n"
                            + (task_dir / "outline.json").read_text(encoding="utf-8")}]
    for label in sorted(mapping):
        pages = sorted((task_dir / mapping[label] / "render").glob("page*.png"))
        content.append({"type": "text", "text": f"\n=== {label}: {len(pages)} pages ==="})
        for i, p in enumerate(pages, 1):
            content.append({"type": "text", "text": f"{label}, page {i}:"})
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()}})
    r = client.chat.completions.create(model="deepseek-flash", messages=[{"role": "user", "content": content}],
                                       response_format={"type": "json_object"}, reasoning_effort="high")
    result = json.loads(r.choices[0].message.content or "{}")
    out = {"model": "deepseek-flash", "mapping": mapping, "result": result,
           "usage": [r.usage.prompt_tokens, r.usage.completion_tokens]}
    (task_dir / f"judge_deepseek_{seed}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    inv = {k.split()[-1]: v for k, v in mapping.items()}
    for label, s in result.get("decks", {}).items():
        print(inv.get(label.split()[-1], label), s.get("design"), s.get("content"), s.get("coherence"))
    print("ranking:", [inv.get(x.split()[-1], x) for x in result.get("ranking", [])], "usage", out["usage"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
