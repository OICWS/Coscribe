# Artifacts: one file menu for the card and the panel's name (shipped)

Why: the Artifacts card menu had Rename, Duplicate and Delete shown as "Soon", and a Word panel
had no menu under its name at all. The maintainer's rule: every artifact's header and menu look the
same, and only what is under the name differs by kind.

## Shipped
- A menu with the same entries from the card and from the name in a panel: what the file is and when
  it was updated, Open in its program, Show in folder, Rename, Duplicate, Pin, Copy path, Delete.
  A kind adds its own entries before Delete (a deck: Discard my edits).
- Rename renames the file on disk, keeping its ending; a name that is not a file name, or one in use,
  is refused. Duplicate makes `name copy.ext`. Delete asks first, then moves the file to the recycle bin
  (new dependency `send2trash`) and takes it off the list.
- A deck is more than its .pptx: its pages folder records the deck by path, so a rename rewrites that
  record and a copy gets its own copy of the folder. Delete trashes both.
- The Word panel's header now has the file name with this menu, like the Slides panel's.
- `GET /api/artifacts/lookup` tells a panel whether the file it shows is an artifact; for any other
  file the menu has only Open and Show in folder.

## Not verified
- send2trash on a real Windows machine (the tests replace it), and PyInstaller picking it up in the packaged app.
- Renaming a deck that is open in PowerPoint (Windows refuses to rename an open file; the menu shows its message).
- Playwright was not run here; `artifacts.spec.ts` has a new test for the menu.
- In a panel in its own window, Rename and Delete are greyed out: that window cannot follow the file.
