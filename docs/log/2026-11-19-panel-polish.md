# Polish Context usage, plan links and workflow quick edits (shipped)

Why: the Context usage label wrapped despite available space, the Open plan
link lacked hover feedback, and the workflow quick editor covered the top bar.

## Shipped

- Size the Context usage number columns to their contents and share their
  alignment across rows. The category name gets the remaining space.
- Give Open plan a pointer, a lighter colour and underline on hover, and an
  underline on keyboard focus.
- Start the workflow quick edit sheet and its backdrop below the app header
  on both desktop and web, using the same height as the header.
- Fast checks, the existing plan and workflow browser tests, and a full
  Electron check of all three interactions passed locally.

## Not verified

- A native Windows desktop. The app check used Electron on Linux.

## Follow-ups

- None.
