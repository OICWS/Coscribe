"""`scripts/check_office.py` runs on the maintainer's Windows machine against real Office; here
the PowerShell it starts is faked, as in `test_office_com.py`, to check the script's own logic."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from coscribe.tools import _office_com

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_office.py"
_spec = importlib.util.spec_from_file_location("check_office", _SCRIPT)
assert _spec is not None and _spec.loader is not None
check_office: Any = importlib.util.module_from_spec(_spec)
sys.modules["check_office"] = check_office
_spec.loader.exec_module(check_office)


class _FakeOffice:
    """Writes each target as a real file of its type, holding the sample's text unless told not
    to."""

    def __init__(self, samples: Path, pdf_text: str) -> None:
        self.samples = samples
        self.pdf_text = pdf_text

    def __call__(
        self, command: list[str], timeout: float, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        assert env is not None
        target = Path(env["COSCRIBE_TARGET"])
        if target.suffix == ".pdf":
            from reportlab.pdfgen import canvas

            page = canvas.Canvas(str(target))
            page.drawString(72, 720, self.pdf_text)
            page.save()
        else:
            shutil.copy(self.samples / f"sample{target.suffix}", target)
        return subprocess.CompletedProcess(command, 0, b"", b"")


@pytest.fixture
def office(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _FakeOffice:
    samples = tmp_path / "modern"
    samples.mkdir()
    check_office.write_modern_samples(samples)
    fake = _FakeOffice(samples, check_office.MARKER)
    monkeypatch.setattr(_office_com, "run_killable", fake)
    monkeypatch.setattr(_office_com, "shutil", type("S", (), {"which": staticmethod(str)}))
    monkeypatch.setattr(_office_com, "_registered", lambda prog_id: not prog_id.startswith("K"))
    monkeypatch.setattr(check_office, "powershell", lambda code, env, check=True: "1")
    monkeypatch.setattr(check_office.time, "sleep", lambda seconds: None)
    return fake


def test_without_an_office_program_it_checks_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_office.main([]) == 0
    assert check_office.main(["--require"]) == 1
    assert "nothing to check" in capsys.readouterr().out


def test_every_check_passes_when_office_writes_good_files(
    office: _FakeOffice, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_office.main(["--out", str(tmp_path / "work")]) == 0

    out = capsys.readouterr().out
    assert "FAIL" not in out
    assert "sample.ppt -> pptx" in out and "PowerPoint.Application" in out
    assert "sample.xlsx stays open" in out and "preview sample.docx" in out


def test_a_pdf_without_the_samples_text_fails_its_check(
    office: _FakeOffice, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    office.pdf_text = "blank"

    assert check_office.main(["--out", str(tmp_path / "work")]) == 1
    assert "the PDF lacks the sample's text" in capsys.readouterr().out


def test_a_closed_user_file_is_reported(
    office: _FakeOffice,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(check_office, "powershell", lambda code, env, check=True: "0")

    assert check_office.main(["--out", str(tmp_path / "work")]) == 1
    assert "the user's file was closed by the conversion" in capsys.readouterr().out


def test_the_legacy_samples_hold_the_marker_text() -> None:
    marker = check_office.MARKER
    for name in ("sample.doc", "sample.xls", "sample.ppt"):
        data = (check_office.SAMPLES / name).read_bytes()
        assert marker.encode("latin-1") in data or marker.encode("utf-16-le") in data, name
