# An artboard exports as a PNG or a Windows icon (shipped)

Why: a Design could be exported as HTML or PDF, but a canvas had no Export at all, and a logo
could not be taken out as an image or an icon. This was the plan's last open Design item.

## Shipped
- **The menu:** the canvas's file menu has **Export** with:
  - **PNG**: the selected artboard (or the first) at twice its size;
  - **ICO**: a Windows icon at 16 to 256 px. It is offered only for a square artboard.
  - The export uses the light or dark scheme the canvas shows.
- **How it is drawn:** the server draws the board as the app serves it, with its parts and the
  canvas's variables (`conversation/page_tools.export_board`). It uses the computer's own Edge or
  Chrome, as `look_at_page` does.
  - `shoot_page` takes a `scale` for the device pixel ratio.
  - A board smaller than 256 px is drawn denser to fill the icon's largest size.
- **Route:** `POST /api/threads/{thread_id}/canvas/export`. It is a POST, not a GET, because it
  starts a browser, so it carries the launch token. It answers with fixed texts when there is no
  browser, when an icon is asked of a board that is not square, or when the drawing fails.
- **Tests:**
  - `tests/test_page_tools.py`: a real Chromium draws a PNG at 2x with the canvas variable
    applied, and a multi-size ICO. A board that is not square, or a page of its own, is refused.
  - `tests/web/test_artifacts.py`: the route and its texts.
  - `design-canvas.spec.ts`: Export saves an 800x600 PNG of a 400x300 board, and ICO is disabled
    for it. All 7 tests pass against a live server.

## Not verified
- Not drawn with Edge on Windows; `test_windows_real.py` covers `shoot_page` there, but not the
  scale or the .ico.
