# presentations.py loses SmartArt, shape description, effects and template slide copying (shipped)

Why: #232 item 5, part 4.

## Shipped
- A pure move: 500 lines leave `tools/presentations.py` (5,479 to 4,979) into `tools/office/pptx/`:
  - `smartart.py`: detecting SmartArt, its node text and its data part.
  - `shape_description.py`: what `list_pptx_shapes` reports for one shape, and `emu_to_inches`. `presentations._describe_shape` stays as the import alias the eval test patches.
  - `template_slides.py`: copying a template's slide parts and adjusting the content slides for `fill_pptx_template`.
  - `effects.py`: shadow, glow and soft edge.
- Names two modules share are public (`is_smartart`, `smartart_text`, `SMARTART_NS`, `SHAPE_EFFECT_TYPES`); the rest stay private to their module. `tests/test_office_golden.py` and `tests/tool_schemas.txt` did not change.
- `quality/baseline.json`: only the `presentations.py` line (5,479 to 4,979).

## Not verified
- A deck with SmartArt, a shadow and a filled template opened in PowerPoint on Windows; the golden and tool tests pass locally.

## Follow-ups
- `presentations.py` is still over the 800-line cap with the toolkit class; the deck engine stays with the PowerPoint maintainer's session (#232, item 5).
