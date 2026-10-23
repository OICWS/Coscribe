# A deck card appears only once a file was written; the composer footer holds its size (shipped)

Why: a presentation card showed under a command still waiting for approval, because a run of
read-only calls (`list_pptx_shapes` and the like) counted as touching the file; the Slides panel
then showed read errors while coscribe was rewriting the file; and the composer's bottom row
wrapped its text when the conversation column was narrow.

## Shipped
- `lib/fileMentions.ts`: `touchedFiles` ignores calls that only look at a file (read, list,
  inspect, get, check, render, preview, search, find, describe, count) and counts the files a
  script reports in `files_written`.
- `SlidesPanel`: while a turn runs it shows "coscribe is working on <name>…" instead of an empty
  stage, and shows no read error; a deck coscribe did not build no longer reports that its
  comments could not be read.
- `Composer`, `RunStatus`: the bottom row does not wrap or shrink; a very narrow column cuts it
  off at the edge (checked at 260px: one line, no horizontal scroll).

## Not verified
- Windows and the desktop app; the detached panel window (it has no turn state, so it never
  shows the working notice).
- Read-style tool names are matched by prefix, so a new read tool named differently would still
  show a card.

## Follow-ups
- A deck the person brought and coscribe rewrote whole is not listed in Artifacts (only files the
  conversation created are); proposed: list whole-file writes too.
- The read-only preview draws a blank page for a deck with SVG or WMF graphics.
