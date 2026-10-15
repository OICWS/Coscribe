# PowerPoint: icons by name on a page (shipped)

Why: ppt-master's decks use icons from a library, and coscribe's pages could only draw icons from
scratch (the guide forbade it as clip art). ppt-master bundles about 12,000 icons in five sets
(about 50 MB); the maintainer ruled out growing the repository and the desktop installer by that,
so a chosen set ships instead.

## Shipped
- `tools/office/pptx/engine/icons.json`: 293 icons of Tabler Icons v3.46.0 (outline, MIT, from
  ppt-master's snapshot; `ICONS_NOTICE.md`), one 89 KB file. Chosen for decks: trends and charts,
  money and trade, people and organisations, buildings and places, transport and logistics,
  energy and environment, technology, security, health, time, documents and communication,
  status marks.
- A page writes `<use data-icon="ship" x y width height stroke="#RRGGBB"/>`; the compiler draws
  the icon there in that colour, the 2 px line scaled with the icon. An `id` names the shape. A
  wrong name is an error listing the nearest names.
- "PPTX Pages": an Icons section; the names are in `icons.md` (read with read_skill_file). The
  tool description names the element.
- Tests: an icon at its box in its colour with its scaled line weight; an unknown name.

## Not verified
- Windows and PowerPoint.
- The model's use of icons: measured with the next theme run on tasks 13 and 14.

## Follow-ups
- Other icon sets (Phosphor, CHUNK) only if a style needs them; the full library stays out.
