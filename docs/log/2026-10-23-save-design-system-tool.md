# A tool that saves a design system from a conversation (shipped, part 1 of 2)

Why: making a design system took the blank form only. The design note
(`docs/assessments/2026-10-23-describe-a-design-system.md`) adds a second way: describe the brand
in a conversation and the model saves the system. This part is the model's side; nothing in the
UI starts it yet.

## Shipped
- `tools/design_systems.py`: `build_design_system_tools` with the deferred tool
  `save_design_system`. Without `system_id` it makes a system from the store's defaults and the
  fields given; with one it changes only the fields passed (a list passed replaces that list).
  Everything goes through the store's `_clean`, so a bad value comes back to the model as the
  store's own message, and a system whose first save failed is not left in the library.
  Risk tier `WRITE_LOCAL`; `coordinator.py` lists it.
- `runtime_lg/messages.py`: the `design-system` kind of `artifact_note` tells the model what to
  ask, to read attachments, to propose in words first and to save with the tool.
- `tests/tool_schemas.txt` regenerated: one more deferred tool; the bound list is unchanged.
- Tests: `tests/test_design_system_tool.py`, `tests/test_runtime_lg_messages.py`.

## Not verified
- How cheaper models fill the text styles, and colors read from a picture are estimates.
- Windows and the desktop app.

## Follow-ups
- Part 2: the chip, the tile menu (Blank form / Describe it), the card at the end of the turn,
  and the wire's `artifact` kind.
