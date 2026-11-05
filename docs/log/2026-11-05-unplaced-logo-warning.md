# A deck's build warns when no slide places its design system's logo (shipped)

Why: the assets work (`docs/log/2026-11-04-design-system-logo-measured.md`) asks the skills to
place a design system's logo, but nothing told the model when a deck had none. Three gaps showed
up while adding that warning:

- A deck learned its library system only once the Slides panel had read it. So the first build,
  and every build of a run without the panel, was not checked against the system at all
  (colours, fonts, text styles).
- An SVG file in the pages folder was taken for a slide, so a logo copied in as `logo.svg` failed
  the build ("canvas differs from the deck's"). That is why the DeepSeek run moved its logos into
  `assets/`.
- The Slides skill (sections, the route for a new deck) did not mention the logo.

## Shipped
- **The conversation's system reaches the build:**
  - `build_presentation_tools(thread_id=...)` passes the conversation to the engine's tool. The
    tool reads `DesignSystemStore.deck_system_for_thread`: the system the conversation started
    with, in a deck's shape, each picture with the `brand/...` path its copy has and its file's
    sha256.
  - A pages folder with no `design-system.json` yet is seeded with it (`seed_design_system`), as
    the panel does on its first read. The existing off-system check now runs from the first build.
- **The logo warning** (`design_check.unplaced_logo`):
  - The build adds a deck warning when the system has logos and no page places one of them.
  - The warning names the `brand/...` file to copy and its note.
  - A logo counts as placed when a picture a page names is that very file, compared by sha256.
    A renamed copy counts. A redrawn or recoloured one does not, which matches the skills' "never
    redrawn".
- **A picture beside the pages is not a slide:** `page_files` leaves out a file a page places with
  `<img src>` or `<image href>`, so `logo.svg` in the folder is a picture. The panel, undo and
  arrange use the same list.
- **The Slides skill:** a system's logo is copied into the deck folder and placed with
  `<img src="logo.svg" style="...; object-fit:contain"/>` where its note says.
- **Tests:**
  - `tests/test_deck_design_check.py`:
    - a logo counts as placed by its file, not its name;
    - through `build_presentation_tools` with a real library and conversation, the first build
      seeds the system and warns; once a slide places a renamed copy, the warning is gone and the
      deck has two slides, not three.
  - `tests/test_design_systems.py`: the conversation's system in a deck's shape.

## Not verified
- Not run with a real model: it was DeepSeek's peak hours. Whether the model acts on the warning
  is not measured.
- A Design canvas has no such warning yet (next, in `look_at_page`).
- Checked on Linux only.
