# A much larger home greeting pool (shipped)

Why: the first two greeting pools were still thin; the request was for far more
variety, in a mix of poetic and witty lines.

## Shipped
- `frontend/src/lib/greetingLines.ts`: about 150 single-line greetings in groups for
  morning, afternoon, evening, night, any time, Monday, Friday, weekend and the four
  seasons (by month). Holidays are left out on purpose.
- `greetings.ts` merges the time of day, any-time, weekday and season groups and draws
  one; `pickGreeting` skips the line shown last, kept in memory for the page's life.
- `HomeGreeting` picks once, after the name has loaded.
- Tests: the plain anchors, no placeholder without a name for any month/day/hour, the
  weekday and season groups, and the no-repeat rule.

## Not verified
- Not looked at in the running app or on Windows; only lint, build and unit tests.

## Follow-ups
- "Welcome back after some days" lines need the last visit saved server-side, because
  the desktop app gets a new port each launch and browser storage resets.
- A first-run welcome group is not added: nothing marks a first run yet.
