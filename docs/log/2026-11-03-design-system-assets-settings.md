# A design system keeps its logos and icons (shipped, step 1 of the assets note)

Why: decision 0020 lists Assets as part of a design system, but none were kept. Design note
`docs/assessments/2026-11-03-design-system-assets.md` (accepted 2026-11-03) splits the work into
four steps; this is the first.

## Shipped
- **Settings > Design systems > a system** has an **Assets** section.
  - **Adding:** a picture is added from a file picker or by drag and drop. It must be SVG, PNG,
    JPEG or WebP, at most 2 MB, and a system holds at most 24.
  - **What each shows:** a thumbnail, a name, a kind and a note. The kind is Logo, Icon or
    Picture; the note says when to use it. The picture's size is also shown.
  - **Editing:** the name, kind and note can be changed, and a picture can be removed.
  - Each change is kept at once. Pictures are not part of what the form's Save sends.
- **Store** (`tools/design_systems.py`):
  - Pictures are kept in `<system>/assets/<id>.<ext>`, with their entries in `system.json`.
  - The format comes from the file's first bytes, not its name. The size of a raster picture is
    read with Pillow, and an SVG's from its viewBox.
  - `duplicate` copies a system with its pictures. The Artifacts menu's Duplicate now uses it,
    which keeps the pictures.
- **Routes:**
  - `POST /api/design-systems/{id}/duplicate`;
  - `POST .../assets` (a file upload);
  - `PUT` and `DELETE .../assets/{asset}`;
  - `GET .../assets/{asset}`. It is served with a sandboxing CSP, so a kept SVG with a script
    cannot run it in the app's origin even when opened at its own address. It is listed among the
    audited read-only GETs.
- **Tests:**
  - `tests/test_design_systems.py`: pictures by content, notes, a duplicate with its pictures, and
    the refusals.
  - `tests/web/test_design_systems.py`: the routes, and the CSP on an SVG.
  - `design-systems.spec.ts`: a logo added, given a kind and a note, refused when the file is not
    a picture, still there after reopening, then removed. All 3 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- Nothing uses the pictures yet; steps 2 and 3 copy them into a conversation and teach the skills.
