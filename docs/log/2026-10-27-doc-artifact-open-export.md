# Doc artifact, step 5 part 2: a Doc opens in the panel, and exports

Date: 2026-10-27
Area: frontend

A Markdown file is now viewable: its chip in a conversation, the Artifacts page and the panel's own
menu open it in the Doc editor. The server says whether it is a Doc; a plain `.md` shows a one-line note
and the menu under its name still opens it in the default app (that was one click away before, and is
now two: this is the price of deciding by the front matter, which a path cannot show; reverting it is
the one line in `viewers.ts`). The Doc's menu has Export as Word (the server's file, 0025), as PDF (the
page copied into a hidden frame and handed to the print dialog, "Save as PDF" there) and as Markdown (the
blocks without the front matter).

Not verified: the PDF printed to a real file on Windows (the print dialog was stubbed; the copied page
has the callouts, the chart and the table); the Word file in the real Word; a Markdown file's chip
opening for every `.md` a tool reads (it does, then says it is not a Doc).
