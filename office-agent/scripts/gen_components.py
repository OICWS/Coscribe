"""Generate `docs/components.md` and the generated block of `.github/CODEOWNERS` from
`components.toml`.

    python scripts/gen_components.py            write both files
    python scripts/gen_components.py --check    exit 1 when either is stale (CI)
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "components.toml"
DOC = ROOT / "docs" / "components.md"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
PYPROJECT = ROOT / "office-agent" / "pyproject.toml"
SOURCE = "office-agent/src/"
BEGIN = "# BEGIN generated from components.toml (python office-agent/scripts/gen_components.py)"
END = "# END generated"


def load() -> list[dict[str, object]]:
    with MAP.open("rb") as handle:
        return list(tomllib.load(handle)["component"])


def render_doc(components: list[dict[str, object]]) -> str:
    lines = [
        "# Components",
        "",
        "Generated from `components.toml`; do not edit. Find the component you change here, read",
        "its card, then the interface the card lists, then only that component's implementation.",
        "",
        "| Component | Path | Layer | Owner | Card |",
        "|---|---|---|---|---|",
    ]
    for item in components:
        path = str(item["path"])
        card = item.get("card")
        card_cell = f"[AGENTS.md](../{card})" if card else "none"
        owners = " ".join(str(o) for o in item["owner"])  # type: ignore[attr-defined]
        layer = str(item["layer"]).replace("|", "\\|")
        lines.append(f"| `{item['name']}` | `{path}` | {layer} | {owners} | {card_cell} |")
    return "\n".join(lines) + "\n"


def render_block(components: list[dict[str, object]]) -> str:
    # Later lines win in CODEOWNERS, so this block goes above the invariant paths.
    lines = [BEGIN]
    for item in components:
        path = "/" + str(item["path"])
        if (ROOT / str(item["path"])).is_dir():
            path += "/"
        owners = " ".join(str(o) for o in item["owner"])  # type: ignore[attr-defined]
        lines.append(f"{path} {owners}")
    lines.append(END)
    return "\n".join(lines) + "\n"


def merged_codeowners(current: str, block: str) -> str:
    if BEGIN in current:
        head, rest = current.split(BEGIN, 1)
        tail = rest.split(END, 1)[1].lstrip("\n")
        return f"{head}{block}\n{tail}"
    return f"{block}\n{current}"


def dotted(item: dict[str, object]) -> str | None:
    """The package's module name, or None for a single module or a non-Python component."""
    path = str(item["path"])
    if not path.startswith(SOURCE) or path.endswith(".py"):
        return None
    return path.removeprefix(SOURCE).replace("/", ".")


def render_contracts(components: list[dict[str, object]]) -> str:
    lines = [BEGIN]
    for item in components:
        name = dotted(item)
        if name is None:
            continue
        protected = item.get("protected_modules") or [f"{name}.*"]
        guidance = (
            f"Import from {name} (the names in its __all__, listed on its card), not from a "
            f"submodule. If the name is missing, export it from {name}/__init__.py and put it "
            "on the card. Do not add an ignore line."
        )
        lines += ["", "[[tool.importlinter.contracts]]"]
        lines.append(f'name = "{name} is entered through its package"')
        lines.append('type = "protected"')
        lines.append("protected_modules = [" + ", ".join(f'"{m}"' for m in protected) + "]")  # type: ignore[attr-defined]
        lines.append(f'allowed_importers = ["{name}"]')
        ignored = item.get("ignore_imports") or []
        if ignored:
            lines.append("ignore_imports = [")
            lines += [f'    "{entry}",' for entry in ignored]  # type: ignore[attr-defined]
            lines.append("]")
        lines.append(f'broken_contract_guidance = "{guidance}"')
    lines.append(END)
    return "\n".join(lines) + "\n"


def merged_pyproject(current: str, block: str) -> str:
    if BEGIN in current:
        head, rest = current.split(BEGIN, 1)
        tail = rest.split(END, 1)[1].lstrip("\n")
        return f"{head}{block}{tail}"
    return f"{current.rstrip()}\n\n{block}"


def main(argv: list[str]) -> int:
    components = load()
    doc = render_doc(components)
    codeowners = merged_codeowners(CODEOWNERS.read_text(encoding="utf-8"), render_block(components))
    pyproject = merged_pyproject(
        PYPROJECT.read_text(encoding="utf-8"), render_contracts(components)
    )
    if "--check" in argv:
        stale = [
            str(path.relative_to(ROOT))
            for path, text in ((DOC, doc), (CODEOWNERS, codeowners), (PYPROJECT, pyproject))
            if not path.exists() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            print(f"stale, run scripts/gen_components.py: {', '.join(stale)}")
            return 1
        return 0
    DOC.write_text(doc, encoding="utf-8")
    CODEOWNERS.write_text(codeowners, encoding="utf-8")
    PYPROJECT.write_text(pyproject, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
