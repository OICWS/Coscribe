# The LibreOffice card shows a download at once and its progress (shipped)

Why: the maintainer clicked Download and saw nothing; a second click said it was already being
downloaded, and the progress bar appeared only after leaving and re-entering Capabilities.

## Shipped
- The status the server returns carried a field named `error`, and the page told a failed request
  (`{"error": ...}`) from a status by that key, so every successful answer was read as a failure
  and dropped: no state change, no polling. The status field is now `problem`.
- A test keeps `error` out of the status.

## Measured
- In a real browser against a server with a slow fake download: "Downloading…" shows 61 ms after the
  click, the progress bar moves (5%, 24%), and the card ends as "found" with the path.
- The LibreOffice card and the Scripts card sit at the same left edge, width and inner inset.

## Not verified
- The "box too far right" the maintainer saw: in this window size the card lines up with the other
  cards, so what was meant is not known.
- The real download in the app (the fake was used here).
