"""Puts the two helpers Codex's sandbox launches, as OpenAI built and signed them, into OUT_DIR:
taken from the pinned Codex wheel and checked against its hashes. Built here instead, unsigned,
Windows Defender takes the setup helper (which creates users and changes permissions) for a
trojan. Usage: signed_helpers.py OUT_DIR"""

from __future__ import annotations

import hashlib
import runpy
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HELPERS = ("codex-windows-sandbox-setup.exe", "codex-command-runner.exe")
PINS = Path(__file__).parents[2] / "office-agent/src/coscribe/code_runtime/_pins.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(out: Path) -> None:
    wheel = runpy.run_path(str(PINS))["WHEELS"]["win32/amd64"]
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / wheel["filename"]
        urllib.request.urlretrieve(wheel["url"], path)
        if _sha256(path) != wheel["sha256"]:
            sys.exit(f"{wheel['filename']} doesn't match its pinned sha256")
        with zipfile.ZipFile(path) as archive:
            for name in HELPERS:
                member = f"codex_cli_bin/codex-resources/{name}"
                target = out / name
                target.write_bytes(archive.read(member))
                if _sha256(target) != wheel["members"][member]["sha256"]:
                    sys.exit(f"{name} doesn't match its pinned sha256")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
