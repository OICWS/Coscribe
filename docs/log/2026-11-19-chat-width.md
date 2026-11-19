# Long tool summaries stay inside the conversation (shipped)

Why: long tool names and the right-aligned message's centered Rewind tooltip could extend
beyond the conversation and make it scroll sideways, especially beside the Plan panel.

## Shipped
- Allow long words in tool summaries to wrap at the available width, keeping the full label,
  existing font and disclosure control. The transcript's overflow is not hidden or clipped.
- Align the Rewind tooltip to its button's right edge, as the adjacent Edit/Copy tips already
  do. An opacity-hidden tooltip still contributes to scroll width: this produced a separate
  40 px overflow in an 824 px transcript, even with the long summary wrapped.
- A browser regression checks full-width and narrow windows, with the Plan panel open/closed
  and tool results expanded/collapsed. It measures transcript width and the label's actual lines.
- The full Electron app reproduced a 983 px chat area with 3342 px of horizontal content before
  the fix; the same content fits afterward. Long prose, tables, formulas and code were checked too.

## Not verified
- A real Windows desktop locally; the application check ran on Linux.

## Follow-ups
- None.
