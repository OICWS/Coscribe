# tools/presentations.py loses its transitions, animation and audio code (shipped)

Why: #232 item 5, part 1. `tools/presentations.py` was 7,081 lines; the plan names the boundary engine / edit / motion / qa / xml / templates.

## Shipped
- A pure move, no behaviour change: 976 lines leave `tools/presentations.py` (7,081 to 6,109) for three modules in `tools/office/pptx/`:
  - `xmlns.py`: the namespace constants (`_P_NS`, `_A_NS`, `_R_NS`, the p14/p15/p159 extensions, `_A14_NS`, `_M_NS`).
  - `transitions.py`: the transition registry and `_set_slide_transition` with the `mc:Ignorable` helpers (276 lines).
  - `animation.py`: the preset catalog, the timing-tree builders, the audio builders and the animation read-back check (692 lines).
- `presentations.py` imports the names back, so the toolkit class and every tool schema are unchanged (`tests/tool_schemas.txt` untouched). The preset catalog path is now resolved from `animation.py`'s own location.
- Two tests import the transition and animation registries from their new modules; their bodies are unchanged. `quality/baseline.json`: `presentations.py` 7,081 to 6,109.

## Not verified
- PowerPoint itself, as before: the XML is the same, checked by the existing structural and LibreOffice tests.

## Follow-ups
- Parts 2 to 4: rendered-slide checks, theme and template helpers, SmartArt, shape description and effects (#232, item 5).
