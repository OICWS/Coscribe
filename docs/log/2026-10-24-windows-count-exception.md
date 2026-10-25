# The Windows night of 10-24 does not restart the count (shipped)

Why: the night failed one test whose wait was too short for a slow runner (#610); the maintainer decided it should not erase five green nights.

## Shipped
- `docs/plan.md`: the Windows line records the decision. The count stays at 5 of 14 (10-19 to 10-23); 10-24 counts neither way; the next green scheduled night is the 6th. Otherwise a red night restarts the count.

## Not verified
- The cause of the 10-24 failure is likely, not proven (the failure did not reproduce locally). If a scheduled night fails again after #610, it is a product bug and the exception does not apply.

## Follow-ups
- Count the scheduled `windows.yml` runs from 10-25; at 14, comment on #232 and make the job required.
