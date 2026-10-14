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
  `coordinator.py` 974 to 869 lines.

## Checked (2026-10-14, off-peak, after merging)
Tasks 03 to 07 on `main` with the cut prompt, `deepseek-flash` at effort low, 3 judge rounds;
before is 03 to 05 on #213 and 06, 07 in the measurement (`2026-10-14-deck-engine-measurement.md`).

| Task | Facts | Design | Content | Coherence | Tool calls | Cost |
|---|---|---|---|---|---|---|
| 03-project-proposal | 18/18 | 4.30 (4.27) | 4.40 (4.57) | 4.53 (4.50) | 59 (36) | 0.052 (0.043) |
| 04-product-launch | 12/12 | 3.83 (3.63) | 3.67 (3.87) | 4.23 (3.87) | 50 (45) | 0.050 (0.038) |
| 05-long-report | 23/23 | 4.27 (4.40) | 4.43 (4.30) | 4.57 (4.57) | 30 (65) | 0.028 (0.050) |
| 06-own-template | 12/12 | 2.87 (2.63) | 3.30 (3.07) | 3.47 (3.27) | 33 (18) | 0.018 (0.015) |
| 07-edit-deck | 5/5 | 2.97 (3.20) | 4.07 (4.33) | 4.00 (3.90) | 33 (34) | 0.022 (0.026) |

- No score moved by more than about one judge spread (0.1 to 0.5 here); 07's design and content
  are the lowest changes and a run of 07 with the same prompt (PR 1 to 3, the same evening)
  scored 3.17 / 4.47 / 3.77, so they are run-to-run variation. 06 and 07 still went through the
  template and edit tools.
- Cost 0.172 dollars for the five, the same as before (0.172). 04 and 05 lost their connection to
  the model in the first minute and were run again (infrastructure, 0.015 for the failed
  attempts); with the judge the evening cost 0.21 dollars, about 1.4 yuan.

## Not verified
- Windows.

## Follow-ups
- `tests/test_presentations_tool.py::test_set_pptx_transition_survives_libreoffice_conversion`
  failed once under `pytest -n 4` and passes alone (LibreOffice run in parallel); not this change.
