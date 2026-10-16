# LibreOffice is out of the product (shipped)

Why: the last step of decision
[0012](../decisions/0012-the-product-does-not-depend-on-libreoffice.md). After steps 1 and 2 the
product only fell back to LibreOffice, which coscribe's Windows users don't have.

## Shipped
- No product code runs LibreOffice:
  - `_thumbnail.py` draws pages in one of three ways: a PDF with PDFium, a built deck from its
    SVG pages, any other file through the office program (COM). Without an office program the
    reason says so;
  - `convert_office_file` needs Microsoft Office or WPS, and its `state_dir` argument is gone;
  - `write_pptx`'s overflow check has the office program draw the deck.
- `tools/_office_bins.py` keeps only `run_killable`, which runs a program with a timeout that
  kills what it started. Finding LibreOffice and its profiles moved to `evals/libreoffice.py`,
  which the evaluation's renders use.
- Tool descriptions, the system prompt's one sentence on skipped previews, the README and
  ARCHITECTURE.md now speak of the office program.
- Tests:
  - an autouse fixture keeps a developer's own Office out of every test;
  - a test marked `real_libreoffice` gets LibreOffice standing in for the office program, so
    previews, the overflow check and the approval card's previews are still checked end to end
    where LibreOffice exists. Those 24 tests pass;
  - their probes call LibreOffice directly (`tests/libreoffice_probe.py`).

## Not verified
- Everything that goes through Office or WPS on Windows. The maintainer's checks are listed in
  `2026-10-16-convert-and-preview-through-office.md`.

## Follow-ups
- None for 0012. LibreOffice stays installed by the cloud session hook for development and the
  evaluation.
