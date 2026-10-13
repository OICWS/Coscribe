"""Writes frontend/src/types/wire.gen.ts from conversation/wire.py.

    python scripts/gen_wire_ts.py            # rewrite the file
    python scripts/gen_wire_ts.py --check    # exit 1 if the checked-in file is stale

Comments come from the source: a TypedDict's docstring, and the `#` lines right
above a field.
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, is_typeddict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coscribe.conversation import wire  # noqa: E402

OUTPUT = ROOT / "frontend" / "src" / "types" / "wire.gen.ts"
REGENERATE = "python scripts/gen_wire_ts.py"

_HEADER = f"""// Generated from src/coscribe/conversation/wire.py -- do not edit.
// Regenerate with `{REGENERATE}` (from office-agent/).
"""


def ts_type(annotation: Any) -> str:
    if annotation is Any:
        return "unknown"
    if annotation is type(None):
        return "null"
    simple = {str: "string", bool: "boolean", int: "number", float: "number"}
    if annotation in simple:
        return simple[annotation]
    if is_typeddict(annotation):
        return str(annotation.__name__)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        return " | ".join(
            "true" if a is True else "false" if a is False else _quote(a) for a in args
        )
    if origin in (Union, types.UnionType):
        return " | ".join(ts_type(a) for a in args)
    if origin is list:
        inner = ts_type(args[0])
        return f"({inner})[]" if " | " in inner else f"{inner}[]"
    if origin is dict:
        return f"Record<string, {ts_type(args[1])}>"
    raise TypeError(f"no TypeScript form for {annotation!r}")


def _literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return _quote(value)


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _doc(text: str, indent: str) -> list[str]:
    lines = [line.strip() for line in text.strip().splitlines()]
    if len(lines) == 1:
        return [f"{indent}/** {lines[0]} */"]
    return [f"{indent}/**", *[f"{indent} * {line}".rstrip() for line in lines], f"{indent} */"]


def _comments() -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    """Class docstrings, and the `#` block above each field, from wire.py's source."""
    source = Path(str(wire.__file__)).read_text(encoding="utf-8")
    lines = source.splitlines()
    docstrings: dict[str, str] = {}
    fields: dict[tuple[str, str], str] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.ClassDef):
            continue
        docstring = ast.get_docstring(node)
        if docstring:
            docstrings[node.name] = " ".join(docstring.split())
        for item in node.body:
            if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                continue
            above: list[str] = []
            row = item.lineno - 2
            while row >= 0 and lines[row].strip().startswith("#"):
                above.insert(0, lines[row].strip().lstrip("#").strip())
                row -= 1
            if above:
                fields[(node.name, item.target.id)] = " ".join(above)
    return docstrings, fields


def _wrap(text: str, width: int = 88) -> str:
    out: list[str] = []
    line = ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    out.append(line)
    return "\n".join(out)


def render() -> str:
    docstrings, field_comments = _comments()
    out = [_HEADER]
    for name, value in vars(wire).items():
        if name.startswith("_"):
            continue
        if is_typeddict(value) and value.__module__ == wire.__name__:
            if name in docstrings:
                out += _doc(_wrap(docstrings[name]), "")
            out.append(f"export interface {name} {{")
            hints = get_type_hints(value)
            for key, annotation in hints.items():
                if (name, key) in field_comments:
                    out += _doc(_wrap(field_comments[(name, key)], 80), "  ")
                optional = "?" if key in value.__optional_keys__ else ""
                out.append(f"  {key}{optional}: {ts_type(annotation)};")
            out.append("}")
            out.append("")
        elif isinstance(value, types.UnionType) and all(is_typeddict(a) for a in get_args(value)):
            members = "\n".join(f"  | {a.__name__}" for a in get_args(value))
            out.append(f"export type {name} =\n{members};")
            out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT} is out of date; run `{REGENERATE}`", file=sys.stderr)
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
