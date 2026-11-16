# The AI drags, drops files and copies and pastes with a clipboard of its own (shipped, part 2b of #915)

Why: pages that move cards, reorder rows or take a slider, upload areas without a button, and
copying a value from one page into another were out of the AI's reach, in conversations and saved
workflows alike (#915).

## Shipped
- `browser_drag(ref, target=...)` or `browser_drag(ref, by_x=..., by_y=...)`: a real mouse press,
  moves and release, which sliders and mouse-driven lists need. With drags intercepted, an HTML5
  drag hands Chromium's drag data over and the drop is sent as drag events at the target
  (`browserAgentMoves.ts`). The moves are sent without waiting for each acknowledgement: a page off
  screen answers input only with its next frame, about a second apart (measured: 12 moves took
  12 s awaited, about 1 s sent together).
- `browser_file_upload(..., drop=True)` drops the person's files onto a drop area.
- `browser_copy` and `browser_paste` use a clipboard per conversation or run in the desktop app.
  The person's own clipboard is never read or written (the maintainer's choice on #915: it may hold
  their passwords, and a copy would replace what they copied). A rich text editor gets the copied
  formatting; a plain field gets the text. Page to Word or Excel goes through files (part 3).
- Copy is a READ tool, drag and paste EXTERNAL. Self-healing does not use them: a paste enters data
  that came from a page, not from the run.
- Tests: `scripts/browser-native.cjs` (real Electron) drags an HTML5 item onto a drop zone with its
  data, moves a slider, drops a file, refuses a paste before a copy, pastes rich text into an
  editor and plain text into a field, and checks the system clipboard was left alone; its overall
  limit goes from 25 s to 50 s for the added checks. pytest covers the tools and a saved workflow
  that drags, copies on one page and pastes on another.

## Not verified
- A person using the Windows app; drag libraries that track pointer events only (not mouse
  events) on real sites.

## Follow-ups
- Part 3 of #915: tables to Excel or CSV, page to PDF, collecting across pages.
