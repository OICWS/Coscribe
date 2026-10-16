# Conversion and previews through the office program on Windows (shipped)

Why: converting a file, and previewing a Word or Excel file or an edited deck, needed a
LibreOffice that Windows users do not have. Decision
[0012](../decisions/0012-the-product-does-not-depend-on-libreoffice.md), step 2.

## Shipped
- `tools/_office_com.py`: opens the file read-only in Microsoft Office through COM and saves
  it as PDF, docx, xlsx or pptx. When Microsoft Office is not installed, it tries WPS Office,
  which registers the same object model (`KWps`, `Ket`, `Kwpp`).
  - Each job runs in a PowerShell process. No new Python package is needed, and a timeout
    kills the job.
  - Paths reach the script through environment variables, never inside its text.
  - The program is hidden and closed only when it holds none of the user's files. PowerPoint
    runs one instance per user, so closing or hiding it would take the user's presentations
    with it.
- `convert_office_file` uses it first, then LibreOffice. With neither, it says it needs
  Microsoft Office (or WPS). The result names the program that converted.
- The previews (`render_thumbnail`, `render_all_page_previews`, `render_single_page_preview`)
  use it first for any file a PDF or a built deck does not cover. They draw the PDF with
  PDFium and measure its words for the deck checks.
- A Windows-only test has PowerShell parse each script; the nightly Windows job runs it.

## Not verified
- Not run against a real Microsoft Office or WPS: the CI runners have neither. The maintainer
  checks on Windows:
  - each conversion: doc to docx, xls to xlsx, ppt to pptx, and each type to PDF;
  - a preview with Word already open;
  - the same with WPS in place of Microsoft Office.
- A timeout kills PowerShell; an Office process that hangs is started by COM, outside that
  process tree, and may stay running.

## Follow-ups
- Step 3 (#319): remove the LibreOffice paths; keep them only in the evaluation.
