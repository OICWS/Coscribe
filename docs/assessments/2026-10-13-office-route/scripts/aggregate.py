"""Average the blind judge scores per condition across judge files and judge models."""

import glob
import json
import statistics
import sys
from collections import defaultdict

task_dir = sys.argv[1]
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
scores = defaultdict(lambda: defaultdict(list))
ranks = defaultdict(list)
files = 0
for f in sorted(glob.glob(f"{task_dir}/judge_*.json")):
    d = json.load(open(f))
    conds = set(d["mapping"].values())
    if only is not None and conds != only:
        continue
    files += 1
    judge = "gemini" if "gemini" in d["model"] else "deepseek"
    inv = {k.split()[-1]: v for k, v in d["mapping"].items()}
    for label, s in d["result"].get("decks", {}).items():
        c = inv.get(label.split()[-1])
        for dim in ("design", "content", "coherence"):
            if isinstance(s.get(dim), (int, float)):
                scores[c][(judge, dim)].append(s[dim])
    for i, label in enumerate(d["result"].get("ranking", []), 1):
        ranks[inv.get(label.split()[-1], label)].append(i)
print(f"{files} judge files")
for c in sorted(scores, key=lambda c: -statistics.mean(scores[c][next(iter(scores[c]))])):
    parts = []
    for judge in ("gemini", "deepseek"):
        ds = scores[c].get((judge, "design"), [])
        if ds:
            parts.append(f"{judge} design {statistics.mean(ds):.2f}±{(statistics.pstdev(ds)):.2f} (n={len(ds)})")
    allc = [x for (j, dim), v in scores[c].items() if dim == "content" for x in v]
    print(f"{c:4s} " + " | ".join(parts) + f" | content {statistics.mean(allc):.2f} | mean rank {statistics.mean(ranks[c]):.1f}")
