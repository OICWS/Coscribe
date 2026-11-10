"""Install office-agent's dependencies at the versions in uv.lock, into this Python.

pyproject.toml keeps ranges, so a plain `pip install -e .` resolves afresh each time: one real
install pulled pydantic 2.14.0a1 and broke every connector. CI, the desktop sidecar and a dev
box install through this script instead, so they all get the versions in uv.lock, each checked
against its recorded hash.

uv reads the lock and writes it out as a hashed requirements list; pip installs that list into
the interpreter running this script (a CI runner's Python or a venv). `--locked` makes the
export fail when uv.lock no longer matches pyproject.toml, so a range changed without
`uv lock` fails here instead of installing something else.

    python scripts/install_locked.py --extra dev --extra web
    .venv/Scripts/python scripts/install_locked.py --extra web --group sidecar

Needs `uv` on PATH (https://docs.astral.sh/uv/getting-started/installation/).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OFFICE_AGENT = Path(__file__).resolve().parent.parent


def export_command(uv: str, extras: list[str], groups: list[str], out: Path) -> list[str]:
    cmd = [
        uv, "export", "--locked", "--format", "requirements-txt",
        "--no-emit-project", "--no-default-groups", "--output-file", str(out),
        "--project", str(OFFICE_AGENT),
    ]
    for extra in extras:
        cmd += ["--extra", extra]
    for group in groups:
        cmd += ["--group", group]
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--extra", action="append", default=[], help="an optional-dependencies extra"
    )
    parser.add_argument("--group", action="append", default=[], help="a dependency group")
    parser.add_argument(
        "--no-project", action="store_true",
        help="install only the dependencies, not coscribe itself (editable)",
    )
    args = parser.parse_args(argv)

    uv = shutil.which("uv")
    if uv is None:
        print(
            "uv is not on PATH. Install it (https://docs.astral.sh/uv/getting-started/"
            "installation/), then run this again.",
            file=sys.stderr,
        )
        return 2

    pip = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "requirements.txt"
        subprocess.run(export_command(uv, args.extra, args.group, requirements), check=True)
        # --no-deps: the list already holds every package the lock resolved, so pip must not
        # resolve again and pull in a version the lock does not name.
        subprocess.run([*pip, "--require-hashes", "--no-deps", "-r", str(requirements)], check=True)
    if not args.no_project:
        subprocess.run([*pip, "--no-deps", "-e", str(OFFICE_AGENT)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
