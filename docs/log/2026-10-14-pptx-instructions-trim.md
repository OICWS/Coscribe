# The PowerPoint instructions cut to what templates and edits need (shipped)

Why: since #213 a new deck is built from pages, and the long guidance on `write_pptx`'s markdown,
its layouts and choosing a bundled template no longer applied; it also contradicted the new-deck
paragraph (ask the user to pick a template / do not). A shorter prompt that scores the same is
the better one.

## Shipped
- `coordinator.py`: about 120 lines on `write_pptx`'s syntax and layouts, picking and asking for a
  bundled template, 16:9 tags and `write_pptx`'s past bugs become one paragraph: read with
  `read_pptx`; new decks from pages; `write_pptx` / `fill_pptx_template` for the user's own
  template or a plain deck the user asks for, after loading "PPTX Slides" (which still documents
  the syntax); fix the warnings and look at the preview. The editing guidance is unchanged.
- The bundled templates are no longer listed in the prompt; the user's own extracted templates
  still are.
- `NEW_DECK_INSTRUCTIONS` no longer says it replaces the guidance above.
- The system prompt: 45,263 to 35,111 characters (about 11.3k to 8.8k tokens, 22% less);
  `coordinator.py` 974 to 870 lines.

## Not verified
- Windows.
- The model run of tasks 03 to 07 (new decks, the user's template, an edit) on the cut prompt:
  pending off-peak; result and cost added to this PR.

## Follow-ups
- `tests/test_presentations_tool.py::test_set_pptx_transition_survives_libreoffice_conversion`
  failed once under `pytest -n 4` and passes alone (LibreOffice run in parallel); not this change.
