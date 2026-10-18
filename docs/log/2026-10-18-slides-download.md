# Slides panel, part C2: the Download menu

Why: the mockups' download button offers PDF, a web page, the current slide as a picture, and the
deck in PowerPoint with its own fonts or with basic ones (issue #420).

## Shipped
- `tools/office/pptx/engine/view_export.py`, each made from the built deck:
  - `deck_pdf`: PowerPoint's own PDF export where it is installed (decision 0012). Otherwise each
    slide is drawn at 2560 px into a 960 × 540 pt page. Text in the drawn copy cannot be selected.
  - `deck_html`: one file with every slide as an image and a few lines of player (arrows, click,
    Home and End). Nothing in it is fetched from anywhere.
  - `deck_basic_fonts`: the .pptx with every latin, East Asian or complex-script face outside a
    basic set swapped. East Asian text goes to Microsoft YaHei (SimSun when the face is serif);
    other text goes to Arial (Times New Roman when serif). The basic set is the faces Windows
    with Office has. Theme references (`+mn-lt`) and the theme's per-script faces are left alone.
- `GET /api/threads/{id}/slides/export?path=&format=pdf|html|pptx-basic`, sent as an attachment.
  The routes now share one error mapping, with fixed messages.
- The panel:
  - the download button and its menu, as the mockup lists them, with the note "Basic fonts work
    on any computer";
  - PowerPoint with current fonts is the built file itself;
  - the current slide is drawn in the browser at 1920 × 1080 and named after its number;
  - the button pulses while a file is being made, and a failure is shown under the header.
- Tests: three in `tests/test_deck_view.py` (a page per slide, a web page that fetches nothing,
  only basic faces after the swap), and the route test extended.

## Checked
- In Chromium against a live server, the six-slide Q3 deck: all five downloads saved.
  - the PDF has 6 pages;
  - the web page plays on its own;
  - the PNG is slide 3 at 1920 × 1080;
  - both .pptx open.

## Not verified
- The PDF from PowerPoint itself (Windows only).
- Downloads in the Electron app, where the save dialog is the shell's.
