#!/usr/bin/env python3
"""The reviewer's input for one pull request, as Markdown on stdout.

    python scripts/review_pack.py 372            # a PR of this repository, read with `gh`
    python scripts/review_pack.py 372 --repo OICWS/coscribe

It collects what a review needs and a diff alone does not show: the components and cards the
change touches, the invariant paths and snapshots it moves, the decisions it links, the ratchet
numbers it changes, and the "Not verified" items. It reads only; it posts nothing.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "office-agent/quality/baseline.json"
SNAPSHOTS = (
    "office-agent/tests/tool_schemas.txt",
    "office-agent/tests/web_routes.txt",
    "office-agent/tests/openapi.json",
    "office-agent/tests/wire_events.txt",
)


# CLAUDE.md also counts "anything that opens a network listener", which no glob can say.
LISTENER_PATHS = (
    "office-agent/src/coscribe/web/app.py",
    "office-agent/src/coscribe/web/browser_panel.py",
)


def _slice() -> Any:
    spec = importlib.util.spec_from_file_location(
        "slice_script", Path(__file__).with_name("slice.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def invariant_patterns(codeowners: str) -> list[str]:
    """The paths CODEOWNERS lists under its "Invariant paths" comment, as repo-relative globs."""
    lines = codeowners.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("# Invariant paths")), None)
    found = []
    for line in lines[start + 1 :] if start is not None else []:
        if line.startswith("/"):
            found.append(line.split()[0].lstrip("/"))
    return found


def touched_invariants(files: list[str], patterns: list[str]) -> list[str]:
    def matches(path: str, pattern: str) -> bool:
        return fnmatch.fnmatch(path, pattern) or (
            pattern.endswith("/") and path.startswith(pattern)
        )

    return [f for f in files if any(matches(f, p) for p in patterns)]


def ratchet_moves(before: dict[str, dict[str, int]], after: dict[str, dict[str, int]]) -> list[str]:
    """Each baseline number the change moves; a new name or a bigger number is the loosening."""
    lines = []
    for metric in sorted(set(before) | set(after)):
        old, new = before.get(metric, {}), after.get(metric, {})
        for name in sorted(set(old) | set(new)):
            if name not in old:
                lines.append(f"- WORSE {metric}: new {name} = {new[name]}")
            elif name not in new:
                lines.append(f"- better {metric}: {name} is gone (was {old[name]})")
            elif new[name] > old[name]:
                lines.append(f"- WORSE {metric}: {name} {old[name]} -> {new[name]}")
            elif new[name] < old[name]:
                lines.append(f"- better {metric}: {name} {old[name]} -> {new[name]}")
    return lines


def not_verified(text: str) -> str:
    """The text under a "Not verified" heading or label, up to the next heading."""
    match = re.search(
        r"(?:^#+ *Not verified *\n|^Not verified:)(.*?)(?=^#+ |\Z)", text, re.S | re.M
    )
    return match.group(1).strip() if match else ""


def linked_decisions(text: str) -> list[str]:
    return sorted(set(re.findall(r"docs/decisions/\d{4}-[\w-]+\.md", text)))


def render(
    meta: dict[str, Any],
    files: list[str],
    components: dict[str, dict[str, Any]],
    invariants: list[str],
    snapshots: list[str],
    moves: list[str],
    log_texts: dict[str, str],
) -> str:
    out = [
        f"# Review pack: #{meta['number']} {meta['title']}",
        "",
        f"{len(files)} files, +{meta['additions']} -{meta['deletions']}, "
        f"`{meta['baseRefName']}` <- `{meta['headRefName']}`.",
        "",
        "## Components touched",
    ]
    for name, info in sorted(components.items()):
        card = info["card"] or "no card"
        out.append(f"- `{name}`: {len(info['files'])} files, card {card}")
        if info["interface"]:
            out.append(f"  - interface: {', '.join(info['interface'])}")
    if not components:
        out.append("- none of the files belongs to a component")
    out += ["", "## Invariant paths touched"]
    if invariants:
        out.append("These need an independent review (both owners are in .github/CODEOWNERS):")
        out += [f"- `{path}`" for path in invariants]
    else:
        out.append("- none")
    out += ["", "## Snapshots changed"]
    out += [f"- `{path}`" for path in snapshots] or ["- none"]
    out += ["", "## Ratchet numbers moved"]
    out += moves or ["- none"]
    out += ["", "## Decisions linked"]
    decisions = linked_decisions(meta.get("body") or "")
    out += [f"- `{d}`" for d in decisions] or ["- none"]
    out += ["", "## Not verified"]
    body_item = not_verified(meta.get("body") or "")
    if body_item:
        out += ["From the PR text:", body_item]
    for path, text in sorted(log_texts.items()):
        item = not_verified(text)
        if item:
            out += [f"From `{path}`:", item]
    if len(out) and out[-1] == "## Not verified":
        out.append("- nothing listed")
    return "\n".join(out) + "\n"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def _repo_of_checkout() -> str:
    url = _git("remote", "get-url", "origin").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    if not match:
        raise SystemExit(f"cannot read OWNER/NAME from the origin url {url!r}; pass --repo")
    return match.group(1)


def _api(path: str, *extra: str) -> str:
    # REST, not `gh pr view`: that one goes through GraphQL, which some environments block.
    return subprocess.run(
        ["gh", "api", path, *extra], capture_output=True, text=True, check=True
    ).stdout


def gather(number: int, repo: str | None) -> str:
    repo = repo or _repo_of_checkout()
    pull = json.loads(_api(f"repos/{repo}/pulls/{number}"))
    meta = {
        "number": number,
        "title": pull["title"],
        "body": pull["body"],
        "baseRefName": pull["base"]["ref"],
        "headRefName": pull["head"]["ref"],
        "additions": pull["additions"],
        "deletions": pull["deletions"],
    }
    files = _api(f"repos/{repo}/pulls/{number}/files", "--paginate", "--jq", ".[].filename").split()
    ref = f"refs/review-pack/{number}"
    _git("fetch", "-q", "origin", f"refs/pull/{number}/head:{ref}", meta["baseRefName"])
    head = ref
    base = _git("merge-base", f"origin/{meta['baseRefName']}", head).strip()
    slicer = _slice()
    items = slicer.components()
    components: dict[str, dict[str, Any]] = {}
    for path in files:
        component = slicer.owning_component(path, items)
        if component is None:
            continue
        info = components.setdefault(
            str(component["name"]),
            {
                "card": component.get("card"),
                "interface": slicer.public_names(component),
                "files": [],
            },
        )
        info["files"].append(path)

    def baseline(ref: str) -> dict[str, dict[str, int]]:
        try:
            loaded: dict[str, dict[str, int]] = json.loads(_git("show", f"{ref}:{BASELINE}"))
            return loaded
        except subprocess.CalledProcessError:
            return {}

    codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    log_texts = {
        p: _git("show", f"{head}:{p}")
        for p in files
        if p.startswith("docs/log/") and p.endswith(".md") and p != "docs/log/README.md"
    }
    return render(
        meta,
        files,
        components,
        touched_invariants(files, [*invariant_patterns(codeowners), *LISTENER_PATHS]),
        [f for f in files if f in SNAPSHOTS],
        ratchet_moves(baseline(base), baseline(head)),
        log_texts,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pr", type=int)
    parser.add_argument("--repo", help="OWNER/NAME, when not the repository of the checkout")
    args = parser.parse_args(argv)
    sys.stdout.write(gather(args.pr, args.repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
