# The caret stays where it was when the editor joins a change

Why: when the Word editor joined coscribe's change with the person's typing (the previous change), it rebuilt its content and the caret went to the start of the document, in the middle of a sentence.

## Shipped
- `lib/docsCaret.ts`: the caret is noted by the words of its paragraph, how far into them and which paragraph it is, and found again in the rebuilt document: in the paragraph with the same words nearest to where it was, else in the paragraph at the same place.
- `useDocsSave` notes the caret before the join and puts it back, and keeps focus if the editor had it.
- Unit tests for the helpers; the join spec now types in the "Price" heading, in the middle of the document, and the next key lands after what was typed. It fails without the restore.

## Not verified
- Not run on Windows or with a real model's turn. A selection of several words is not kept: only where the caret is.
