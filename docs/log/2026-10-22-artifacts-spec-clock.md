# The Artifacts e2e test no longer depends on the hour

Why: `artifacts.spec.ts` listed its newest artifact as "3 hours ago" and expected a "Today" heading, so it failed in CI for every run between 00:00 and 03:00 UTC (seen on #524 at 01:20 UTC).

## Shipped
- The fixture is three hours ago or midnight, whichever is later, so it is always today.

## Not verified
- Run only in the 01:00 hour, where the old fixture fails and the new one passes; not in a time zone with a half-hour offset.
