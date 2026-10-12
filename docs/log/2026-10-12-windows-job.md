# A Windows job runs the tests nightly, report only (shipped)

Why: The maintainer tests the app by using it, not from a checklist (record 0009), so what a real Windows machine would catch (paths, the locale's code page, PowerShell and cmd, the keychain) has to be caught by a script. Several bugs so far were found only that way.

## Shipped
- `.github/workflows/windows.yml`: on `windows-latest` (free for public repositories) it builds the frontend, installs coscribe and runs the whole test suite with `pytest`. It runs nightly, by hand, and on a pull request that changes the workflow file. A failure does not fail the pull request: the job is `continue-on-error` and not a required check. The job summary lists the tests that failed or errored, and the junit report is kept as an artifact.

## Not verified
- What fails on Windows: the first run of this pull request is the first time the suite runs there. Tests written on Linux may assume POSIX paths or tools; the list the run shows is the work to do next.

## Follow-ups
- Fix the failures that are bugs, fence the tests that only assume Linux (a marker with a reason), then make the job a required check after two green weeks.
- Test selection by changed package, to keep the job short as the code grows.
