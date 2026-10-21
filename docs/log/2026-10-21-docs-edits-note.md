# Docs: coscribe is told what the person edited in the editor (shipped)

Why: the Docs editor writes straight into the `.docx`. Without a hand-off, coscribe's next turn could work
from an older copy of the file and write it over the person's edits. Slides already tell coscribe about
the person's edits (#462); Docs now do the same.

## Shipped
- A save from the editor first records what the document said before the person's first edit since coscribe
  was last told (`state_dir/docs_edits/`, one small file per document: a line `kind: text` per block).
- In front of the person's next message, coscribe gets one line: the document was edited in the app, what
  changed, was added and was removed (up to 12 blocks, each cut to 80 characters), with the instruction to
  read the document before changing it and not to write it again from an older copy. Told once: the record
  is deleted when it is read, so the next message carries nothing until the person edits again.
- A changed and a replaced block are told as changed, not as one removed and one added: blocks are paired by
  similarity (`difflib`), so a reworded sentence stays one change.
- The deck note and the document note share one entry point (`conversation/user_edits.py`), so `session.py`
  calls one function.
- Tests: the diff (changed, added, removed, a reworded block, no change, told once) and a web test that
  the line reaches the model in front of the next message and not the one after.

## Not verified
- With a real model: whether coscribe reads the document again before it edits, as the line asks.
- A document edited in Word itself (outside the app) is not told; only the editor's saves are.
- The packaged app on Windows.

## Follow-ups
- Undo in the editor that covers coscribe's own turns, images, divider and page break, version history:
  in `docs/plan.md`.
