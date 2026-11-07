# Editing an existing deck's slides and shapes moved from the system prompt into a "PPTX Editing" skill (shipped)

Why: the coordinator's system prompt was 30.4k characters, and about a third of
it explained tools only needed when an existing .pptx is edited shape by shape.
Every turn of every conversation paid for that text. Part of #805.

## Shipped
- `builtin_skills/pptx-editing/SKILL.md` ("PPTX Editing"): slides, shapes and
  SmartArt, diagrams from preset shapes, formulas, pictures, icons, tables,
  hyperlinks and theme colors, moved from `coordinator.py`'s instructions.
- The instructions keep a pointer to `load_skill("PPTX Editing")` and the two
  rules a wrong first call breaks: a plain arrow or box is `add_pptx_shape`,
  not an icon; theme colors don't recolor existing text. The prompt is now
  21.8k characters.
- Evals 07, 11 and 15 (DeepSeek, one run each): every fact kept, every deck
  opens and stays editable in both runs. Task 15's overlaps went from 9 to 0
  and its overflow from 0 to 1; tool calls rose from 88 to 118 in total,
  partly the extra `load_skill` call.

## Not verified
- One eval run per side, so the tool-call and cost changes are within the
  noise seen between runs; no run on a Claude or Gemini model.
- A real Windows machine.

## Follow-ups
- Run the same three tasks a few more times before slimming the other
  per-format sections the same way.
