# The coverage floor is raised to what CI measures (shipped)

Why: The floor was set at 85 while CI's number was unknown (record 0009, step 2).

## Shipped
- CI's first run on `main` measured **88.58%** (statements and branches together, our own code), 1825 tests passed and 33 skipped in 9 min 3 s; local was 89%. `fail_under` is 88 now. The skipped tests are the ones that need tools CI does not have (LibreOffice), which is why CI is slightly lower.
- The changed-lines report (`diff-cover`) ran on the step 2 pull request in 2 seconds and passed; it is still report only.
- Wall time of the check step: about 10 minutes with coverage, against about 9.5 before; the two 60-second tests that were fixed paid for most of it.

## Not verified
- That 88 does not fail on a run where more tests are skipped; if it does, lower it by the difference and say why in the log.

## Follow-ups
- Make the changed-lines coverage fail under 80% after a week of numbers.
