# "Describe it" and a template .pptx add pictures to a design system (shipped)

Why: the assets design note (`docs/assessments/2026-11-03-design-system-assets.md`) leaves one
step for later: the Design System conversation, and the extraction from a template, may add the
pictures the person attached or the template holds. Until now a system got pictures only in
Settings.

## Shipped
- **`save_design_system` takes `assets`:**
  - Each row is `{file, name, kind, note}`.
  - `file` is a picture in the workspace (an attachment lands there), or a picture inside a deck
    as `read_pptx_design` names it (`template.pptx#ppt/media/image3.png`), read from the
    package without writing a file.
  - Each goes through the library's own checks (SVG, PNG, JPEG or WebP; 2 MB; 24 at most).
  - Pictures are added to those the system has. The same file twice is kept once, so a second
    save does not duplicate them.
  - A row it cannot take is an error to repair. A new system then leaves nothing half made, as
    before.
  - The tool reads pictures from the workspace: `build_design_system_tools(state_dir, root,
    extra_readable)`. That is one argument more in `coordinator.py`, on the same line.
  - Its summary counts the pictures.
- **`read_pptx_design` lists `pictures`:** the pictures the master and its layouts draw on
  every slide (a logo, a band), each once. Each entry gives the `file` to pass on, where it is
  drawn, its size there on a 1920 px slide, and its own pixel size.
- **The "Describe it" note** (`runtime_lg/messages.py`) asks for the attached logos and icons,
  or the template's, to be saved as the system's assets.
- `tests/tool_schemas.txt` is regenerated on Python 3.11 for the two changed tools.
- **Tests:**
  - `tests/test_design_system_tool.py`:
    - attached pictures are added once each;
    - a picture that can't be taken (not a picture, missing, outside the workspace, a bad
      in-deck path, no workspace) is refused and leaves no system.
  - `tests/tools/office/pptx/test_theme_colors.py`: a logo drawn by a layout is listed, and
    the `file` it gives is saved as a logo.

## Not verified
- Not run with a real model ("describe it" with an attached logo, or with a template).
- A template whose logo is on a slide rather than the master or a layout: only the master and
  layouts are read, as for its colors and fonts.
- Checked on Linux only.
