# A written Word file's pages are checked, and conversion falls back to LibreOffice (shipped)

Why: the last two parts of decision 0026 (`docs/log/2026-10-27-libreoffice-*.md` built detection,
the download and previews). A Word file coscribe wrote was never looked at as laid out, so an empty
page or a table running off the paper reached the person unseen. `convert_office_file` still needed
Microsoft Office or WPS.

## Shipped
- **The page check** (`tools/_page_check.py`). Every Word write (`write_docx`,
  `edit_docx_structure`, accepting or rejecting tracked changes, `edit_docx_review`) returns
  `page_check`:
  - who laid the document out (Microsoft Word, WPS or LibreOffice), and its page count;
  - an empty page (no text, picture or drawing besides the header, footer and page number);
  - text past the paper's edge (a table or line too wide), measured against the MediaBox so a
    rotated landscape page is not flagged;
  - a last page holding a line or two, only after a full page, so a signature put on its own page
    is not flagged.
  - A header, footer or page number is a line at the same place, in the top or foot band, on most
    pages; it counts neither as body nor against an empty page.
  - It reads the PDF the preview already makes (`_thumbnail._draw`), so nothing is converted
    twice.
  - With no office program it says "not checked" and why, never a pass. A check that can't read
    the PDF says that the program laid it out but its PDF could not be read, and the preview is
    still drawn.
  - The Word skill says to fix what it lists and write again.
- **`convert_office_file` through LibreOffice.** When neither Office nor WPS converts over COM, the
  LibreOffice this computer has (coscribe's own copy or one installed) writes the file, and
  `converted_by` says so. `coordinator.py` passes the state folder to `build_convert_tools`, on
  the line that was there, so `build_coordinator_agent` does not grow. `state_dir` is a required
  keyword, so a caller cannot leave LibreOffice out by accident.
- `tests/tool_schemas.txt` is regenerated (Python 3.11) for the three descriptions that changed.
- **Tests:**
  - `tests/test_page_check.py`:
    - hand-written PDFs: one that looks right; an empty page, text past the edge and a spilled
      last line, each named;
    - a header, footer and page number on every page; a short page after a half-empty one; a
      rotated page;
    - "not checked" and why, and a PDF the check cannot read;
    - `write_docx` returning what a stand-in for Word laid out.
  - `tests/test_convert_tool.py`: LibreOffice converts when Office and WPS don't.
  - Live, in this container's real LibreOffice: a one-page document reports no problems; one more
    line reports "page 2, the last, holds only a line or two"; a whole paragraph on page 2 does not.

## Not verified
- On Windows: Word's and WPS's layouts through COM, and LibreOffice through coscribe's own copy.
- LibreOffice runs as the user, as previews through it already do. Decision 0026 asks for the
  scripts' folder limits where that isolation is set up; that is not done here.
