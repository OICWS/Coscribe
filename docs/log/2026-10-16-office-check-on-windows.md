# One command checks the conversions and previews through Office on Windows (shipped)

Why: conversion and previews go through Microsoft Office or WPS on Windows (decision 0012, step
2), and none of it had run against a real office program: CI's Windows runners have neither, so
the tests fake PowerShell, and the maintainer had a checklist to work through by hand.

## Shipped
- `office-agent/scripts/check_office.py`, run on a Windows machine with Office or WPS:
  - all nine conversions `convert_office_file` offers (doc, xls and ppt to their new formats and
    to PDF; docx, xlsx and pptx to PDF), each output opened and checked for the sample's text;
  - the first-page preview of a Word, Excel and PowerPoint file;
  - a file the user has open in Word, Excel or PowerPoint stays open while another is converted;
  - an office process left running afterwards is reported.

  It prints one table and exits 1 when a check fails; `--require` also fails when no program is
  found. The legacy samples are in `scripts/office_check_samples/` (made with LibreOffice).
- `.github/workflows/windows-office.yml`: installs WPS Office on a Windows runner (the installer
  winget lists) and runs the script against it. By hand, and on a PR that changes it or the
  script; not a required check.
- `tests/test_check_office.py`: the script's logic against a faked Office.

## Not verified
- Microsoft Office: no runner has it. The maintainer runs `python scripts/check_office.py` once
  on Windows with Office.
- Whether WPS installs and answers COM on a runner without anyone at the screen: this PR's run
  of the new workflow says.
