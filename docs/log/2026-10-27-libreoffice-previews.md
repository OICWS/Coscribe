# A Word, Excel or PowerPoint file is previewed through LibreOffice when no other office program is there (shipped; part 3 of decision 0026)

Why: previews of a generated file (the write tools' `preview_path`, `review_work`'s page images, the
approval card) needed Microsoft Office or WPS, so on most computers the reviewer had no page to look
at. Decision 0026 lets a LibreOffice stand in.

## Shipped
- `_thumbnail._draw` tries Microsoft Office or WPS over COM first, as before, then a LibreOffice the
  computer has (`convert_with_libreoffice`: coscribe's own copy, else one installed). The PDF it
  makes is drawn page by page by PDFium and its words measured, exactly as the COM path's PDF is.
  The reason when none can is "drawing this file needs Microsoft Office, WPS Office or
  LibreOffice, and none was found".
- Every run uses one profile of coscribe's own (`<state_dir>/libreoffice/profile`) under a lock,
  so the person's LibreOffice settings are left alone and two runs never share a profile.
- The failure messages of the download now carry Windows Installer's code, and code 1625 says
  Windows refused, "usually because of a security policy or security software", not a company's.
- Tests hide the machine's LibreOffice (`tests/conftest.py`), as they hide Microsoft Office.

## Measured
- A 5-page Word file with a wide table, through the container's LibreOffice 24.2: 4.3 s for the
  first preview, 1.7 s for the second, 5 pages.

## Not verified
- On Windows: only the code paths shared with the download test (`convert_to_pdf`) ran there; the
  preview through the trimmed copy was not run by a person or a Windows test.
- That the reviewer judges better from these pages: not measured.
- Excel and PowerPoint through LibreOffice: only Word was previewed live here.

## Follow-ups
- `convert_office_file` (legacy `.doc`/`.xls`/`.ppt`, and PDF export) still needs Office; giving it
  LibreOffice means passing the state folder to it from `coordinator.py`, an invariant path that
  needs an independent review.
- The page-level check of a generated Word file (pagination, tables over the edge, empty pages).
