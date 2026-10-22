# A picture in the message box can be drawn on

Why: the maintainer wanted a picture put in the message box to be opened and edited before it is sent (the Claude app has an Annotate image pencil in the preview, with a toolbar of pen, shapes, text, colour, width and Save).

## Shipped
- Opening an attached picture shows a pencil, "Annotate image". It opens the annotator over the picture: Pen, a Shape menu (Line, Arrow, Rectangle, Ellipse, Step for a numbered circle, Redact for a box that blacks out what is under it), Text, Colour, four line widths, Undo, Redo, Clear, Close and Save. Save adds the marked copy as a new attachment (`<name>-annotated.jpg`) beside the original, which stays; Escape closes the annotator and not the preview under it.
- The Browser panel's annotator and this one are one component now (`ImageAnnotator`), so the Browser panel's screenshots get the same tools. A picture with clear areas is saved on white, not black.
- Tests: a Playwright spec (open, draw a step and a pen stroke, undo and redo, save, both attachments there) and a unit test of the new shapes.

## Not verified
- The Browser panel's annotator (desktop app only) was refactored into the shared component and not run; it uses the same code with the picture stretched over the panel as before.
- Not run on Windows. Whether the marks land exactly under the pointer on a high-DPI screen was checked only by the code's scaling, not by eye.

## Follow-ups
- Annotating a picture in a conversation's history, and a picture made by a tool; here only the message box's own pictures can be marked.
