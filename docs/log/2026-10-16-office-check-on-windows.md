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
- `tests/test_check_office.py`: the script's logic against a faked Office.

## Verified
- Microsoft Office on the maintainer's Windows machine (2026-10-16), twice: all nine
  conversions, the three previews and the three open-file cases passed, each in 1-11 s. On the
  second run, after the fix below, no office program was left running.
- The first run had found Word, Excel and PowerPoint still running: the open-file cases had
  started them themselves. The leftover check now runs before those cases, and the script
  quits the programs it started.

## Not verified
- WPS Office. Installing it on a GitHub runner was tried and dropped: the 357 MB installer
  winget lists (official-package.wpscdn.cn) came at about 100 KB/s, an hour per run. Someone
  with WPS runs the script once.
