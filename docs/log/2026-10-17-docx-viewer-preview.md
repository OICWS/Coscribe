# Word viewer panel, read only (partly shipped)

Why: step 3 of the file viewers (decision 0014, `docs/assessments/2026-10-17-file-viewers.md` §3).
The maintainer asked for a read-only version first, to judge the look before the actions are
wired.

## Shipped
- A `viewer` panel in the panel layout. A Word file under Task details (Outputs or Context)
  opens in it instead of in Word; "Open in Word" is in its header.
- Pages drawn by docx-preview 0.4.1 (Apache-2.0, with JSZip), loaded only when the panel opens.
  Review, Final and Original views; Original is the server's copy with every change rejected.
- The comment rail: cards level with their words, pushed apart when they overlap, the active one
  level with its words and the others making way (`stackCards`, unit-tested). Connectors run
  from the end of the commented words to the card. Replies under their comment; a resolved
  thread folds to one line.
- Cards are placed by the `start of comment #id` markers docx-preview leaves in the page. When
  its count of changes or comments differs from the server's, connectors are not drawn.
- Above the page: the count of changes and comments, and previous / next through both.
- Pages scale to the panel; when that would leave a page below 60% beside the rail, the comments
  open in a drawer instead.

## Not verified
- On Windows, in the desktop app: rendering of real Word files with fonts the machine lacks,
  and long documents (render time not measured).
- No Playwright spec: the CI stub model never calls a tool, so no Word file reaches Task
  details there. Checked by hand against a live server instead.

## Follow-ups
- Accept or reject a change, reply, resolve, comment on a selection, Ask coscribe (step 3, part 2).
- Open from a file card in the conversation and from a tool row.
