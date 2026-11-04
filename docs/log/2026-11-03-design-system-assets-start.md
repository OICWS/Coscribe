# A design system's pictures go with a Slides or Design start (shipped, step 2 of the assets note)

Why: step 1 (`docs/log/2026-11-03-design-system-assets-settings.md`) keeps logos and icons with
a system, but a conversation started with the system did not get them.

## Shipped
- **The copy:** a Slides or Design conversation started with a system that has pictures gets them
  copied into its workspace as `brand/<system name>/<picture name>.<ext>`.
  - The names are made plain: letters and digits of any script, dashes and underscores.
  - A repeated name gets `-2`.
  - The source is `DesignSystemStore.copy_assets`, called from `design_system_for_start`.
  - As with the rest of decision 0020, the copy does not refer back to the library.
- **The first message:** the note that carries the system (`design_system_text`) lists each
  picture with its workspace path, kind, size and note. It also says to use a logo where its note
  says, copied into the deck or canvas folder. This goes in the message, never in the system
  prompt or a tool schema.
- **Tests:**
  - `tests/test_design_systems.py`: the names and paths of the copies.
  - `tests/test_runtime_lg_messages.py`: the pictures in the note.
  - `tests/web/test_chat_events.py`: a Design start over the socket with a system that has a
    logo. The file is in the workspace, and the message names it with its note.

## Not verified
- Not run with a real model. Steps 3 and 4 teach the skills to place the pictures, let a Design
  page show a picture file of its canvas folder, and measure it with DeepSeek.
