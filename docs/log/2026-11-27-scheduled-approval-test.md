# Synchronize the scheduled approval test with delivery

The scheduled run test waits for the watching tab to receive the approval event, then denies
it and joins the background task before closing SQLite. The test runs again on Windows and
Linux after the quarantine in #986 expired.

## Not verified

- Windows timing will be checked by the Windows CI job.
