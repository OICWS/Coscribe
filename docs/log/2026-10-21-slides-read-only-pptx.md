# Slides: any .pptx is shown read-only (shipped)

Why: the panel said "was not made by coscribe from slide pages, so it can't be shown here yet" for
every other .pptx, a template a person sent included. Editing such a file in the panel is not
planned; a read-only view is.

## Shipped
- A .pptx coscribe did not build is written as a PDF by the installed office program (Microsoft
  Office or WPS, decision 0012) once per version of the file, and each slide is that PDF's page,
  drawn by PDFium and held in an SVG, so the panel's thumbnails, Present, zoom and notes work as
  for a built deck (`engine/view_foreign.py`; the routes fall back to it where they would answer
  "not built").
- The panel marks it read-only: no editor, no properties panel, and a line saying to ask coscribe or
  open it in PowerPoint. Without an office program nothing changes: the panel keeps the old message.

## Not verified
- Against a real PowerPoint (the office program is faked in the tests).
- Not shown read-only yet: the New slide, reorder and duplicate controls and comments still call
  the edit routes and answer with the "not built" message.
- Not run in a live server or the app.
