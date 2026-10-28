# The Sheets kind is gone from Artifacts (shipped, part 3 of decision 0027)

Why: decision 0027. A workbook is made and opened in Excel; the listing already stopped
registering `.xlsx` (part 1), so nothing could carry the kind any more.

## Shipped
- Wire: `user_message.artifact` no longer allows `"sheets"`; `wire.gen.ts` regenerated.
- Server: `list_artifacts` names Docs, presentations and designs, and its `kind` takes docs, slides
  or design (its schema snapshot changed); `artifact_note("sheets")` is empty. The note's
  history-stripping pattern still knows "Sheets", so an older conversation loses its note as before.
- Frontend: the kind, its icon, thumbnail, tile drawing, menu words and chip noun are removed;
  "Make something new" draws every page kind, since none is left to leave out.

## Not done
- `npm` packages only the Word editor used are still in `package.json`.
