# coscribe is told which slides the user changed since its last turn (#462)

Why: a slide edited in the Slides panel is a page file the user wrote, and coscribe learned of it
only by reading the page or by a rebuild being refused. Design §12 listed it as open.

## Shipped
- `tools/office/pptx/engine/view_changes.py`: `deck_edits_since_coscribe(deck)` compares the pages
  of coscribe's last known state (its last build, or the state it was last told about) with the
  pages now, from the undo history's recorded states, and returns the pages edited, added and
  removed. The net difference counts, so an edit that was undone reports nothing. Reporting marks
  it told (`told` in `.history/states.json`, kept by every write of the log), so it is said once.
- `conversation/deck_edits.py`: for each .pptx the conversation has worked on (the activity it
  already summarises), one line in front of the user's message, with the date, mode and language
  notes: which deck, which pages (named by file), where the pages are, and to read them before
  changing those slides and not to rebuild from older sources. `session.py` calls it once per turn.
- It goes in the newest message only: not the system prompt, not the tool list, and nothing
  earlier in the history is changed, so the provider's prompt cache is untouched.
- `session.py` did not grow (the ratchet): the mode note's choice moved to `turn_text.py`.
- Tests: `tests/test_deck_changes.py`, `tests/test_deck_edits_note.py`,
  `tests/web/test_chat_deck_edits.py` (a whole turn: the note is in the model's message once).

## Not verified
- With a real model: whether it reads the named pages first. A deck built before the undo history
  existed has no recorded states, so nothing is told for it.
- Edits made outside the app (the .pptx opened in PowerPoint) are not told; the rebuild refusal
  stays the guard for those.

## Follow-ups
- Refusing coscribe's overwrite of a hand-edited slide before the rebuild (plan.md).
