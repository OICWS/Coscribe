# Finished decks keep their chat cards and slide sources (shipped)

Renaming the final build left cards pointing to its temporary names. The viewer
could show unrelated source slides during a turn, and the delivered file lost
its link to the source pages. Those pages also showed up as picture notices.

## Shipped

- Check that a deck path exists before showing its chat link or card. Recheck
  after tool results so files moved during the conversation stop appearing.
- Show source thumbnails only for the deck named by the active build.
- Preserve the build record when the file tool renames a deck in the same
  folder, including an overwrite of the delivery name. Keep the existing check
  for changes made directly to the PowerPoint file after the build.
- Defer notices for new SVGs until the turn completes, then omit SVGs reported
  as build inputs. Standalone images still get notices.

## Not verified

- Native Windows was not exercised locally.
- An already-moved deck whose build record names the old path is not migrated.
  The app needs a new build to reconnect it, or the existing PPTX can be edited
  in PowerPoint.

## Follow-ups

- None.
