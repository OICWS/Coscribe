"""Converting through the office program installed on Windows (decision 0012). CI has no Office,
so the PowerShell run is faked here; the scripts themselves are checked by the maintainer on
Windows with Microsoft Office and with WPS."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from coscribe.tools import _office_com, _thumbnail
from coscribe.tools.convert import build_convert_tools


class _FakeOffice:
    """Stands in for PowerShell: records each run and writes the target the environment names."""

    def __init__(self, fail: str = "") -> None:
        self.runs: list[dict[str, Any]] = []
        self.fail = fail

    def __call__(
        self, command: list[str], timeout: float, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        assert env is not None
        self.runs.append({"script": command[-1], "env": env, "timeout": timeout})
        if self.fail:
            raise subprocess.CalledProcessError(1, command, b"", self.fail.encode())
        target = Path(env["COSCRIBE_TARGET"])
        if target.suffix == ".pdf":
            from PIL import Image

            Image.new("RGB", (200, 300), "white").save(target)
        else:
            target.write_bytes(b"converted")
        return subprocess.CompletedProcess(command, 0, b"", b"")


@pytest.fixture
def office(monkeypatch: pytest.MonkeyPatch) -> _FakeOffice:
    fake = _FakeOffice()
    monkeypatch.setattr(_office_com, "run_killable", fake)
    monkeypatch.setattr(_office_com, "shutil", type("S", (), {"which": staticmethod(str)}))
    monkeypatch.setattr(_office_com, "_registered", lambda prog_id: prog_id.startswith("K"))
    return fake


def test_no_office_program_is_found_off_windows(tmp_path: Path) -> None:
    assert _office_com.program_for(tmp_path / "a.docx") is None


def test_a_file_name_never_becomes_part_of_the_script(office: _FakeOffice, tmp_path: Path) -> None:
    source = tmp_path / "a'; Remove-Item C:\\ -Recurse; '.docx"
    source.write_bytes(b"x")

    _office_com.convert(source, tmp_path / "out.pdf", "pdf", 30)

    (run,) = office.runs
    assert "Remove-Item" not in run["script"] and "Remove-Item" in run["env"]["COSCRIBE_SOURCE"]
    assert run["env"]["COSCRIBE_FORMAT"] == "17"


def test_wps_is_used_when_microsoft_office_is_not_installed(
    office: _FakeOffice, tmp_path: Path
) -> None:
    source = tmp_path / "a.pptx"
    source.write_bytes(b"x")

    assert _office_com.convert(source, tmp_path / "a.pdf", "pdf", 30) == "Kwpp.Application"
    assert "New-Object -ComObject 'Kwpp.Application'" in office.runs[0]["script"]


def test_the_program_is_closed_and_hidden_only_when_it_holds_no_file_of_the_users() -> None:
    for kind, count in (
        ("word", "Documents"),
        ("excel", "Workbooks"),
        ("powerpoint", "Presentations"),
    ):
        script = _office_com._OPEN_AND_SAVE[kind]
        assert f"$open = $app.{count}.Count" in script
        assert "if ($open -eq 0) { $app.Quit() }" in script
        assert "Visible = $false" not in script or "if ($open -eq 0) { $app.Visible" in script


def test_convert_uses_the_office_program_and_says_which(
    office: _FakeOffice, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "old.xls").write_bytes(b"x")
    (tool,) = build_convert_tools(tmp_path)

    result = tool(path="old.xls", to_format="xlsx")

    assert result["converted_by"] == "Ket.Application" and (tmp_path / "old.xlsx").is_file()
    assert office.runs[0]["env"]["COSCRIBE_FORMAT"] == "51"


def test_without_any_office_program_convert_says_it_needs_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    (tool,) = build_convert_tools(tmp_path)

    with pytest.raises(ValueError, match="needs Microsoft Office"):
        tool(path="a.docx", to_format="pdf")


def test_a_failure_in_office_is_reported_with_its_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, office: _FakeOffice
) -> None:
    office.fail = "Exception calling Open: The file is corrupt\nmore detail"
    (tmp_path / "a.docx").write_bytes(b"x")

    with pytest.raises(ValueError, match="KWps.Application could not convert.*corrupt"):
        _office_com.convert(tmp_path / "a.docx", tmp_path / "a.pdf", "pdf", 30)


def test_a_word_file_is_previewed_through_the_office_program(
    office: _FakeOffice, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")

    name, reason = _thumbnail.render_thumbnail(tmp_path / "a.docx", tmp_path / "state")

    assert reason is None and name is not None and len(office.runs) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell parses the scripts on Windows")
@pytest.mark.parametrize("suffix", [".docx", ".xlsx", ".pptx"])
def test_powershell_parses_each_script(suffix: str, tmp_path: Path) -> None:
    check = (
        "$errors = $null; "
        "[System.Management.Automation.Language.Parser]::ParseInput("
        "$env:COSCRIBE_SCRIPT, [ref]$null, [ref]$errors) | Out-Null; "
        "$errors | ForEach-Object { $_.Message }; exit $errors.Count"
    )
    script = _office_com.script(tmp_path / f"a{suffix}", "Some.Application")

    done = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", check],
        capture_output=True,
        env={**os.environ, "COSCRIBE_SCRIPT": script},
        timeout=60,
    )

    assert done.returncode == 0, done.stdout.decode(errors="replace")
