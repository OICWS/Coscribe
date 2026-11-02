# 0033: A run can pause for a person or a time

Status: proposed (2026-11-02, kurtosisOC; needs the maintainer's acceptance). Builds on 0029,
0031 and 0032. Issue #776, batch 3.

## Context
A run could stop only for an approval or a folder or site it wasn't allowed. A monthly task that
needs a number only the person knows, or that has to wait for the bank's file, had to be split
into two tasks or run by hand at the right moment.

## Decision
- **An ask step** (`kind: "ask"`) stops the run until a person fills its `fields` (1 to 12, each
  a typed value as inputs are (0031), or a `pick` of items from a list before it); `save_as`
  holds them by name. It waits as long as it takes unless `timeout_hours` (at most 720) is set,
  then it fails the step or, when every value it needs has a default, goes on with the defaults.
  Answers that don't fit are asked for again, saying why; the server checks them before the run
  goes on. Stopping there fails the run as a person's no.
- **A wait step** (`kind: "wait"`) waits for `minutes`, until a time (`at`, on the day `on` or the
  next time it comes), or until a file is there and has stopped changing for 5 seconds, for at
  most `max_minutes` (at most a week). A file that doesn't come fails the step (a loop that skips
  items skips it, 0032) or goes on with `found: false`. It only looks whether the file is there,
  so it needs no folder permission; the step that reads it does.
- **A paused run holds nothing but its checkpoint.** A run at a wait step has its own status,
  `waiting`; at an ask step it is `needs_approval`, as at an approval. The step's record carries
  `pause` (`kind`, `until`, and the fields or the path), which is all the poller needs: each poll
  continues the runs whose time came or whose file is there, so one due while Coscribe was closed
  goes on when it next starts.
- **The person can end a wait early**: "Go on now" ends a time wait, and for a file it looks
  again. Stopping a waiting run ends it without running anything.
- **A run waiting for an answer is announced, and reminded once a day** while the app runs; a
  wait is not announced.
- **A test run doesn't wait**: a wait ends at once and a file wait looks once; an ask step goes
  on with its defaults when it has one for every value it needs, and otherwise the test stops
  there as before an approval.
- **The run report lists the ask steps no one answered** (`unanswered`), so a run that went on
  with defaults is never read as one a person answered.
- Neither kind is allowed in `after_failure`: no one may be watching, and those steps never pause
  (0032).

## Consequences
- The editor has both kinds in its add menu, quick edit and full editor; the run view answers an
  ask on its card and shows when a wait ends.
- A workflow without these steps runs as before; no new version.
- Out of scope: waiting for an email or a web page to change, and asking someone other than the
  task's owner.
