# Three interface fixes from the maintainer's testing

Why: the maintainer tested the packaged app and reported three things.

## Shipped
- **A Word document with no comments sat to the left in the panel.** The panel kept room for the comment rail even when there were no comments, so the page was centred together with an empty rail. The rail is now left out when there are no comments, and the page is fitted to the whole width. A spec checks the page is centred (264 px off before, within 40 px now).
- **A table being edited on a Slides slide changed its header alignment.** The editor drew every header cell left-aligned, while the server's picture centres them unless the cell says otherwise. Header cells are now centred by default in the editor too. A unit test covers header, body and right-aligned cells.
- **The calls under a task card item were not in line with its words.** They started under the status ring; they now start under the item's text.

## Not verified
- Not run on Windows or in the desktop shell.
- The web search failing with "operation timed out" on every engine is not a code fault found here: see the plan for what is next.
