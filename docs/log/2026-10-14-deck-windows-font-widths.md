# PowerPoint part 2: text widths from the faces PowerPoint draws them in, measured on Windows (shipped)

Why: the deck engine sizes every text box, and the overflow check reads those boxes, from
per-character advances. The copied emitter had them only for fonts bundled with PowerPoint for
Mac, and it looked them up by the stack's first family. The tool's own stack is
`"Microsoft YaHei, Arial"`, so a page's digits and Latin letters, which PowerPoint draws in Arial,
were guessed at 0.55 em instead of read from Arial's table. A page in YaHei alone had no table at
all.

## Shipped
- The emitter looks advances up for the run's Latin face (what it writes as `a:latin`), not
  the first family: 2 lines in `_native_svg/.../drawingml/utils.py`, listed in its `NOTICE.md`.
- `font_advances_windows.json` (ours, beside upstream's table): Microsoft YaHei (regular, bold;
  UI and Light), Microsoft JhengHei and SimSun. They were measured on the Windows CI runner by
  `scripts/measure_font_advances.py`: Pillow (FreeType) at 1000 px, no kerning, upstream's 227
  characters, the same method that reproduces upstream's Arial table from Liberation Sans.
- The Windows job measures on every run and uploads the table. A Windows-only test fails when
  the committed table and the machine's fonts differ.
- Measured differences against the old guess:
  - `"Microsoft YaHei, Arial"`: `"5,410"` was 10% too wide; `"Q3 2026"` and `"Revenue +23.5%"`
    were within about 1%.
  - YaHei alone: Latin text was 5 to 6% too narrow.
  - Segoe UI: upstream's stand-in (Selawik) equals the Windows font, so it is not in our table.
- The engine golden changes in two box widths: a label 0.3% wider, a bold `5,410` 13% narrower.
- `tests/test_font_advances_windows.py`: 3 tests. Two fail without the change; the third is the
  Windows-only check.

## Not verified
- DengXian, SimHei, KaiTi and FangSong are not installed on the Windows Server runner, so they
  keep the guess. A user's Windows 10/11 has them; measuring them needs a desktop Windows.
- Whether the overflow check now flags different pages in real decks: no model run (none of
  today's tasks depends on it alone).
