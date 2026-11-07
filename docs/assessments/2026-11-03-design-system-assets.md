# Assets in a design system: logos and icons kept with it, and used by decks and designs

Status: proposed (2026-11-03), for the maintainer to accept. Decision 0020 lists Assets as part of a
design system ("logos and icons, each with a note on when to use it"); nothing of it is built.

## What the person does
- **Settings > Design systems > a system** gets an **Assets** section beside Colors, Typography,
  Spacing and Corner radius.
- **Adding an asset:** a picture is added by drag and drop or a file picker. It must be SVG, PNG,
  JPEG or WebP, at most 2 MB. A system holds at most 24 assets.
- **What each asset shows:** a thumbnail, a name, a kind and a note. The kind is Logo, Icon or
  Picture. The note says when to use it, for example "on dark backgrounds" or "app icon only".
- **Editing:** the name, kind and note can be changed, and an asset can be deleted.
- **"Describe it":** the Design System conversation, and the extraction from a template .pptx
  (`read_pptx_design`), may also add the pictures the person attached or the template holds.
  This is a later step, not the first.

## Where it is kept
- **Library:** `<system folder>/assets/<id>.<ext>`, listed in `system.json` as
  `assets: [{id, file, name, kind, note, width, height}]`. The id is generated, so a file name the
  person chose never becomes a path.
- **The image itself:** served to Settings by
  `GET /api/design-systems/{id}/assets/{asset}`, drawn as `<img>`. An SVG there runs no script.
- **In a conversation:** a conversation started with the system (Slides or Design) gets the system
  copied as today. Its assets are copied into the workspace as `brand/<system name>/<name>.<ext>`.
  As with the rest of 0020, the copy never refers back: a later change in the library does not
  move a finished deck or design.

## How coscribe uses them
- **The first message:** the note that carries the system (`design_system_text`) lists each asset
  with its workspace path, kind, size and note. As with everything per conversation, this goes in
  a message, never in the system prompt or a tool schema (0001).
- **Slides:** a picture must be a file inside the deck folder (`section_format`). The Slides guide
  says to `copy_file` the asset into the deck folder and place it with `<img src>`. A logo goes
  where the system's note says. Nothing new is needed in the engine.
- **Design:** a page loads only `data:` URIs (the frame's policy). The server would fill in, at
  serve time, an `<img src>` that names a picture file in the canvas folder, as a `data:` URI,
  the same way it fills in parts.
  - The Design skill then says: `copy_file` the asset into the canvas folder, and
    `<img src="logo.svg">`.
  - This relaxes the skill's "pictures are inline SVG or data URIs" rule for files in the canvas
    folder only. A path outside the folder, or any network address, stays blocked.
- **The checker:** later, a deck or design that began from a system with a Logo and places none
  could get a gentle note. This is not in the first steps.

## Steps
1. The store, the asset routes, and the Assets section in Settings (add, list, edit, delete).
2. Assets copied at a Slides or Design start, and listed in the first-message note.
3. Design's serve-time filling-in of a picture file in the canvas folder, and the Slides and
   Design skill lines.
4. Measured with DeepSeek, off-peak: a Slides brief and a Design brief started with a system that
   has a logo. Does the logo appear, where its note says?

## Not decided here
- Font files (0020 keeps fonts to installed ones).
- Template thumbnails.
- Writing assets into a .pptx master.
- Sharing systems between people.
