# An HTML page coscribe writes is a Design artifact, shown in a sandboxed panel (shipped)

Why: the maintainer saw a page of icon options (inline SVG with gradients and shadows, each icon at 16 to 128 px on a light and a dark background) published as a Design artifact in another tool, and asked for coscribe to make and show the same. Decision 0015 already says Design is drawn in a sandboxed frame; nothing did it yet. Issue 551.

## Shipped
- `.html` files a conversation creates are registered as kind `design` (`conversation/artifacts.py`). A lone `.svg` is a picture file like a .png and is not an artifact: a design is an HTML page with its drawings inline.
- `web/routes/design.py` serves the page (`/api/threads/{id}/design?path=`, `/api/artifacts/{id}/content`) with `Content-Security-Policy: sandbox allow-scripts; default-src 'none'`: the page may run its own script and style, and has no origin, network, frames or forms. 8 MB cap. A `print=true` copy carries a small listener so the app can print it.
- Frontend: Design is the fourth kind (tile, icon, filter, "Make something new" tile with a prompt). A card draws the page itself, scaled, in the same sandbox. The viewer panel (`DesignPanel`) shows the page full size and draws it again whenever the file is written, so a rewritten file updates in place. The name menu is the common artifact menu.
- `Export` in that menu opens a second menu to its right (`SlideMenu` now takes `submenu`, `description` and `trailing`): HTML downloads the page, PDF opens the print dialog.
- Built-in skill `svg-design`: one self-contained HTML page, drawings as `symbol`/`use`, gradients and shadows with per-drawing ids, every size on both backgrounds, and a separate .svg per finished drawing. It is delivered by the skill mechanism and the first-message note (`artifact: "design"`), not the tool list or system prompt (0001).
- Tests: the registry and the route's headers (`tests/web/test_artifacts.py`), the note, `viewers.test.ts`, route and OpenAPI snapshots.

## Not verified
- Not run with a real model: whether the skill gets a model to write good pages.
- Not run on Windows or in the desktop shell; the PDF print path was not exercised (it opens the browser's print dialog, which a headless run cannot see).
- The light and dark switch inside the frame follows the system, not the app's theme setting.

## Follow-ups
- Dashboard (same sandbox, data attached), PNG and .ico export of a drawing, a theme toggle in the panel, a server-rendered thumbnail for the web build.
