# ruff: noqa: E501 -- the rubric is prompt text, kept as written
"""A blind judge: a vision model scores the rendered pages of decks it cannot tell apart.

    python -m evals.judge evals/runs/baseline --rounds 3
    python -m evals.judge evals/runs/a evals/runs/b --rounds 3 --judge gemini:gemini-3.5-flash

With several runs, the decks every run made for one task go into one request under random
labels (`Deck P`, `Deck Q`...), drawn again each round, so neither position nor name tells
which route made which. With one run a round is a fresh absolute scoring of each deck. Each
answer is written into the task folder of every run it scored, under `judge/`, and
`aggregate_scores` turns the rounds into a mean and a spread per deck.

By default DeepSeek judges decks DeepSeek made; `--judge gemini:<model>` gives a judge from another
vendor, and each record names its judge so a reader can weigh the two apart.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Collection
from pathlib import Path
from typing import Any

from .tasks import discover

DEFAULT_JUDGE = "deepseek:deepseek-flash"
DEEPSEEK_URL = "https://api.deepseek.com/v1"
DIMENSIONS = ("design", "content", "coherence")
LABELS = "PQRSTUVW"

RUBRIC = """You are a strict senior presentation designer judging slide decks made for a real business audience.
You see the user's request, then the rendered pages of each deck.
Score each deck from 1 to 5 (decimals allowed) on:
- design: harmonious colors, clear hierarchy, layout that aids reading, alignment, spacing, no overlap, no overflow or clipped text, no awkward empty space, professional look;
- content: concise and readable text, numbers and labels legible, the page's message is clear, visuals support the message, and the deck does what the request asked;
- coherence: the deck reads as one consistent, progressing story with a consistent visual language.
Also list the 3 most serious concrete defects you see in each deck (page number + defect).
If there are several decks, rank them from best to worst.
Return JSON only: {"decks": {"<label>": {"design": n, "content": n, "coherence": n, "defects": [str]}}, "ranking": ["<label>", ...]}"""


def assign_labels(count: int, rng: random.Random) -> list[str]:
    """`Deck P`... in a random order: the i-th entry is the label of the i-th run."""
    labels = [f"Deck {c}" for c in LABELS[:count]]
    rng.shuffle(labels)
    return labels


def _is_score(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 5


def parse_answer(text: str, labels: list[str]) -> dict[str, Any]:
    """The judge's JSON, with every label present, every score a number in 1..5, the defects a
    list of strings and the ranking a permutation of the labels. A judge may answer `P` for
    `Deck P`: keys and the ranking are matched on the letter."""
    answer = json.loads(text)
    by_letter = {label.split()[-1]: label for label in labels}

    def label_of(key: Any) -> Any:
        return by_letter.get(str(key).split()[-1], key)

    decks = {label_of(k): v for k, v in answer["decks"].items()}
    for label in labels:
        for dimension in DIMENSIONS:
            value = decks[label][dimension]
            if not _is_score(value):
                raise ValueError(f"{label}.{dimension} is not a score from 1 to 5: {value!r}")
        defects = decks[label].get("defects", [])
        if not isinstance(defects, list) or not all(isinstance(d, str) for d in defects):
            raise ValueError(f"{label}.defects is not a list of strings: {defects!r}")
        decks[label]["defects"] = defects
    ranking = [label_of(x) for x in answer.get("ranking") or []]
    if len(labels) > 1 and sorted(map(str, ranking)) != sorted(labels):
        raise ValueError(f"ranking is not each of {labels} once: {ranking!r}")
    return {"decks": decks, "ranking": ranking if len(labels) > 1 else []}


def build_request(brief: str, decks: dict[str, list[Path]]) -> list[tuple[str, Path | None]]:
    """The request as (text, image-or-None) parts, decks in label order."""
    parts: list[tuple[str, Path | None]] = [(RUBRIC, None), (f"The user's request:\n{brief}", None)]
    for label in sorted(decks):
        parts.append((f"\n=== {label}: {len(decks[label])} pages ===", None))
        for number, page in enumerate(decks[label], start=1):
            parts.append((f"{label}, page {number}:", page))
    return parts


def _png_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def ask_deepseek(model: str, parts: list[tuple[str, Path | None]]) -> tuple[str, dict[str, int]]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=DEEPSEEK_URL)
    content: list[dict[str, Any]] = []
    for text, image in parts:
        content.append({"type": "text", "text": text})
        if image is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64," + _png_base64(image)},
                }
            )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
        reasoning_effort="high",
    )
    usage = response.usage
    return response.choices[0].message.content or "{}", {
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }


def ask_gemini(model: str, parts: list[tuple[str, Path | None]]) -> tuple[str, dict[str, int]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gemini_parts: list[dict[str, Any]] = []
    for text, image in parts:
        gemini_parts.append({"text": text})
        if image is not None:
            gemini_parts.append(
                {"inline_data": {"mime_type": "image/png", "data": _png_base64(image)}}
            )
    body = {
        "contents": [{"role": "user", "parts": gemini_parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    # The key goes in a header: a URL ends up in logs and in `URLError` text.
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        },
    )
    with urllib.request.urlopen(request, timeout=600) as handle:  # noqa: S310 -- fixed https host
        data = json.loads(handle.read())
    meta = data.get("usageMetadata", {})
    return data["candidates"][0]["content"]["parts"][0]["text"], {
        "input_tokens": meta.get("promptTokenCount", 0),
        "output_tokens": meta.get("candidatesTokenCount", 0),
    }


def ask(judge: str, parts: list[tuple[str, Path | None]]) -> tuple[str, dict[str, int]]:
    provider, _, model = judge.partition(":")
    asker = {"deepseek": ask_deepseek, "gemini": ask_gemini}.get(provider)
    if asker is None:
        raise ValueError(f"no judge for provider {provider!r}; use deepseek: or gemini:")
    return asker(model, parts)


def _retryable(exc: Exception) -> bool:
    """A wrong answer, a dropped connection, a rate limit or a server error is worth another
    try; a 400, 401, 403 or 404 will answer the same again (and a retry spends quota)."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or exc.code >= 500
    if isinstance(exc, urllib.error.URLError | OSError | ValueError | KeyError | TypeError):
        return True
    if isinstance(exc, AttributeError):
        return True  # a wrong-shaped answer: `.items()` on a list
    try:
        import openai
    except ImportError:
        return False
    return isinstance(
        exc,
        openai.APIConnectionError
        | openai.RateLimitError
        | openai.APITimeoutError
        | openai.InternalServerError,
    )


def judge_round(
    judge: str, brief: str, decks: dict[str, list[Path]], labels: list[str], retries: int = 3
) -> tuple[dict[str, Any], dict[str, int]]:
    parts = build_request(brief, decks)
    for attempt in range(retries):
        try:
            text, usage = ask(judge, parts)
            return parse_answer(text, labels), usage
        except Exception as exc:  # noqa: BLE001 -- sorted by `_retryable`, the rest is raised
            if attempt == retries - 1 or not _retryable(exc):
                raise
            print(f"judge retry: {type(exc).__name__}: {exc}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise AssertionError("unreachable")


def _pages(run: Path, task: str) -> list[Path]:
    return sorted((run / task / "render").glob("page-*.png"))


def run_set_id(runs: Collection[Path]) -> str:
    """Which runs were judged together, as a short name for the record file: judging the same
    task for another pairing must not overwrite this pairing's records."""
    paths = sorted(str(r.resolve()) for r in runs)
    return hashlib.sha1("\n".join(paths).encode(), usedforsecurity=False).hexdigest()[:8]


def check_runs(runs: list[Path]) -> None:
    if len(runs) > len(LABELS):
        raise ValueError(f"at most {len(LABELS)} runs can be judged together, got {len(runs)}")
    if len({r.resolve() for r in runs}) != len(runs):
        raise ValueError("the same run is given twice")


def judge_runs(runs: list[Path], task_names: list[str], judge: str, rounds: int, seed: int) -> int:
    """Returns the number of rounds that failed: one bad answer does not stop the batch."""
    check_runs(runs)
    rng = random.Random(seed)
    tag = judge.replace(":", "-")
    failures = 0
    for task in discover("all"):
        if task.name not in task_names:
            continue
        present = [r for r in runs if _pages(r, task.name)]
        for run in runs:
            if run not in present:
                print(f"{task.name}: {run} has no rendered pages, not scored", flush=True)
        if not present:
            continue
        group = run_set_id(present)
        for number in range(1, rounds + 1):
            labels = assign_labels(len(present), rng)
            decks = {
                label: _pages(run, task.name) for label, run in zip(labels, present, strict=True)
            }
            try:
                answer, usage = judge_round(judge, task.brief, decks, labels)
            except Exception as exc:  # noqa: BLE001 -- reported below, the other tasks go on
                failures += 1
                print(f"FAILED {task.name} round {number}: {type(exc).__name__}: {exc}", flush=True)
                continue
            for label, run in zip(labels, present, strict=True):
                folder = run / task.name / "judge"
                folder.mkdir(exist_ok=True)
                ranking = answer["ranking"]
                record = {
                    "judge": judge,
                    "round": number,
                    "seed": seed,
                    "label": label,
                    "runs": sorted(str(r.resolve()) for r in present),
                    "decks_in_request": len(present),
                    "scores": answer["decks"][label],
                    "rank": ranking.index(label) + 1 if label in ranking else None,
                    "usage": usage,
                }
                (folder / f"{tag}-{group}-round{number}-{seed}.json").write_text(
                    json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            print(f"judged {task.name} round {number}", flush=True)
    return failures


def aggregate_scores(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Mean and spread (population standard deviation) of each dimension over the rounds."""
    result: dict[str, dict[str, float]] = {}
    for dimension in DIMENSIONS:
        values = [float(r["scores"][dimension]) for r in records if dimension in r["scores"]]
        if values:
            result[dimension] = {
                "mean": statistics.fmean(values),
                "spread": statistics.pstdev(values),
                "n": float(len(values)),
            }
    return result


def load_records(
    run: Path,
    task: str,
    judge: str | None = None,
    joint_with: Collection[Path] | None = None,
) -> list[dict[str, Any]]:
    """The rounds of one deck. Scores from different judges, or from a lone request and a
    side-by-side one, are not one population, so a reader picks: `judge` keeps one judge;
    `joint_with` is None for the lone requests, or the runs judged together with this one
    (this run included) for that pairing."""
    folder = run / task / "judge"
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
    if judge is not None:
        records = [r for r in records if r.get("judge") == judge]
    if joint_with is None:
        return [r for r in records if r.get("decks_in_request", 1) == 1]
    wanted = sorted(str(r.resolve()) for r in joint_with)
    return [r for r in records if r.get("runs") == wanted]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("runs", nargs="+", type=Path, help="run folders made by evals.run")
    parser.add_argument(
        "--judge", default=DEFAULT_JUDGE, help="provider:model, deepseek: or gemini:"
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--tasks", default="all")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    names = [t.name for t in discover(args.tasks)]
    try:
        failures = judge_runs(args.runs, names, args.judge, args.rounds, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
