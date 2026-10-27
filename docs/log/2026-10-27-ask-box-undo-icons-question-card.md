# Ask coscribe opens a box, new undo/redo icons, a typed message closes the question card (shipped)

Why: three reported details. "Ask coscribe" on selected words sent at once instead of letting the
person say what to change; the undo and redo icons looked poor; typing in the chat box while
AskUserQuestion was open left the card open.

## Shipped
- The older Word editor's bubble and the Word viewer's selection bar open the same box as the Doc
  editor (`AskBox`: a text field and the chips "Make it shorter", "Make it simpler", "Fix spelling
  and grammar"); the instruction follows the quoted words in the message.
- `UndoIcon` and `RedoIcon` are curved-arrow shapes; every place that shows them changes.
- Sending a message while a question card is pending closes the card as dismissed, then sends the
  message (`App.tsx`).

## Not verified
- None of the three in a browser or the desktop app: build, lint and unit tests only.
- Whether the box keeps focus in the older editor's bubble menu (the Doc editor's box was checked
  earlier).
- What the model does with a dismissed question followed by the typed message.

## Follow-ups
- None.
