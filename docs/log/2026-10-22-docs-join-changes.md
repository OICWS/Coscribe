# The Word editor joins coscribe's change with the person's typing

Why: the person types in the Word editor while coscribe edits the same document. A save over a file changed meanwhile stopped at "This document changed since you opened it" and offered only Reload, which dropped what the person had typed, even when the two changes were in different paragraphs.

## Shipped
- `lib/docsMerge.ts`: `mergeBlocks(base, mine, theirs)`, a three-way join by blocks. It finds the stretches each side changed from the version the editor last saved or loaded (by what the blocks hold, not their ids, which shift when a block is added) and applies both when they touch different blocks. The result carries the file's ids, so a save over the file's version finds each block where it is. Where both changed the same block, or both added at the same place, it returns nothing.
- `useDocsSave`: on a save refused because the file changed, the editor reads the file, joins it with its current content (including what was typed since the save began), puts the result in place and saves it. Only when the join gives up does the old banner with Reload show.
- Unit tests for the join; an e2e spec: a change to another block made behind the editor, then typing, ends with both in the file and no conflict banner.

## Not verified
- Not run with a real model's turn on Windows. The join replaces the editor's content, so the caret goes to the start of the document when it happens; it only happens on a save refused by a changed file.
- Two changes to the same paragraph still stop at the banner; they are not joined inside the text.

## Follow-ups
- Keeping the caret where it was across a join.
