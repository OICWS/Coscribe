# A deck stays tied to its pages when it or its workspace moves (shipped)

Why: a pages folder's `build.json` named its deck by absolute path, and the viewer looked for the
pages only beside the deck. Renaming or syncing the workspace folder, renaming the deck in
Explorer or by a script, moving it to another folder, or building from pages kept elsewhere left
the deck read-only in the viewer, and the next revision's build was refused as "not built from
these pages", which is one way a revision ended up as a second PPTX.

## Shipped
- `build.json` names the deck relative to the pages folder (`tools/_presentation_record.py`);
  `read_manifest` hands callers the absolute path, so the comparisons are unchanged.
- A deck renamed outside coscribe is found again by its slides: when no record names it and
  exactly one beside it names a deck that is gone and holds exactly these slide hashes, that
  record is pointed at it (on viewing, and before a build to it).
- `move_file` of a deck to another folder takes its pages folder along (a free name there).
- `build_pptx_from_pages` refuses a pages folder that is not beside the `.pptx`.
- The PPTX, a slide's page, the comments and the design system are written to a hidden file and
  then replaced whole (`_file_locks.write_atomically`): a failed write leaves the old file and no
  `.tmp`. A template deck's overflow check no longer leaves an empty temporary folder when the
  office program fails.

## Not verified
- On Windows: the replace over a deck open in PowerPoint (it should give the same "probably open
  in another program" message as before, from the replace), and a workspace on another drive than
  its pages (falls back to the absolute path).

## Follow-ups
- Leftover working files at the end of a turn (in `docs/plan.md`).
