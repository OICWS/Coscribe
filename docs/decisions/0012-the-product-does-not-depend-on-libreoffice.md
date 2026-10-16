# 0012: The product does not depend on LibreOffice

Status: accepted (2026-10-16, by the maintainer). Supersedes 0011's stage-1 engine
("openpyxl and LibreOffice"); the rest of 0011 stands.

## Context
These features ran through a LibreOffice found on the user's machine:
- workbook recalculation and its checks;
- previews;
- the old deck route's overflow check;
- the reviewer's page images;
- file conversion.

Windows does not ship LibreOffice, coscribe's users have Microsoft Office and almost none
install it, so on their machines these features were silently off. Mainstream agents do not
rely on a local LibreOffice either: they use a cloud sandbox, a local VM, Office itself or an
engine of their own.

Measured here:
- **IronCalc** (MIT/Apache-2.0, 3.3 MB wheel): the same value as LibreOffice for all 89 formula
  cells of the ten Excel tasks, XLOOKUP and XMATCH included.
- **resvg** (resvg-py, MPL-2.0, 2.9 MB): renders a deck's SVG page with Chinese text in about a
  second.
- **pypdfium2**, already a dependency: renders PDF pages.

## Decision
- **No product code path needs LibreOffice:**
  - IronCalc computes formula values and their checks;
  - a deck page is previewed from its SVG with resvg;
  - PDF pages are rendered with pypdfium2;
  - file conversion and the exact preview of a user's Word, Excel or PowerPoint file go
    through Microsoft Office (COM) when it is installed.
- **Without Office**, conversion says it needs Microsoft Office, and Word and Excel files have
  no picture preview.
- **LibreOffice stays in development and the evaluation** (the judge's renders) only.
- **resvg's MPL-2.0** is accepted for an unmodified dependency wheel; 0010's licence rule covers
  code copied into the repository.

## Consequences
- The installer grows by about 6 MB, accepted by the maintainer.
- Checks give the same result on every machine. A function IronCalc cannot evaluate is
  reported as not checked, never as the model's error.
- A deck page's native charts and tables are placeholders in its SVG preview; Office shows
  them as built.
- COM paths are tested with fakes, and by the maintainer on Windows: CI runners have no Office.
